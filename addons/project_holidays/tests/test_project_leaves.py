# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import re

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common, freeze_time, Form


@freeze_time('2020-01-01')
class TestProjectLeaves(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.env.user.tz = "Europe/Brussels"

        self.user_hruser = mail_new_test_user(self.env, login='usertest', groups='base.group_user,hr_holidays.group_hr_holidays_user')
        self.employee_hruser = self.env['hr.employee'].create({
            'name': 'Test HrUser',
            'user_id': self.user_hruser.id,
            'tz': 'UTC',
        })

        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'time off',
            'requires_allocation': False,
            'request_unit': 'hour',
        })
        self.project = self.env['project.project'].create({
            'name': "Coucoubre",
        })

    def test_simple_employee_leave(self):

        leave = self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-01-01',
            'request_date_to': '2020-01-01',
        })

        task_1 = self.env['project.task'].create({
            'name': "Task 1",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 1, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 1, 17, 0),
        })
        task_2 = self.env['project.task'].create({
            'name': "Task 2",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 2, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 2, 17, 0),
        })

        self.assertNotEqual(task_1.leave_warning, False,
                            "leave is not validated , but warning for requested time off")

        leave.action_approve()

        self.assertNotEqual(task_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        self.assertNotEqual(task_1.leave_warning.startswith(
            "Test HrUser is on time off on that day"), "single day task, should show date")

        self.assertEqual(task_2.leave_warning, False,
                         "employee is not on leave, no warning")

    def test_multiple_leaves(self):
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-01-06',
            'request_date_to': '2020-01-07',
        }).action_approve()

        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-01-08',
            'request_date_to': '2020-01-10',
        }).action_approve()

        task_1 = self.env['project.task'].create({
            'name': "Task 1",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 6, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 6, 17, 0),
        })

        self.assertNotEqual(task_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        self.assertTrue(task_1.leave_warning.startswith(
            "Test HrUser is on time off from 01/06/2020 to 01/07/2020. \n"), "single day task, should show date")

        task_2 = self.env['project.task'].create({
            'name': "Task 2",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 6, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 7, 17, 0),
        })
        self.assertEqual(task_2.leave_warning,
                         "Test HrUser is on time off from 01/06/2020 to 01/07/2020. \n")

        task_3 = self.env['project.task'].create({
            'name': "Task 3",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 6, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 10, 17, 0),
        })
        self.assertEqual(task_3.leave_warning, "Test HrUser is on time off from 01/06/2020 to 01/10/2020. \n",
                         "should show the start of the 1st leave and end of the 2nd")

    def test_half_day_employee_leave(self):
        self.leave_type.request_unit = 'half_day'
        leave_1, leave_2 = self.env['hr.leave'].create([{
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from':  datetime.datetime(2020, 1, 1, 9, 0),
            'request_date_to':  datetime.datetime(2020, 1, 1, 13, 0),
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        }, {
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': datetime.datetime(2020, 1, 2, 14, 0),
            'request_date_to': datetime.datetime(2020, 1, 2, 18, 0),
            'request_date_from_period': 'pm',
            'request_date_to_period': 'pm',
        }])

        task_1, task_2, task_3 = self.env['project.task'].create([{
            'name': "Task 1",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 1, 9, 0),
            'date_deadline': datetime.datetime(2020, 1, 1, 18, 0),
        }, {
            'name': "Task 2",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 2, 9, 0),
            'date_deadline': datetime.datetime(2020, 1, 2, 18, 0),
        }, {
            'name': "Task 3",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 3, 9, 0),
            'date_deadline': datetime.datetime(2020, 1, 3, 18, 0),
        }])

        self.assertNotEqual(task_1.leave_warning, False,
                            "leave is not validated , but warning for requested time off")
        self.assertNotEqual(task_2.leave_warning, False,
                            "leave is not validated , but warning for requested time off")

        (leave_1 + leave_2).action_approve()
        # there is no direct link with the task, so we invalidate manually
        self.env.invalidate_all()

        self.assertNotEqual(task_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        self.assertEqual(re.sub(r'\s+', ' ', task_1.leave_warning),
            "Test HrUser is on time off on 01/01/2020 from 9:00 AM to 1:00 PM. ")
        self.assertNotEqual(task_2.leave_warning, False,
                            "employee is on leave, should have a warning")
        self.assertEqual(re.sub(r'\s+', ' ', task_2.leave_warning),
            "Test HrUser is on time off on 01/02/2020 from 2:00 PM to 6:00 PM. ")
        self.assertEqual(task_3.leave_warning, False,
                         "employee is not on leave, no warning")

    def test_leave_warning_on_creation(self):
        self.leave_type.request_unit = 'day'
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-01-01',
            'request_date_to': '2020-01-01',
        }).action_approve()

        with Form(self.env['project.task']) as task_form:
            task_form.name = 'Test Task'
            task_form.user_ids = self.employee_hruser.user_id
            task_form.project_id = self.project
            task_form.date_deadline = datetime.datetime(2020, 1, 2)
            task_form.planned_date_begin = datetime.datetime(2020, 1, 1)

            self.assertEqual(task_form.leave_warning, "Test HrUser is on time off on 01/01/2020. \n")

            task_form.planned_date_begin = datetime.datetime(2020, 1, 2)
            self.assertFalse(task_form.leave_warning)

    def test_multicompany_with_time_off_warning(self):
        """
        Ensure that time-off warnings are displayed if multi-company is activated.
        Flow:
            - Create a company(Opoo)
            - Add company(Opoo) to Allowed Companies
            - Create a time-off and validate
            - Create task
            - Check the time-out alert by My company.
            - Check the time-out alert by all Companies(My company + Opoo)
            - Check the time-out alert by Opoo Company.
        """
        company_1 = self.env['res.company'].create({'name': 'Opoo'})
        self.user_hruser.company_ids += company_1
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': '2020-01-06',
            'request_date_to': '2020-01-07',
        }).action_approve()

        task = self.env['project.task'].create({
            'name': "Task",
            'project_id': self.project.id,
            'user_ids': self.user_hruser,
            'planned_date_begin': datetime.datetime(2020, 1, 6, 8, 0),
            'date_deadline': datetime.datetime(2020, 1, 10, 17, 0),
        })
        leave_warning = task.with_context(allowed_company_ids=self.user_hruser.company_ids[1].ids).leave_warning
        self.assertEqual(leave_warning, "Test HrUser is on time off from 01/06/2020 to 01/07/2020. \n",
                        "should show the start of the 6st leave and end of the 7nd")
        leave_warning = task.with_context(allowed_company_ids=self.user_hruser.company_ids.ids).leave_warning
        self.assertEqual(leave_warning, "Test HrUser is on time off from 01/06/2020 to 01/07/2020. \n",
                        "should show the start of the 6st leave and end of the 7nd")
        leave_warning = task.with_context(allowed_company_ids=company_1.ids).leave_warning
        self.assertNotEqual(task.leave_warning, False)
