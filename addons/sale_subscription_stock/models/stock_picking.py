# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        picking_per_so = defaultdict(lambda: self.env['stock.picking'])
        for move in self.move_ids:
            picking = move.picking_id
            sale_order = picking.sale_id
            # Creates new SO line only when pickings linked to a sale order and
            # for moves with qty. done and not already linked to a SO line.
            if not sale_order or move.location_dest_id.usage != 'customer' or not move.picked:
                continue

            if sale_order.subscription_state == "7_upsell":
                # we need to compute the parent id, because it was not computed when we created the SOL in _subscription_update_line_data
                self.env.add_to_compute(self.env['sale.order.line']._fields['parent_line_id'], move.sale_line_id)
                for line in move.sale_line_id:
                    if line.parent_line_id:
                        line.parent_line_id.qty_delivered += line.qty_delivered
            elif sale_order.subscription_state and sale_order.id not in picking_per_so:
                for sol in sale_order.order_line:
                    line_invoiced_date = sol.last_invoiced_date
                    order_invoice_date = sol.order_id.invoice_ids and sol.order_id.last_invoice_date and sol.order_id.last_invoice_date - relativedelta(days=1)
                    last_invoiced_date = line_invoiced_date or order_invoice_date
                    if last_invoiced_date and picking.date_done.date() <= last_invoiced_date:
                        picking_per_so[sol.order_id.id] += move.picking_id

        for so_id, moves in picking_per_so.items():
            order = self.env['sale.order'].browse(so_id)
            unique_moves = set(moves)
            order._post_subscription_activity(
                record=unique_moves,
                summary=self.env._("Delivered Product(s) (Already Invoiced)"),
                explanation=self.env._("New picking has been confirmed"),
            )
        return res
