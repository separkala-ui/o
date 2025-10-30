from odoo import fields, models, _


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _check_suite_annual_closing(self, check_codes_to_ignore):
        checks = super()._check_suite_annual_closing(check_codes_to_ignore)

        if 'check_fixed_assets' not in check_codes_to_ignore:
            domain = [
                ('company_id', 'in', self.company_ids.ids),
                ('state', '=', 'open'),
                ('depreciation_move_ids', '!=', False),
                ('depreciation_move_ids.date', '<=', fields.Date.to_string(self.date_to)),
                ('depreciation_move_ids.date', '>=', fields.Date.to_string(self.date_from)),
            ]
            fixed_assets_exist = self.env['account.asset'].sudo().search_count(domain, limit=1)
            if not fixed_assets_exist:
                checks.append({
                    'name': _("Fixed Assets"),
                    'message': _("Odoo manages depreciation for your fixed assets. No depreciation was recorded for this period. Ensure assets are properly registered for automatic depreciation calculation."),
                    'code': 'check_fixed_assets',
                    'result': 'todo',
                })
        return checks
