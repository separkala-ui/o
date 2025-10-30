# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = "account.account"

    fiscal_category_id = fields.Many2one('account.fiscal.category', string='Fiscal Category', check_company=True, index='btree_not_null')
    rate_ids = fields.One2many('account.account.fiscal.rate', 'related_account_id', string='Rate')

    @api.onchange('internal_group')
    def _onchange_internal_group(self):
        if self.internal_group not in ('asset', 'expense', 'income'):
            self.fiscal_category_id = None


class AccountAccountFiscalRate(models.Model):
    _name = 'account.account.fiscal.rate'
    _description = "Fiscal Rate"
    _order = 'date_from desc'

    rate = fields.Float(string='Fiscal Rate (%)', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    related_account_id = fields.Many2one('account.account', string='Account', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
