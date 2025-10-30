# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class SaleCommissionAchievementReport(models.Model):
    _inherit = "sale.commission.achievement.report"

    def _get_sale_rates(self):
        return super()._get_sale_rates() + ['margin']

    def _get_sale_rates_product(self):
        return super()._get_sale_rates_product() + "+ (rules.margin_rate * cr.rate * COALESCE(sol.margin, 0)) / fo.currency_rate"
