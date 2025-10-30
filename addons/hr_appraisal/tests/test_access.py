# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.addons.mail.tests.common import mail_new_test_user


class TestAppraisalPublicAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({'name': 'mami rock'})
        cls.manager_user = mail_new_test_user(
            cls.env,
            name='manager_user',
            login='manager_user',
            email='manager_user@example.com',
            notification_type='email',
            groups='hr.group_hr_user',
            company_id=cls.company.id,
        )

        cls.manager = cls.env['hr.employee'].create({
            'name': 'Johnny',
            'user_id': cls.manager_user.id,
            'company_id': cls.company.id,
        })

        cls.employee_a, cls.employee_b = cls.env['hr.employee'].create([{
            'name': 'David',
            'parent_id': cls.manager.id,
            'company_id': cls.company.id,
            'wage': 1,
            'contract_date_start': '2017-12-05',
            'next_appraisal_date': '2057-12-05',
        }, {
            'name': 'Laura',
            'company_id': cls.company.id,
            'wage': 1,
            'contract_date_start': '2018-12-05',
            'next_appraisal_date': '2058-12-05',
        }])
        cls.employee_c = cls.env['hr.employee'].create({
            'name': 'Jade',
            'parent_id': cls.employee_a.id,
            'company_id': cls.company.id,
            'wage': 1,
            'contract_date_start': '2019-12-05',
            'next_appraisal_date': '2059-12-05',
        })

    def test_manager(self):
        with self.with_user(self.manager_user.login):
            david, laura, jade = self.env['hr.employee.public'].browse((self.employee_a | self.employee_b | self.employee_c).ids)

            self.assertTrue(david.is_manager)
            self.assertFalse(laura.is_manager)
            self.assertTrue(jade.is_manager)

    def test_manager_access_read(self):
        with self.with_user(self.manager_user.login):
            david, laura, jade = self.env['hr.employee.public'].browse((self.employee_a | self.employee_b | self.employee_c).ids)

            # Should be able to read direct reports and indirect reports birthday_public_display_string
            self.assertEqual(str(david.next_appraisal_date), '2057-12-05')
            self.assertEqual(str(jade.next_appraisal_date), '2059-12-05')
            # Cannot read values of "manager only field" on an employee the user is not manager of
            self.assertFalse(laura.next_appraisal_date)

    def test_manager_access_search(self):
        with self.with_user(self.manager_user.login):
            employees = self.env['hr.employee.public'].search([('next_appraisal_date', '>=', '2057-12-05')])

            # Should not find Laura as the user is not her manager
            self.assertEqual(len(employees), 2)
            self.assertTrue('Laura' not in employees.mapped('name'))
