# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
NON_TAXABLE_GRIDS = {'+21', '+45_BASE', '-21', '-45_BASE'}


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_de_vat_definition_export_identifier = fields.Integer(string='L10n DE Vat Definition Export ID', compute='_compute_l10n_de_vat_definition_export_identifier', help="The ID of the VAT definition in the Fiskaly export.", store=True, readonly=False)

    @api.depends('amount', 'invoice_repartition_line_ids.tag_ids', 'refund_repartition_line_ids.tag_ids', 'company_id.l10n_de_fiskaly_api_secret')
    def _compute_l10n_de_vat_definition_export_identifier(self):
        for tax in self._get_german_tax():
            if not tax.amount:
                all_tags = set((tax.invoice_repartition_line_ids + tax.refund_repartition_line_ids).tag_ids.mapped('name'))
                tax.l10n_de_vat_definition_export_identifier = 5 if all_tags.issubset(NON_TAXABLE_GRIDS) else 6
            else:
                # Sort to prioritize standard VATs (lower IDs) over historical ones (higher IDs) when selecting the export ID
                sorted_vats = sorted(tax.company_id.l10n_de_vat_export_data, key=lambda x: x['vat_definition_export_id'])
                tax.l10n_de_vat_definition_export_identifier = next((i['vat_definition_export_id'] for i in sorted_vats if i['percentage'] == tax.amount), 0)

    @api.model_create_multi
    def create(self, vals_list):
        taxes = super().create(vals_list)
        taxes.get_vat_definition_export_id()
        return taxes

    def write(self, values):
        taxes = super().write(values)
        if 'amount' in values:
            self.get_vat_definition_export_id()
        return taxes

    def get_vat_definition_export_id(self):
        """ This method is used to ensure that the export definition ID is set for all taxes that are created or updated. specifically for invidual circumstances where the export ID is not set yet."""
        for tax in self._get_german_tax():
            # Sort to prioritize standard VATs (lower IDs) over historical ones (higher IDs) when selecting the export ID
            sorted_vats = sorted(tax.company_id.l10n_de_vat_export_data, key=lambda x: x['vat_definition_export_id'])
            if not next((i['vat_definition_export_id'] for i in sorted_vats if i['percentage'] == tax.amount), 0):
                # For individual circumstances we have to create a new VAT definition with ID above 1000
                vat_definition_export_id = tax.amount + 1000
                new_vat_response = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('PUT', f'/vat_definitions/{vat_definition_export_id}', {"percentage": tax.amount})
                if new_vat_response.status_code == 200:
                    tax.l10n_de_vat_definition_export_identifier = new_vat_response.json().get("vat_definition_export_id", 0)
                    tax.company_id.l10n_de_update_vat_export_data()

    def _get_german_tax(self):
        return self.filtered(lambda t: t.company_id.is_country_germany and t.company_id.l10n_de_fiskaly_api_secret and t.company_id.l10n_de_vat_export_data)
