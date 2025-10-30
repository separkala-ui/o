import { registry } from "@web/core/registry";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";

registry.category("web_tour.tours").add("l10n_mx_edi_pos.test_mx_pos_invoice_order_and_refund", {
    steps: () =>
        [
            {
                content: "Click the POS icon",
                trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
                run: "click",
            },
            {
                content: "Open POS session from backend",
                trigger: "button[name='open_ui']",
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: "Open Register",
                trigger: ".modal .modal-footer .btn-primary:contains(open register)",
                run: "click",
            },
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Arturo Garcia"),
            {
                content: "Select a product",
                trigger: "div.product-content:contains('product_mx')",
                run: "click",
            },
            {
                content: "go to Payment",
                trigger: ".pay-order-button",
                run: "click",
            },
            {
                content: "Customer wants an invoice",
                trigger: ".js_invoice",
                run: "click",
            },
            {
                content: "Set Usage: 'General Expenses'",
                trigger: "select[name='l10n_mx_edi_usage']",
                run: "select G03",
            },
            {
                content: "Set Invoice to Public: 'Yes'",
                trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
                run: "select 1",
            },
            Dialog.confirm(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            {
                content: "Usage: 'Returns, discounts or bonuses' should be selected",
                trigger: "div.mx_invoice:contains('Returns, discounts or bonuses')",
            },
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_mx_edi_pos.tour_invoice_order_default_usage", {
    steps: () => [
        {
            content: "Click the POS icon",
            trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
            run: "click",
        },
        {
            content: "Open POS session from backend",
            trigger: "button[name='open_ui']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Open Register",
            trigger: ".modal .modal-footer .btn-primary:contains(open register)",
            run: "click",
        },
        {
            content: "Select a product",
            trigger: "div.product-content:contains('product_mx')",
            run: "click",
        },
        {
            content: "Select a customer",
            trigger: ".set-partner",
            run: "click",
        },
        {
            content: "Select the partner 'Arturo Garcia'",
            trigger: "tr.partner-line:contains('Arturo Garcia')",
            run: "click",
        },
        {
            content: "go to Payment",
            trigger: ".pay-order-button",
            run: "click",
        },
        {
            content: "Customer wants an invoice",
            trigger: ".js_invoice",
            run: "click",
        },
        Dialog.confirm(),
        {
            content: "Option I01 should be selected",
            trigger: "div.mx_invoice:contains('Constructions')",
        },
        Chrome.endTour(),
    ],
});
