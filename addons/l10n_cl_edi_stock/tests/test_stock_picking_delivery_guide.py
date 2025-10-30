# -*- coding: utf-8 -*-
import base64
import logging
from freezegun import freeze_time
from lxml import etree
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import tagged, Form
from odoo.tools import misc
from odoo.addons.l10n_cl_edi_stock.tests.common import TestL10nClEdiStockCommon
from odoo.addons.l10n_cl_edi.tests.common import _check_with_xsd_patch, _is_valid_certificate

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
@patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
@patch('odoo.addons.certificate.models.certificate.CertificateCertificate._compute_is_valid', _is_valid_certificate)
class TestL10nClEdiStock(TestL10nClEdiStockCommon):

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_edi_delivery_with_taxes_from_inventory(self):
        picking = self.env['stock.picking'].create({
            'name': 'Test Delivery Guide',
            'partner_id': self.chilean_partner_a.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.warehouse.out_type_id.id,
        })
        self.env['stock.move'].create({
            'product_id': self.product_with_taxes_a.id,
            'product_uom': self.product_with_taxes_a.uom_id.id,
            'product_uom_qty': 10.00,
            'quantity': 10.00,
            'procure_method': 'make_to_stock',
            'picking_id': picking.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'company_id': self.env.company.id
        })
        self.env['stock.move'].create({
            'product_id': self.product_with_taxes_b.id,
            'product_uom': self.product_with_taxes_b.uom_id.id,
            'product_uom_qty': 1,
            'quantity': 1,
            'procure_method': 'make_to_stock',
            'picking_id': picking.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'company_id': self.env.company.id
        })
        picking.button_validate()
        picking.create_delivery_guide()

        self.assertEqual(picking.l10n_cl_dte_status, False)
        self.assertEqual(picking.l10n_cl_draft_status, True)

        picking.l10n_latam_document_number = 100
        picking.l10n_cl_confirm_draft_delivery_guide()

        self.assertEqual(picking.l10n_latam_document_number, '100')
        self.assertEqual(picking.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi_stock/tests/expected_dtes/delivery_guide_products_with_taxes.xml').read()

        self.assertXmlTreeEqual(
            etree.fromstring(base64.b64decode(picking.l10n_cl_sii_send_file.with_context(bin_size=False).datas)),
            etree.fromstring(xml_expected_dte.encode())
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_edi_delivery_with_taxes_from_sale_order(self):
        so_vals = {
            'partner_id': self.chilean_partner_a.id,
            'order_line': [
                (0, 0, {
                'name': self.product_with_taxes_a.name,
                'product_id': self.product_with_taxes_a.id,
                'product_uom_qty': 10.0,
                'price_unit': self.product_with_taxes_a.list_price
                }),
                (0, 0, {
                'name': self.product_with_taxes_b.name,
                'product_id': self.product_with_taxes_b.id,
                'product_uom_qty': 1.0,
                'price_unit': self.product_with_taxes_b.list_price
                })
            ],
            'company_id': self.env.company.id,
        }
        sale_order = self.env['sale.order'].create(so_vals)
        sale_order.action_confirm()

        picking = sale_order.picking_ids[0]
        picking.action_assign()
        picking.move_ids[0].write({'quantity': 10})
        picking.move_ids[1].write({'quantity': 1})
        picking.button_validate()

        picking.create_delivery_guide()

        self.assertEqual(picking.l10n_cl_dte_status, False)
        self.assertEqual(picking.l10n_cl_draft_status, True)

        picking.l10n_latam_document_number = 100
        picking.l10n_cl_confirm_draft_delivery_guide()

        self.assertEqual(picking.l10n_latam_document_number, '100')
        self.assertEqual(picking.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi_stock/tests/expected_dtes/delivery_guide_products_with_taxes.xml').read()

        self.assertXmlTreeEqual(
            etree.fromstring(base64.b64decode(picking.l10n_cl_sii_send_file.with_context(bin_size=False).datas)),
            etree.fromstring(xml_expected_dte.encode())
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_edi_delivery_without_taxes_from_sale_order(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.chilean_partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_without_taxes_a.name,
                    'product_id': self.product_without_taxes_a.id,
                    'product_uom_qty': 5.0,
                    'price_unit': self.product_without_taxes_a.list_price,
                    'discount': 10.00,
                    'tax_ids': [],
                }),
                (0, 0, {
                    'name': self.product_without_taxes_b.name,
                    'product_id': self.product_without_taxes_b.id,
                    'product_uom_qty': 10.0,
                    'price_unit': self.product_without_taxes_b.list_price,
                    'tax_ids': [],
                })
            ],
        })
        sale_order.action_confirm()

        picking = sale_order.picking_ids[0]
        picking.action_assign()
        picking.move_ids[0].write({'quantity': 5})
        picking.move_ids[1].write({'quantity': 10})
        picking.button_validate()

        picking.create_delivery_guide()

        self.assertEqual(picking.l10n_cl_dte_status, False)
        self.assertEqual(picking.l10n_cl_draft_status, True)

        picking.l10n_latam_document_number = 100
        picking.l10n_cl_confirm_draft_delivery_guide()

        self.assertEqual(picking.l10n_latam_document_number, '100')
        self.assertEqual(picking.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi_stock/tests/expected_dtes/delivery_guide_products_without_taxes.xml').read()

        self.assertXmlTreeEqual(
            etree.fromstring(base64.b64decode(picking.l10n_cl_sii_send_file.with_context(bin_size=False).datas)),
            etree.fromstring(xml_expected_dte.encode())
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_edi_delivery_with_references_from_sale_order(self):
        """ Tests that references are copied over from sale orders to pickings
        and are properly exported to DTE documents. Since this is performed in the
        last order, we test it via pick_pack_ship."""
        self.warehouse.delivery_steps = 'pick_pack_ship'

        purchase_reference_doc_id = self.env.ref('l10n_cl.dc_odc')
        reference_template = {
            'origin_doc_number': 'PO00273',
            'l10n_cl_reference_doc_type_id': purchase_reference_doc_id.id,
            'reason': 'Cross Reference To Purchase Order',
            'date': fields.Date.from_string('2019-10-24'),
        }

        sale_order = self.env['sale.order'].create({
            'partner_id': self.chilean_partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_without_taxes_a.name,
                    'product_id': self.product_without_taxes_a.id,
                    'product_uom_qty': 5.0,
                    'price_unit': self.product_without_taxes_a.list_price,
                    'discount': 10.00,
                    'tax_ids': [],
                }),
                (0, 0, {
                    'name': self.product_without_taxes_b.name,
                    'product_id': self.product_without_taxes_b.id,
                    'product_uom_qty': 10.0,
                    'price_unit': self.product_without_taxes_b.list_price,
                    'tax_ids': [],
                }),
            ],
            'client_order_ref': 'PO00273',
        })
        sale_order.action_confirm()

        picking = sale_order.picking_ids[0]

        self.assertRecordValues(picking.l10n_cl_reference_ids, [{
            **reference_template,
            'picking_id': picking.id,
        }])

        picking.action_assign()
        picking.move_ids[0].write({'quantity': 5})
        picking.move_ids[1].write({'quantity': 10})
        picking.button_validate()
        next_transfer = picking._get_next_transfers()

        self.assertRecordValues(next_transfer.l10n_cl_reference_ids, [{
            **reference_template,
            'picking_id': next_transfer.id,
        }])

        next_transfer.button_validate()
        final_delivery = next_transfer._get_next_transfers()

        self.assertRecordValues(final_delivery.l10n_cl_reference_ids, [{
            **reference_template,
            'picking_id': final_delivery.id,
        }])

        final_delivery.button_validate()
        final_delivery.create_delivery_guide()

        self.assertEqual(final_delivery.l10n_cl_dte_status, False)
        self.assertEqual(final_delivery.l10n_cl_draft_status, True)

        final_delivery.l10n_latam_document_number = 100
        final_delivery.l10n_cl_confirm_draft_delivery_guide()

        self.assertEqual(final_delivery.l10n_latam_document_number, '100')
        self.assertEqual(final_delivery.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi_stock/tests/expected_dtes/delivery_guide_products_with_reference.xml').read()

        self.assertXmlTreeEqual(
            etree.fromstring(base64.b64decode(final_delivery.l10n_cl_sii_send_file.with_context(bin_size=False).datas)),
            etree.fromstring(xml_expected_dte.encode()),
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_edi_delivery_guide_no_price(self):
        copy_chilean_partner = self.chilean_partner_a.copy()
        copy_chilean_partner.write({'l10n_cl_delivery_guide_price': 'none'})
        so_vals = {
            'partner_id': copy_chilean_partner.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_with_taxes_a.name,
                    'product_id': self.product_with_taxes_a.id,
                    'product_uom_qty': 3.0,
                    'price_unit': self.product_with_taxes_a.list_price,
                    'discount': 10.00,
                })
            ],
            'company_id': self.env.company.id,
        }
        sale_order = self.env['sale.order'].create(so_vals)
        sale_order.action_confirm()

        picking = sale_order.picking_ids[0]
        picking.action_assign()
        picking.move_ids[0].write({'quantity': 3})
        picking.button_validate()

        picking.create_delivery_guide()

        self.assertEqual(picking.l10n_cl_dte_status, False)
        self.assertEqual(picking.l10n_cl_draft_status, True)

        picking.l10n_latam_document_number = 100
        picking.l10n_cl_confirm_draft_delivery_guide()

        self.assertEqual(picking.l10n_latam_document_number, '100')
        self.assertEqual(picking.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi_stock/tests/expected_dtes/delivery_guide_no_price.xml').read()

        self.assertXmlTreeEqual(
            etree.fromstring(base64.b64decode(picking.l10n_cl_sii_send_file.with_context(bin_size=False).datas)),
            etree.fromstring(xml_expected_dte.encode())
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_edi_delivery_guide_report_pdf_line_amounts_no_demand(self):
        """ Test the amounts (total & unit price) computed for Delivery Guide SII DTE report
            when a stock move line has 0 as demand quantity.
         """
        uom_unit = self.env.ref('uom.product_uom_unit')
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'uom_id': uom_unit.id,
            'is_storable': True,
            'list_price': 100.0,
            'taxes_id': [],
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'uom_id': uom_unit.id,
            'is_storable': True,
            'list_price': 30.0,
            'taxes_id': [],
        })
        product_c = self.env['product.product'].create({
            'name': 'Product C',
            'uom_id': uom_unit.id,
            'is_storable': True,
            'list_price': 50.0,
            'taxes_id': [],
        })
        # create a SO with Product A and use another unit price
        so = self.env['sale.order'].create({
            'partner_id': self.chilean_partner_a.id,
            'order_line': [Command.create({
                'product_id': product_a.id,
                'product_uom_qty': 2.0,
                'price_unit': 150.0,
            })],
            'company_id': self.env.company.id,
        })
        so.action_confirm()

        picking = so.picking_ids
        picking_form = Form(picking)
        # add a stock move with Product B manually (not linked to a SO line)
        with picking_form.move_ids.new() as move:
            move.product_id = product_b
            move.product_uom_qty = 1.0
        # add a stock move with Product C without "product_uom_qty" (demand == 0)
        with picking_form.move_ids.new() as move:
            move.product_id = product_c
        picking_form.save()
        move_a = picking.move_ids[0]
        move_b = picking.move_ids[1]
        move_c = picking.move_ids[2]
        move_a.quantity = 1.0
        move_b.quantity = 2.0
        move_c.quantity = 3.0
        # generate the values used by "Delivery Guide SII DTE 52 (CL)"
        pdf_values = picking._prepare_pdf_values()
        line_amounts = pdf_values['total_line_amounts']
        # amounts for Product A are computed from SO line
        self.assertEqual(line_amounts[move_a]['total_amount'], 150.0)
        self.assertEqual(line_amounts[move_a]['price_unit'], 150.0)
        # amounts for Product B and Product C are computed from product
        self.assertEqual(line_amounts[move_b]['total_amount'], 60.0)
        self.assertEqual(line_amounts[move_b]['price_unit'], 30.0)
        self.assertEqual(line_amounts[move_c]['total_amount'], 150.0)
        self.assertEqual(line_amounts[move_c]['price_unit'], 50.0)

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_edi_delivery_guide_report_pdf_withholding_taxes(self):
        """ Test withholding taxes are correctly collected in pdf values
        """
        tax_19 = self.env['account.tax'].search([
            ('name', '=', 'IVA 19% Venta'),
            ('company_id', '=', self.env.company.id)])
        tax_wh = self.env['account.tax'].search([
            ('name', '=', 'Beb. Analc. 10% (Ventas)'),
            ('company_id', '=', self.env.company.id)])

        uom_unit = self.env.ref('uom.product_uom_unit')
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'uom_id': uom_unit.id,
            'is_storable': True,
            'list_price': 100.0,
            'taxes_id': [Command.set((tax_19 | tax_wh).ids)],
        })

        picking = self.env['stock.picking'].create({
            'name': 'Test Delivery Guide',
            'partner_id': self.chilean_partner_a.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.warehouse.out_type_id.id,
        })
        self.env['stock.move'].create({
            'product_id': product_a.id,
            'product_uom_qty': 10.00,
            'quantity': 10.00,
            'procure_method': 'make_to_stock',
            'picking_id': picking.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        })

        pdf_values = picking._prepare_pdf_values()
        expected_values = [{'tax_code': 27, 'tax_percent': 10.0, 'tax_name': 'ILA', 'tax_amount': 100.0}]
        self.assertEqual(pdf_values['withholdings'], expected_values)

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_delivery_guide_qtyitem_matches_move_quantity(self):
        """
        Ensure that the generated XML for a delivery guide includes the correct
        quantity (`QtyItem`) taken from the stock move.
        """
        picking = self.env['stock.picking'].create({
            'name': 'Test Delivery Guide',
            'partner_id': self.chilean_partner_a.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'picking_type_id': self.warehouse.out_type_id.id,
        })
        self.env['stock.move'].create({
            'product_id': self.product_with_taxes_a.id,
            'product_uom': self.product_with_taxes_a.uom_id.id,
            'product_uom_qty': 10.00,
            'quantity': 8.00,
            'procure_method': 'make_to_stock',
            'picking_id': picking.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'company_id': self.env.company.id
        })

        picking.button_validate()
        picking.create_delivery_guide()
        picking.l10n_latam_document_number = 100
        picking.l10n_cl_confirm_draft_delivery_guide()

        xml_bytes = base64.b64decode(picking.l10n_cl_sii_send_file.with_context(bin_size=False).datas)
        root = etree.fromstring(xml_bytes)
        qty = root.find(".//sii:QtyItem", namespaces={"sii": "http://www.sii.cl/SiiDte"})

        self.assertIsNotNone(qty, "QtyItem tag should exist in XML")
        self.assertEqual(qty.text, "8.000000")
