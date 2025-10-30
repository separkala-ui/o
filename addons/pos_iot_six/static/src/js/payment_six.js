import { _t } from "@web/core/l10n/translation";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { PaymentInterfaceIot } from "@pos_iot/app/utils/payment/payment_interface_iot";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PaymentSix extends PaymentInterfaceIot {
    getPaymentData(uuid) {
        const paymentLine = this.pos.getOrder().getPaymentlineByUuid(uuid);
        return {
            messageType: "Transaction",
            transactionType: "Payment",
            amount: Math.round(paymentLine.amount * 100),
            currency: this.pos.currency.name,
            cid: uuid,
            posId: this.pos.session.name,
            userId: this.pos.user.id,
        };
    }

    getCancelData(uuid) {
        return {
            messageType: "Cancel",
            cid: uuid,
        };
    }

    getPaymentLineForMessage(order, data) {
        const line = order.getPaymentlineByUuid(data.cid);
        const terminalProxy = line?.payment_method_id.terminal_proxy;
        if (line && terminalProxy) {
            return line;
        }
        return null;
    }

    onTerminalMessageReceived(data, line) {
        this._setCardAndReceipt(data, line);
        if (data.Stage === "Cancel") {
            // Result of a cancel request
            if (data.Error) {
                this._resolveCancellation?.(false);
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Transaction could not be cancelled"),
                    body: data.Error,
                });
            } else {
                this._resolveCancellation?.(true);
                this._resolvePayment?.(false);
            }
        } else if (data.Disconnected) {
            // Terminal disconnected
            line.setPaymentStatus("force_done");
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Terminal Disconnected"),
                body: _t(
                    "Please check the network connection and then check the status of the last transaction manually."
                ),
            });
        } else if (line.payment_status !== "retry") {
            // Result of a transaction
            if (data.Error) {
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Payment terminal error"),
                    body: _t(data.Error),
                });
                this._resolvePayment?.(false);
            } else if (data.Response === "Approved") {
                this._resolvePayment?.(true);
            } else if (["WaitingForCard", "WaitingForPin"].includes(data.Stage)) {
                line.setPaymentStatus("waitingCard");
            }
        }
    }

    _setCardAndReceipt(data, line) {
        if (data.Ticket) {
            line.setReceiptInfo(data.Ticket);
        }
        if (data.Card) {
            line.card_type = data.Card;
        }
    }
}

register_payment_method("six_iot", PaymentSix);
