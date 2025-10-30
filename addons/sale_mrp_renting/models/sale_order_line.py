# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        qty = super()._get_qty_procurement(previous_product_uom_qty)
        if self.is_rental and self.env['res.groups']._is_feature_enabled('sale_stock_renting.group_rental_stock_picking') and 'phantom' in self.product_id.bom_ids.mapped('type'):
            bom = self.env['mrp.bom']._bom_find(self.product_id, bom_type='phantom')[self.product_id]
            outgoing_moves = self.move_ids.filtered(lambda m: m.location_dest_id == m.company_id.rental_loc_id and m.state != 'cancel' and m.location_dest_usage != 'inventory' and m.product_id in bom.bom_line_ids.product_id)
            filters = {
                'incoming_moves': lambda m: m.location_dest_id == m.company_id.rental_loc_id and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                'outgoing_moves': lambda m: m.location_dest_id != m.company_id.rental_loc_id and m.to_refund
            }
            order_qty = previous_product_uom_qty.get(self.id, 0) if previous_product_uom_qty else self.product_uom_qty
            order_qty = self.product_uom_id._compute_quantity(order_qty, bom.product_uom_id)
            qty_to_compute = outgoing_moves._compute_kit_quantities(self.product_id, order_qty, bom, filters)
            qty = bom.product_uom_id._compute_quantity(qty_to_compute, self.product_uom_id)
        return qty

    def _compute_qty_delivered(self):
        if not self._are_rental_pickings_enabled():
            return super()._compute_qty_delivered()
        todo_ids = []
        self.fetch(['is_rental', 'product_id'])
        for line in self:
            product = line.product_id
            if not (line.is_rental and 'phantom' in product.bom_ids.mapped('type')):
                todo_ids.append(line.id)
            elif outgoing_done_moves := line.move_ids.filtered(
                lambda m: m.state == 'done' and m.location_dest_id == m.company_id.rental_loc_id,
            ):
                bom = self.env['mrp.bom']._bom_find(product, bom_type='phantom')[product]
                filters = {
                    'incoming_moves': lambda m: m.location_id == m.company_id.rental_loc_id,
                    'outgoing_moves': lambda m: m.location_dest_id == m.company_id.rental_loc_id,
                }
                amount_kits_delivered = outgoing_done_moves._compute_kit_quantities(
                    product, line.product_uom_qty, bom, filters,
                )
                # Because we only use outgoing moves, it will always return a negative value
                line.qty_delivered = -amount_kits_delivered
            else:
                line.qty_delivered = 0
        return super(SaleOrderLine, self.browse(todo_ids))._compute_qty_delivered()
