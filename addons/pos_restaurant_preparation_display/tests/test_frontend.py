# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_restaurant.tests import test_frontend
from odoo.addons.pos_enterprise.tests.test_frontend import TestPreparationDisplayHttpCommon
from unittest.mock import patch
import odoo.tests
import json


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(test_frontend.TestFrontendCommon, TestPreparationDisplayHttpCommon):
    def test_01_preparation_display_resto(self):
        self.pdis.write({
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        # open a session, the /pos/ui controller will redirect to it
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationDisplayTourResto')

        self.start_pdis_tour('PreparationDisplayFrontEndCancelTour')

        # Order 1 should have 2 preparation orderlines (Coca-Cola and Water)
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000001')], limit=1)
        pdis_order1 = self.env['pos.prep.order'].search([('pos_order_id', '=', order1.id)], limit=1)
        self.assertEqual(len(pdis_order1.prep_line_ids), 2, "Should have 2 preparation orderlines")

        # Order 2 should have 1 preparation orderline (Coca-Cola)
        order2 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000002')], limit=1)
        pdis_order2 = self.env['pos.prep.order'].search([('pos_order_id', '=', order2.id)], limit=1)
        self.assertEqual(len(pdis_order2.prep_line_ids), 1, "Should have 1 preparation orderline")
        self.assertEqual(pdis_order2.prep_line_ids.quantity, 1, "Should have 1 quantity of Coca-Cola")

        # Order 3 should have 3 preparation orderlines (Coca-Cola, Water and Minute Maid)
        # with one cancelled Minute Maid
        order3 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000003')], limit=1)
        pdis_order3 = self.env['pos.prep.order'].search([('pos_order_id', '=', order3.id)], limit=1)
        cancelled_orderline = pdis_order3.prep_line_ids.filtered(lambda x: x.product_id.name == 'Minute Maid')
        self.assertEqual(cancelled_orderline.cancelled, 1, "Should have 1 cancelled Minute Maid orderline")
        self.assertEqual(cancelled_orderline.product_id.name, 'Minute Maid', "Cancelled orderline should be Minute Maid")

    def test_02_preparation_display_resto(self):
        self.pdis.write({
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        # open a session, the /pos/ui controller will redirect to it
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationDisplayTourResto2')

        # Order 1 should have 1 preparation orderlines (Coca-Cola) with quantity 2
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000001')], limit=1)
        prep_line = self.env['pos.prep.line'].search([
            ('prep_order_id.pos_order_id', '=', order1.id),
        ])
        self.assertEqual(len(prep_line), 2)
        self.assertEqual(sum(prep_line.mapped('quantity')), 2)

    def test_preparation_display_with_internal_note(self):
        self.pdis.write({
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationDisplayTourInternalNotes')

        self.start_pdis_tour('PreparationDisplayFrontEndNoteTour')

        # Order 1 should have 2 preparation orderlines (Coca-Cola and Water)
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000001')], limit=1)
        pdis_order1 = self.env['pos.prep.order'].search([('pos_order_id', '=', order1.id)])
        self.assertEqual(len(pdis_order1.prep_line_ids), 2, "Should have 2 preparation orderlines")
        self.assertEqual(pdis_order1.prep_line_ids[0].quantity, 1)
        self.assertEqual(json.loads(pdis_order1.prep_line_ids[0].internal_note)[0]['text'], "Test Internal Notes")
        self.assertEqual(pdis_order1.prep_line_ids[1].quantity, 1)
        self.assertEqual(pdis_order1.prep_line_ids[1].internal_note, "[]")

    def test_cancel_order_notifies_display(self):
        category = self.env['pos.category'].create({'name': 'Food'})
        self.env['product.product'].create({
            'name': 'Test Food',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': category,
        })
        self.pdis.write({
            'pos_config_ids': [(4, self.pos_config.id)],
            'category_ids': category,
        })

        notifications = []

        def _send_load_orders_message(self, sound, notification, orderId):
            notifications.append(self.id)

        # open a session, the /pos/ui controller will redirect to it
        with patch('odoo.addons.pos_enterprise.models.pos_prep_display.PosPrepDisplay._send_load_orders_message', new=_send_load_orders_message):
            self.pos_config.printer_ids.unlink()
            self.pos_config.with_user(self.pos_user).open_ui()
            self.start_pos_tour('PreparationDisplayCancelOrderTour')

        # Should receive 2 notifications, 1 placing the order, 1 cancelling it
        self.assertEqual(notifications.count(self.pdis.id), 2)

    def test_payment_does_not_cancel_display_orders(self):
        self.pdis.write({
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PreparationDisplayPaymentNotCancelDisplayTour', login="pos_user")
        pos_order = self.env['pos.order'].search([], limit=1)
        pdis_order = self.env['pos.prep.order'].search(
            [('pos_order_id', '=', pos_order.id)]
        )
        pdis_lines = pdis_order.prep_line_ids
        self.assertEqual(len(pdis_lines), 2)
        self.assertEqual(pdis_lines[0].quantity, 2.0)
        self.assertEqual(pdis_lines[0].cancelled, 1.0)
        self.assertEqual(pdis_lines[1].quantity, 2.0)
        self.assertEqual(pdis_lines[1].cancelled, 0.0)

    def test_update_internal_note_of_order(self):
        category = self.env['pos.category'].create({'name': 'Test-cat'})
        product_1, product_2 = self.env['product.product'].create([{
            'name': 'Test Food',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': category,
        }, {
            'name': 'Demo Food',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': category,
        }])

        self.env['pos.prep.display'].create({
            'name': 'Preparation Display (Food only)',
            'pos_config_ids': [(4, self.pos_config.id)],
            'category_ids': category,
        })

        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'test_update_internal_note_of_order', login='pos_admin')

        pos_order = self.env['pos.order'].search([('session_id', 'in', self.pos_config.session_ids.ids)], limit=1)
        order_lines = self.env['pos.prep.order'].search([('pos_order_id', '=', pos_order.id)], limit=1).prep_line_ids
        self.assertEqual(len(order_lines), 2)
        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(pos_order.amount_paid, product_2.list_price)

        self.assertEqual(order_lines[0]['product_id'].id, product_2.id)
        self.assertEqual(order_lines[0]['quantity'], 1)
        self.assertEqual(order_lines[0]['cancelled'], 0)

        self.assertEqual(order_lines[1]['product_id'].id, product_1.id)
        self.assertEqual(order_lines[1]['internal_note'], '[]')
        self.assertEqual(order_lines[1]['quantity'], 1)
        self.assertEqual(order_lines[1]['cancelled'], 1)

    def test_receipt_screen_after_unsent_order_dialog(self):
        self.env['pos.prep.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.pos_config.printer_ids.unlink()
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_receipt_screen_after_unsent_order_dialog')
        order = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000001')], limit=1)
        pdis_order = self.env['pos.prep.order'].search([('pos_order_id', '=', order.id)], limit=1)
        self.assertEqual(len(pdis_order.prep_line_ids), 1, "Should have 1 preparation orderline")
        self.assertEqual(pdis_order.prep_line_ids.quantity, 1, "Should have 1 quantity of Coca-Cola")

    def test_order_preparation(self):
        self.env['pos.prep.display'].create({
            'name': 'Preparation Display (Food only)',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        self.pos_config.write({'module_pos_restaurant': False})
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'test_order_preparation_preparation_printer', login='pos_admin')

        current_session = self.pos_config.current_session_id
        current_session.post_closing_cash_details(0)
        current_session.close_session_from_ui()
        self.pos_config.write({'printer_ids': [], 'is_order_printer': False, 'module_pos_restaurant': True})
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'test_order_preparation_preparation_display', login='pos_admin')
        last_orders = self.pos_config.current_session_id.order_ids

        first_order = last_orders[1]
        preparation_change = self.env['pos.prep.order'].search([('pos_order_id', '=', first_order.id)])
        product_quantity = preparation_change.prep_line_ids.mapped('quantity')
        product_cancelled = preparation_change.prep_line_ids.mapped('cancelled')
        self.assertEqual(product_cancelled, product_quantity, "A one-time order must be successfully cancelled.")

        second_order = last_orders[0]
        preparation_change = self.env['pos.prep.order'].search([('pos_order_id', '=', second_order.id)])
        product_quantity = preparation_change.prep_line_ids.mapped('quantity')
        product_cancelled = preparation_change.prep_line_ids.mapped('cancelled')
        self.assertEqual(product_cancelled, product_quantity, "A two-times order must be successfully cancelled")
