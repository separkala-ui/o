# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestPickingBarcodeClientAction(TestBarcodeClientAction):

    def setUp(self):
        super().setUp()

        self.component01 = self.env['product.product'].create({
            'name': 'Compo 01',
            'is_storable': True,
            'barcode': 'compo01',
        })
        self.component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'is_storable': True,
            'barcode': 'compo02',
        })
        self.component_lot = self.env['product.product'].create({
            'name': 'Compo Lot',
            'is_storable': True,
            'barcode': 'compo_lot',
            'tracking': 'lot',
        })

        self.simple_kit = self.env['product.product'].create({
            'name': 'Simple Kit',
            'is_storable': True,
            'barcode': 'simple_kit',
        })
        self.kit_lot = self.env['product.product'].create({
            'name': 'Kit Lot',
            'is_storable': True,
            'barcode': 'kit_lot',
        })

        self.bom_kit_lot = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_lot.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': self.component_lot.id, 'product_qty': 1.0}),
            ],
        })
        self.bom_simple_kit = self.env['mrp.bom'].create({
            'product_tmpl_id': self.simple_kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': self.component02.id, 'product_qty': 1.0}),
            ],
        })

    def test_immediate_receipt_kit_from_scratch_with_tracked_compo(self):
        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_immediate_receipt_kit_from_scratch_with_tracked_compo', login='admin', timeout=180)

        self.assertRecordValues(receipt_picking.move_ids.move_line_ids, [
            {'product_id': self.component01.id, 'qty_done': 3.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component_lot.id, 'qty_done': 3.0, 'lot_name': 'super_lot', 'state': 'done'},
            {'product_id': self.component01.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component02.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
        ])

    def test_planned_receipt_kit_from_scratch_with_tracked_compo(self):
        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_planned_receipt_kit_from_scratch_with_tracked_compo', login='admin', timeout=180)

        self.assertRecordValues(receipt_picking.move_ids.move_line_ids, [
            {'product_id': self.component01.id, 'qty_done': 3.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component_lot.id, 'qty_done': 3.0, 'lot_name': 'super_lot', 'state': 'done'},
            {'product_id': self.component01.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
            {'product_id': self.component02.id, 'qty_done': 1.0, 'lot_name': False, 'state': 'done'},
        ])

    def test_picking_product_with_kit_and_packaging(self):
        """ A picking with a move for a product with a kit BOM and packaging can be processed
        in Barcode
        """
        packaging = self.env['uom.uom'].create({
            'name': 'test packaging',
            'relative_factor': 1.0,
        })
        self.simple_kit.uom_ids = packaging

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_internal.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'product_id': self.simple_kit.id,
                'product_uom_qty': 1.0,
                'product_uom': self.simple_kit.uom_id.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        picking.action_confirm()

        create_vals = []
        for stock_move, component in zip(picking.move_ids, picking.move_ids.mapped('product_id')):
            create_vals.append({
                'product_id': component.id,
                'picking_id': picking.id,
                'move_id': stock_move.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
                'quantity': 1.0,
            })

        self.env['stock.move.line'].create(create_vals)

        url = self._get_client_action_url(picking.id)
        self.start_tour(url, 'test_picking_product_with_kit_and_packaging', login='admin', timeout=180)
        self.assertEqual(picking.state, 'done')

    def test_picking_product_with_kit_and_component(self):
        """ A picking with a kit (comp A + comp B) and a separate move for a component(comp B) should not group the
        two lines (the comp B line linked to the kit and the comp B line from the comp B move) in Barcode
        """
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'group_ids': [(4, grp_lot.id, 0)]})
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_internal.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1.0,
                'product_uom': self.kit_lot.uom_id.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
            }) for product in [self.kit_lot, self.component_lot]],
        })
        picking.action_confirm()
        picking.move_ids.write({'quantity': 1})
        url = self._get_client_action_url(picking.id)
        self.start_tour(url, 'test_picking_product_with_kit_and_component', login='admin', timeout=180)
