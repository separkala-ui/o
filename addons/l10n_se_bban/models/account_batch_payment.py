import base64
import io
import zipfile

from datetime import datetime

from odoo import models, _
from odoo.exceptions import RedirectWarning


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def validate_batch(self):

        if self.payment_method_code == 'iso20022_se':
            if (
                self.journal_id.bank_account_id.acc_type in ('bban_se', 'plusgiro', 'bankgiro')
                and (no_eur_payments := self.payment_ids.filtered(lambda pay: pay.currency_id.name not in ('SEK', 'EUR')))
            ):
                raise RedirectWarning(
                    _("Internal swedish payments must be in EUR or SEK. Some payments are using another currency."),
                    no_eur_payments._get_records_action(name=_("Non-EUR/SEK Payments")),
                    _("View Payments"),
                )

        return super().validate_batch()

    def _generate_export_file(self):
        # OVERRIDES of account_batch_payment
        if self.payment_method_code == 'iso20022_se' and len(self.payment_ids.mapped('partner_bank_id.acc_type')) > 1:
            sorted_payments = self.payment_ids.sorted('id')
            iban_payments = sorted_payments.filtered(lambda p: p.partner_bank_id.acc_type == 'iban')
            iban_payments_data = self._generate_payment_template(iban_payments)
            iban_payments_xml = self.journal_id.create_iso20022_credit_transfer(
                iban_payments_data,
                self.payment_method_code,
                batch_booking=self.iso20022_batch_booking,
            )
            bban_payments = sorted_payments - iban_payments
            bban_payments_data = self._generate_payment_template(bban_payments)
            bban_payments_xml = self.journal_id.create_iso20022_credit_transfer(
                bban_payments_data,
                self.payment_method_code,
                batch_booking=self.iso20022_batch_booking,
            )
            if iban_payments_data and bban_payments_data:
                with io.BytesIO() as buffer:
                    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
                        filename = f"{self.journal_id.code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        zip_file.writestr(f"SCT-{filename}-iban.xml", iban_payments_xml)
                        zip_file.writestr(f"PAIN-{filename}-bban.xml", bban_payments_xml)

                    return {
                        'file': base64.encodebytes(buffer.getvalue()),
                        'filename': f"{filename}.zip",
                    }

        return super()._generate_export_file()

    def _get_export_file_name_prefix(self):
        if self.payment_method_code == 'iso20022_se' and self.payment_ids and self.payment_ids[0].partner_bank_id.acc_type != 'iban':
            return "PAIN-"
        return super()._get_export_file_name_prefix()

    def _get_payment_vals(self, payment):
        return {
            **super()._get_payment_vals(payment),
            'acc_type': payment.partner_bank_id.acc_type,
        }
