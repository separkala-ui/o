from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_jo_annual_leave_type_id = fields.Many2one(related="company_id.l10n_jo_annual_leave_type_id", readonly=False)
