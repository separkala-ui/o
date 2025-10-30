# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase, HttpCase


@tagged("-at_install", "post_install")
class TestHrAppraisalGoal(HttpCase):
    """Tests covering Appraisal Goals"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env["hr.employee"].create(
            {
                "name": "Trixie Lulamoon",
            },
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Pinkie Pie",
                "parent_id": cls.manager.id,
            }
        )
        cls.appraisal = cls.env["hr.appraisal"].create(
            {
                "employee_id": cls.employee.id,
                "manager_ids": cls.manager.ids,
            }
        )

    def test_appraisal_goal_autocompletion(self):
        """
        See if the employee and manager fields are auto-completed correctly on
        creation with smart buttons
        """
        self.start_tour(
            f"/odoo/appraisals/{self.appraisal.id}",
            "appraisals_create_appraisal_goal_from_smart_button",
            login="admin",
        )
        self.start_tour(
            f"/odoo/employees/{self.employee.id}",
            "employees_create_appraisal_goal_from_smart_button",
            login="admin",
        )
        autocompleted_goals = self.env["hr.appraisal.goal"].search(
            [
                ("employee_ids", "=", self.employee.id),
                ("manager_ids", "=", self.manager.id),
            ]
        )
        self.assertEqual(len(autocompleted_goals), 2,
            "Two appraisal goals with automatically filled employee and \
            manager inputs should have been created",
        )


class TestHrAppraisal(TransactionCase):
    """ Test used to check that when doing appraisal creation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_without_hr_right = cls.env['res.users'].create({
            'name': 'Test without hr right',
            'login': 'test_without_hr_right',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
            'notification_type': 'email',
        })
        cls.user_without_hr_right.action_create_employee()
        cls.employee_without_hr_right = cls.user_without_hr_right.employee_ids[0]
        cls.employee_subordinate = cls.env['hr.employee'].create({
            'name': 'Gerard',
            'parent_id': cls.employee_without_hr_right.id,
        })

    def test_create_goal_without_hr_right(self):
        goal_form = Form(self.env['hr.appraisal.goal'].with_user(self.user_without_hr_right).with_context(
            {'uid': self.user_without_hr_right.id}
        ))
        goal_form.name = "My goal"
        goal_form.employee_ids = self.employee_subordinate
        goal_form.save()
