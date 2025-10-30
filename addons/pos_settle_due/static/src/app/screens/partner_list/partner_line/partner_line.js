import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { CustomSelectCreateDialog } from "@pos_settle_due/app/views/view_dialogs/select_create_dialog";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PartnerLine.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
    },
    get partnerInfos() {
        return this.pos.getPartnerCredit(this.props.partner);
    },
    async settleCustomerDue() {
        this.props.close();
        const partnerId = this.props.partner.id;
        const commercialPartnerId = this.props.partner.raw.commercial_partner_id;
        this.dialog.add(CustomSelectCreateDialog, {
            resModel: "pos.order",
            noCreate: true,
            multiSelect: true,
            listViewId: this.pos.models["ir.ui.view"].find(
                (v) => v.name == "customer_due_pos_order_list_view"
            ).id,
            domain: [
                ["commercial_partner_id", "=", commercialPartnerId],
                ["customer_due_total", ">", 0],
            ],
            onSelected: async (orderIds) => {
                const settleDueLinesIds = this.pos
                    .getOrder()
                    .lines.filter((line) => line.isSettleDueLine())
                    .map((line) => line.settled_order_id.id);
                const isAnyOrderAlreadySettled = orderIds.some((orderId) =>
                    settleDueLinesIds.includes(orderId)
                );
                if (isAnyOrderAlreadySettled) {
                    return this.dialog.add(AlertDialog, {
                        title: _t("Error"),
                        body: _t("One of the selected orders is already being settled."),
                    });
                }
                this.pos.onClickSettleDue(orderIds, partnerId, commercialPartnerId);
            },
        });
    },
    async depositMoney(amount = 0) {
        this.props.close();
        this.pos.depositMoney(this.props.partner, amount);
    },
    payLaterPaymentExists() {
        return this.pos.models["pos.payment.method"].some(
            (pm) =>
                this.pos.config.payment_method_ids.some((m) => m.id === pm.id) &&
                pm.type === "pay_later"
        );
    },
    async settleCustomerInvoices() {
        this.props.close();
        const partnerId = this.props.partner.id;
        const commercialPartnerId = this.props.partner.raw.commercial_partner_id;
        this.dialog.add(CustomSelectCreateDialog, {
            resModel: "account.move",
            noCreate: true,
            multiSelect: true,
            listViewId: this.pos.models["ir.ui.view"].find(
                (v) => v.name == "due_account_move_list_view"
            ).id,
            domain: [
                ["commercial_partner_id", "=", commercialPartnerId],
                ["pos_amount_unsettled", ">", 0],
            ],
            onSelected: async (invoiceIds) => {
                this.pos.onClickSettleInvoices(invoiceIds, partnerId, commercialPartnerId);
            },
        });
    },
});
