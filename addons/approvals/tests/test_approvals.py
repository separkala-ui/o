# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import common, Form, new_test_user
from odoo.exceptions import AccessError, UserError


class TestRequest(common.TransactionCase):
    def test_compute_request_status(self):
        category_test = self.env.ref('approvals.approval_category_data_business_trip')
        requester_user = self.env.ref('base.user_admin')
        record = self.env['approval.request'].create({
            'name': 'test request',
            'request_owner_id': requester_user.id,
            'category_id': category_test.id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })
        first_approver = self.env['approval.approver'].create({
            'user_id': 1,
            'request_id': record.id,
            'status': 'new'})
        second_approver = self.env['approval.approver'].create({
            'user_id': 2,
            'request_id': record.id,
            'status': 'new'})
        record.approver_ids = (first_approver | second_approver)

        self.assertEqual(record.request_status, 'new')

        record.action_confirm()

        # Test case 1: Min approval = 1
        self.assertEqual(record.request_status, 'pending')
        record.action_approve(first_approver)
        self.assertEqual(record.request_status, 'approved')
        record.action_approve(second_approver)
        self.assertEqual(record.request_status, 'approved')
        record.action_withdraw(first_approver)
        self.assertEqual(record.request_status, 'approved')
        record.action_refuse(first_approver)
        self.assertEqual(record.request_status, 'refused')

        # Test case 2: Min approval = 1
        category_test.approval_minimum = 2
        record.action_withdraw(first_approver)
        record.action_withdraw(second_approver)
        self.assertEqual(record.request_status, 'pending')
        record.action_approve(first_approver)
        self.assertEqual(record.request_status, 'pending')
        record.action_approve(second_approver)
        self.assertEqual(record.request_status, 'approved')
        record.action_withdraw(second_approver)
        self.assertEqual(record.request_status, 'pending')
        record.action_refuse(second_approver)
        self.assertEqual(record.request_status, 'refused')

        # Test case 3: Check that cancel is erasing the old validations
        record.action_cancel()
        self.assertEqual(first_approver.status, 'cancel')
        self.assertEqual(second_approver.status, 'cancel')
        self.assertEqual(record.request_status, 'cancel')

        # Test case 4: Set the approval request to draft
        record.action_draft()
        self.assertEqual(first_approver.status, 'new')
        self.assertEqual(second_approver.status, 'new')
        self.assertEqual(record.request_status, 'new')

        # Test case 5: Set min approval to an impossible value to reach
        category_test.approval_minimum = 3
        with self.assertRaises(UserError):
            record.action_confirm()
        self.assertEqual(record.request_status, 'new')

    def test_compute_request_status_with_required(self):
        category_test = self.env.ref('approvals.approval_category_data_business_trip')
        requester_user = self.env.ref('base.user_admin')
        record = self.env['approval.request'].create({
            'name': 'test request',
            'request_owner_id': requester_user.id,
            'category_id': category_test.id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })
        first_approver = self.env['approval.approver'].create({
            'user_id': 1,
            'request_id': record.id,
            'status': 'new',
            'required': True})
        second_approver = self.env['approval.approver'].create({
            'user_id': 2,
            'request_id': record.id,
            'status': 'new'})
        record.approver_ids = (first_approver | second_approver)

        self.assertEqual(record.request_status, 'new')

        record.action_confirm()

        # Min approval = 1 but first approver IS required
        self.assertEqual(record.request_status, 'pending')
        record.action_approve(second_approver)
        # Min approval is met but required approvals are not
        self.assertEqual(record.request_status, 'pending')
        record.action_approve(first_approver)
        self.assertEqual(record.request_status, 'approved')

        # Min approval = 2
        category_test.approval_minimum = 2
        record.action_withdraw(first_approver)
        record.action_withdraw(second_approver)
        self.assertEqual(record.request_status, 'pending')
        record.action_approve(first_approver)
        # All required approvals are met but not the minimal approval count
        self.assertEqual(record.request_status, 'pending')
        record.action_approve(second_approver)
        self.assertEqual(record.request_status, 'approved')

    def test_product_line_compute_uom(self):
        category_test = self.env.ref('approvals.approval_category_data_business_trip')
        uom = self.env.ref('uom.product_uom_dozen')
        product = self.env['product.product'].create({
            'name': 'foo',
            'uom_id': uom.id,
        })
        approval = self.env['approval.request'].create({
            'category_id': category_test.id,
            'product_line_ids': [
                Command.create({'product_id': product.id})
            ],
        })
        self.assertEqual(approval.product_line_ids.description, 'foo')
        self.assertEqual(approval.product_line_ids.product_uom_id, uom)

    def test_unlink_approval(self):
        """
        There is no error when unlinking a draft request with a document attached
        or a binary field filled.
        """
        approval = self.env['approval.request'].create({
            'name': 'test request',
            'category_id': self.env.ref('approvals.approval_category_data_business_trip').id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })
        self.env['ir.attachment'].create({
            'name': 'test.file',
            'res_id': approval.id,
            'res_model': 'approval.request',
        })

        self.env['ir.model.fields'].create({
            'name': 'x_test_field',
            'model_id': self.env.ref('approvals.model_approval_request').id,
            'ttype': 'binary',
        })
        approval.x_test_field = 'test'
        approval.unlink()

    def test_unlink_multiple_approvals_with_product_line(self):
        """
        There is no error when unlinking a multiple approval requests with a
        product line.
        """
        approvals = self.env['approval.request'].create([{
            'name': 'Approval Request 1',
            'category_id': self.env.ref('approvals.approval_category_data_borrow_items').id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland',
        }, {
            'name': 'Approval Request 1',
            'category_id': self.env.ref('approvals.approval_category_data_borrow_items').id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testitems',
        }])
        product_line = self.env['approval.product.line'].create({
            'approval_request_id': approvals[0].id,
            'description': "Description",
        })

        approvals.unlink()
        self.assertFalse(product_line.exists())
        self.assertFalse(approvals.exists())

    def test_request_with_automated_sequence(self):
        approval_category = self.env['approval.category'].create({
            'name': 'Test Category',
            'automated_sequence': True,
            'sequence_code': '1234',
        })

        request_form = Form(self.env['approval.request'])
        request_form.category_id = approval_category
        approval_request = request_form.save()
        self.assertEqual( approval_request.name, '123400001')

    def test_approval_request_change_category(self):
        user1 = new_test_user(self.env, login='user1')
        user2 = new_test_user(self.env, login='user2')
        category1 = self.env['approval.category'].create({
            'name': 'Test category 1',
            'approver_ids': [
                Command.create({'user_id': user1.id}),
                Command.create({'user_id': user2.id}),
            ]
        })
        category2 = self.env['approval.category'].create({
            'name': 'Test category 2',
            'approver_ids': [
                Command.create({'user_id': user1.id})
            ]
        })
        approval = self.env['approval.request'].create({
            'name': 'Test request',
            'category_id': category1.id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })
        self.assertEqual(approval.approver_ids.user_id, (user1 + user2))
        approval.write({
            'category_id': category2.id
        })
        self.assertEqual(approval.approver_ids.user_id, user1)

    def test_approval_request_write_approved(self):
        user_1 = new_test_user(self.env, login="user 1", groups="base.group_user")
        user_2 = new_test_user(self.env, login="user 2", groups="base.group_user")

        category_test = self.env.ref('approvals.approval_category_data_business_trip')
        record = self.env['approval.request'].create({
            'name': 'test request',
            'request_owner_id': user_1.id,
            'category_id': category_test.id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })
        first_approver = self.env['approval.approver'].create({
            'user_id': user_2.id,
            'request_id': record.id,
            'status': 'new'
        })
        record.approver_ids = first_approver

        # approval owner can write on his approval
        record.with_user(user_1).write({'amount': 10})

        record.action_confirm()
        self.assertEqual(record.request_status, 'pending')

        record.action_approve(first_approver)

        self.assertEqual(record.request_status, 'approved')
        # approval owner cannot write on approved approval
        with self.assertRaises(AccessError):
            record.with_user(user_1).write({'amount': 20})
        record.with_user(user_2).write({'amount': 20})

        # approval owner can cancel
        record.with_user(user_1).write({'request_status': 'cancel'})
        self.assertEqual(record.request_status, 'cancel')

        record.action_draft()
        self.assertEqual(record.request_status, 'new')

        # approval owner cannot approved his own approval
        with self.assertRaises(AccessError):
            record.with_user(user_1).write({'request_status': 'approved'})

    def test_approval_approvers_access(self):
        user1 = new_test_user(self.env, login='user1')
        user2 = new_test_user(self.env, login='user2')
        user3 = new_test_user(self.env, login='user3', groups='approvals.group_approval_user')
        category1 = self.env['approval.category'].create({
            'name': 'Test category 1',
            'company_id': user1.company_id.id,
            'approver_ids': [
                Command.create({'user_id': user2.id}),
            ]
        })
        approval = self.env['approval.request'].with_user(user1).create({
            'name': 'Test request',
            'request_owner_id': user1.id,
            'category_id': category1.id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })

        # Only an officer can edit an approver
        with self.assertRaises(AccessError):
            approval.approver_ids.with_user(user1).write({'required': True})
        approval.approver_ids.with_user(user3).write({'required': True})
        self.assertTrue(approval.approver_ids.required)

        # Only an officer can add an approver to the request
        with self.assertRaises(AccessError):
            self.env['approval.approver'].with_user(user1).create({'user_id': user3.id, 'request_id': approval.id})
        self.env['approval.approver'].with_user(user3).create({'user_id': user3.id, 'request_id': approval.id})
        self.assertEqual(len(approval.approver_ids), 2)

        approver2 = approval.approver_ids.filtered(lambda a: a.user_id.id == user2.id)
        approver3 = approval.approver_ids.filtered(lambda a: a.user_id.id == user3.id)

        # user1 cannot approve the user 2 approver, but user 2 can
        with self.assertRaises(AccessError):
            approver2.with_user(user1).action_approve()
        approver2.with_user(user2).action_approve()
        self.assertEqual(approver2.status, 'approved')

        # Officer can access, and user2 can access because they are the approver
        approver2.with_user(user2).read()
        approver2.with_user(user3).read()

        # Only officer can read the approvers
        with self.assertRaises(AccessError):
            approver3.with_user(user2).read()
        approver3.with_user(user3).read()

        # Only officer can unlink an approver
        with self.assertRaises(AccessError):
            approver3.with_user(user1).unlink()
        approver3.with_user(user3).unlink()
        self.assertEqual(approval.approver_ids.user_id.id, user2.id)

    def test_user_access_to_admin_approval(self):
        user = new_test_user(self.env, login='user1', groups='base.group_user')
        admin = new_test_user(self.env, login='admin1', groups='approvals.group_approval_manager')
        admin_env = self.env(user=admin)

        category1 = self.env['approval.category'].create({
            'name': 'Test category 1',
            'approver_ids': [
                Command.create({'user_id': admin.id}),
            ]
        })

        private_approval = admin_env['approval.request'].create({
            'name': 'Test request (admin)',
            'request_owner_id': admin.id,
            'category_id': category1.id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })

        approval = admin_env['approval.request'].create({
            'name': 'Test request',
            'request_owner_id': admin.id,
            'category_id': category1.id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            'location': 'testland'
        })
        user_approver = admin_env['approval.approver'].create({
            'user_id': user.id,
            'request_id': approval.id,
        })

        with self.assertRaises(AccessError):
            user_approver.with_user(user).request_id = private_approval
