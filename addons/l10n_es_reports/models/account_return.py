from odoo import models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _get_vat_closing_entry_additional_domain(self):
        # EXTENDS account_reports
        domain = super()._get_vat_closing_entry_additional_domain()
        if self.type_external_id == 'l10n_es_reports.es_mod303_tax_return_type':
            mod_tags = self.env.ref('l10n_es.mod_303').line_ids.expression_ids._get_matching_tags()
            domain.append(('tax_tag_ids', 'in', mod_tags.ids))
        return domain
