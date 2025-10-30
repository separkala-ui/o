# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('ae')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.ae'),
            structure=cls.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure'),
            structure_type=cls.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure_type'),
            contract_fields={
                'wage': 40000.0,
                'l10n_ae_housing_allowance': 400.0,
                'l10n_ae_transportation_allowance': 220.0,
                'l10n_ae_other_allowances': 100.0,
                'l10n_ae_is_dews_applied': True,
            }
        )

        cls.work_entry_types = {
            entry_type.code: entry_type
            for entry_type in cls.env['hr.work.entry.type'].search([])
        }

    def _get_input_line_amount(self, payslip, code):
        input_lines = payslip.input_line_ids.filtered(lambda line: line.code == code)
        amounts = input_lines.mapped('amount')
        return len(amounts), sum(amounts)

    @classmethod
    def _create_worked_days(cls, name=False, code=False, number_of_days=0, number_of_hours=0):
        return Command.create({
            'name': name,
            'work_entry_type_id': cls.work_entry_types[code].id,
            'code': code,
            'number_of_days': number_of_days,
            'number_of_hours': number_of_hours,
        })

    def _test_eos_calculation(self, start_date, departure_date, payslip_start, payslip_end,
                            expected_eos, has_unpaid_leave=False, wage=15000.0):
        """Helper method to test end of service salary rule calculations."""
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'structure_type_id': self.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure_type').id,
            'country_id': self.env.ref('base.ae').id,
            'wage': wage,
            'date_version': start_date,
            'contract_date_start': start_date,
        })

        if has_unpaid_leave:
            unpaid_leave = self.env['hr.leave'].create({
                'name': 'Unpaid Leave',
                'employee_id': employee.id,
                'holiday_status_id': self.env.ref('hr_holidays.leave_type_unpaid').id,
                'request_date_from': date(2025, 8, 4),
                'request_date_to': date(2025, 8, 8),
            })
            unpaid_leave.action_approve()
            employee.version_id.generate_work_entries(payslip_start, payslip_end)

        departure_notice = self.env['hr.departure.wizard'].create({
            'employee_ids': [Command.link(employee.id)],
            'departure_date': departure_date,
            'departure_description': 'foo',
        })
        departure_notice.with_context(employee_termination=True).action_register_departure()

        payslip = self._generate_payslip(payslip_start, payslip_end, employee_id=employee.id, version_id=employee.version_id.id)
        payslip.compute_sheet()

        self.assertEqual(
            payslip._get_line_values(['EOS'])['EOS'][payslip.id]['total'],
            expected_eos,
            "End of Service calculation is incorrect"
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 40000.0, 'HOUALLOW': 400.0, 'TRAALLOW': 220.0, 'OTALLOW': 100.0, 'EOSP': 3333.33, 'ALP': 3393.33, 'GROSS': 40720.0, 'SICC': 5090.0, 'SIEC': -2036.0, 'DEWS': -3332.0, 'NET': 35352.0}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_2(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        other_inputs_to_add = [
            (self.env.ref('l10n_ae_hr_payroll.input_salary_arrears'), 1000),
            (self.env.ref('l10n_ae_hr_payroll.input_other_earnings'), 2000),
            (self.env.ref('l10n_ae_hr_payroll.input_salary_deduction'), 500),
            (self.env.ref('l10n_ae_hr_payroll.input_other_deduction'), 200),
            (self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_overtime_allowance'), 300),
            (self.env.ref('l10n_ae_hr_payroll.input_bonus_earnings'), 400),
            (self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_other_allowance'), 600),
            (self.env.ref('l10n_ae_hr_payroll.input_airfare_allowance_earnings'), 700),
        ]
        for other_input, amount in other_inputs_to_add:
            self._add_other_input(payslip, other_input, amount)
        payslip.compute_sheet()

        payslip_results = {'BASIC': 40000.0, 'HOUALLOW': 400.0, 'TRAALLOW': 220.0, 'OTALLOW': 100.0, 'SALARY_ARREARS': 1000.0, 'OTHER_EARNINGS': 2000.0, 'SALARY_DEDUCTIONS': -500.0, 'OTHER_DEDUCTIONS': -200.0, 'OVERTIMEALLOWINP': 300.0, 'BONUS': 400.0, 'OTALLOWINP': 600.0, 'AIRFARE_ALLOWANCE': 700.0, 'EOSP': 3333.33, 'ALP': 3393.33, 'GROSS': 45720.0, 'SICC': 5090.0, 'SIEC': -2036.0, 'DEWS': -3332.0, 'NET': 39652.0}
        self._validate_payslip(payslip, payslip_results)

    def test_instant_pay_payslip_generation(self):
        instant_pay_structure = self.env.ref('l10n_ae_hr_payroll.l10n_ae_uae_instant_pay')
        payslip = self._generate_payslip(date(2023, 3, 1), date(2023, 3, 31), struct_id=instant_pay_structure.id)
        other_inputs_to_add = [
            (self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_allowance'), 1000),
            (self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_commission'), 800),
            (self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_salary_advance'), 1500),
            (self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_loan_advance'), 1200),
            (self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_deduction'), 700),
        ]
        for other_input, amount in other_inputs_to_add:
            self._add_other_input(payslip, other_input, amount)
        payslip.compute_sheet()

        payslip_results = {'ALLOW': 1000.00, 'COMM': 800.00, 'ADV': 1500.00, 'LOAN': 1200.00, 'DED': -700.00, 'NET': 3800.00}
        self._validate_payslip(payslip, payslip_results)

    def test_salary_advance(self):
        instant_pay_structure = self.env.ref('l10n_ae_hr_payroll.l10n_ae_uae_instant_pay')
        uae_employee_structure = self.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure')
        salary_advance_other_input = self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_salary_advance')

        # First salary advance payslip of 500 on 01/09/2024 and setting the advance amount to 500 and validate the payslip
        test_saladv_payslip1 = self._generate_payslip(
            date(2024, 9, 1), date(2024, 9, 30), struct_id=instant_pay_structure.id
        )
        self._add_other_input(test_saladv_payslip1, salary_advance_other_input, 500)

        test_saladv_payslip1.compute_sheet()
        test_saladv_payslip1.action_payslip_done()

        # Second salary advance payslip of 200 on 15/09/2024
        test_saladv_payslip2 = self._generate_payslip(
            date(2024, 9, 15), date(2024, 9, 30), struct_id=instant_pay_structure.id
        )
        self._add_other_input(test_saladv_payslip2, salary_advance_other_input, 200)

        test_saladv_payslip2.compute_sheet()
        test_saladv_payslip2.action_payslip_done()

        # September monthly payslip
        test_payslip_sept = self._generate_payslip(
            date(2024, 9, 1), date(2024, 9, 30), struct_id=uae_employee_structure.id
        )
        test_payslip_sept._compute_input_line_ids()
        # September monthly pay should have salary advance recovery = 700 by default
        nbr_rec, amount_rec = self._get_input_line_amount(test_payslip_sept, "ADVREC")
        self.assertEqual(nbr_rec, 1)
        self.assertEqual(amount_rec, 700)
        # Changing the recovery amount to 500 and validate the payslip
        test_payslip_sept.input_line_ids.filtered(lambda line: line.code == "ADVREC").write({
            "amount": 500
        })
        test_payslip_sept.compute_sheet()
        test_payslip_sept.action_payslip_done()

        nbr_rec, amount_rec = self._get_input_line_amount(test_payslip_sept, "ADVREC")
        self.assertEqual(nbr_rec, 1)
        self.assertEqual(amount_rec, 500)

        # Third salary advance payslip of 300 on 1/10/2024
        test_saladv_payslip3 = self._generate_payslip(
            date(2024, 10, 1), date(2024, 10, 31), struct_id=instant_pay_structure.id
        )
        self._add_other_input(test_saladv_payslip3, salary_advance_other_input, 300)
        test_saladv_payslip3.compute_sheet()
        test_saladv_payslip3.action_payslip_done()

        # October monthly pay should have salary advance recovery = 500 (200+300) by default
        test_payslip_oct = self._generate_payslip(
            date(2024, 10, 1), date(2024, 10, 31), struct_id=uae_employee_structure.id
        )
        test_payslip_oct._compute_input_line_ids()
        test_payslip_oct.compute_sheet()
        test_payslip_oct.action_payslip_done()

        nbr_rec, amount_rec = self._get_input_line_amount(test_payslip_oct, "ADVREC")
        self.assertEqual(nbr_rec, 1)
        self.assertEqual(amount_rec, 500)

        # November monthly pay should have salary advance recovery = 0
        test_payslip_nov = self._generate_payslip(
            date(2024, 11, 1), date(2024, 11, 30), struct_id=uae_employee_structure.id
        )
        test_payslip_nov._compute_input_line_ids()
        test_payslip_nov.compute_sheet()
        test_payslip_nov.action_payslip_done()
        nbr_rec, amount_rec = self._get_input_line_amount(test_payslip_nov, "ADVREC")
        self.assertEqual(nbr_rec, 0)
        self.assertEqual(amount_rec, 0)

    def test_end_of_service_salary_rule_1(self):
        """Case: Employee worked 2 years, 8 months, and 15 days
        Expected: Calculate EOS for 2 years, 8 months and 15 days
        (2 years * 12 month / year) + 8 months = 32 months
        because the total is less than 6 years, ratio = 21 / 30
        (15_000 $/year) * ratio * (1/12 year/month) = 875 $/month
        (15_000 $/year) * ratio * (1/365 year/day) ~ 28.77 $/day

        total = 32 months * 875 $/month = 28_000 $
                15 days * 28.77 $/day ~ 432 $       +
              = 28_432 $
        """
        self._test_eos_calculation(
            start_date=date(2014, 6, 4),
            departure_date=date(2017, 2, 19),
            payslip_start=date(2017, 2, 1),
            payslip_end=date(2017, 2, 28),
            expected_eos=28_432.0
        )

    def test_end_of_service_salary_rule_2(self):
        """Case: Employee worked 5 years, 5 months, and 17 days
        Expected: Calculate EOS for 5 years, 5 months and 17 days
        (5 years * 12 month / year) + 5 months = 65 months
        because the total is less than 6 years, ratio = 21 / 30
        (15_000 $/year) * ratio * (1/12 year/month) = 875 $/month
        (15_000 $/year) * ratio * (1/365 year/day) ~ 28.77 $/day

        total = 65 months * 875 $/month = 56_875 $
                17 days * 28.77 $/day ~ 490 $       +
              = 57_365 $
        """
        self._test_eos_calculation(
            start_date=date(2019, 7, 22),
            departure_date=date(2025, 1, 8),
            payslip_start=date(2025, 1, 1),
            payslip_end=date(2025, 1, 31),
            expected_eos=57_365.0
        )

    def test_end_of_service_salary_rule_3(self):
        """Case: Employee worked 6 years, 5 months, and 17 days
        Expected: Calculate EOS for 6 years, 5 months and 17 days
        (6 years * 12 month / year) + 5 months = 77 months
        because the total is greater than 6 years, ratio = 1
        (15_000 $/year) * ratio * (1/12 year/month) = 1250 $/month
        (15_000 $/year) * ratio * (1/365 year/day) ~ 41.1 $/day

        total = 60 months * 1250 * (21/30) $/month = 52_500 $
                17 months * 1250 $/month = 21_250 $
                17 days * 41.1 $/day ~ 699 $       +
              = 74_449 $
        """
        self._test_eos_calculation(
            start_date=date(2018, 7, 22),
            departure_date=date(2025, 1, 8),
            payslip_start=date(2025, 1, 1),
            payslip_end=date(2025, 1, 31),
            expected_eos=74_449.0
        )

    def test_end_of_service_salary_rule_4(self):
        """Case: Employee worked 2 years, 8 months, and 15 days with 5 unpaid days
        Expected: Calculate EOS for 2 years, 8 months and 10 days
        (2 years * 12 month / year) + 8 months = 32 months
        because the total is less than 6 years, ratio = 21 / 30
        (15_000 $/year) * ratio * (1/12 year/month) = 875 $/month
        (15_000 $/year) * ratio * (1/365 year/day) ~ 28.77 $/day

        total = 32 months * 875 $/month = 28000 $
                10 days * 28.77 $/day ~ 288 $       +
              = 28_288 $
        """
        self._test_eos_calculation(
            start_date=date(2022, 12, 16),
            departure_date=date(2025, 8, 31),
            payslip_start=date(2025, 8, 1),
            payslip_end=date(2025, 8, 31),
            expected_eos=28_288.0,
            has_unpaid_leave=True
        )

    def test_end_of_service_salary_rule_5(self):
        """Case: Employee worked 6 years and 3 days with 5 unpaid days
        Expected: Calculate EOS for 5 years, 11 months and 29 days
        (5 years * 12 month / year) + 11 months = 71 months
        because the total is less than 6 years, ratio = 21 / 30
        (15_000 $/year) * ratio * (1/12 year/month) = 875 $/month
        (15_000 $/year) * ratio * (1/365 year/day) ~ 28.77 $/day

        total = 71 months * 875 $/month = 62_125 $
                29 days * 28.77 $/day ~ 835 $       +
              = 62_960 $
        """
        self._test_eos_calculation(
            start_date=date(2019, 8, 28),
            departure_date=date(2025, 8, 31),
            payslip_start=date(2025, 8, 1),
            payslip_end=date(2025, 8, 31),
            expected_eos=62_960.0,
            has_unpaid_leave=True
        )

    def test_end_of_service_salary_rule_6(self):
        """Case: Employee worked 7 years and 3 days with 5 unpaid days
        Expected: Calculate EOS for 6 years, 11 months and 29 days
        (6 years * 12 month / year) + 11 months = 83 months
        because the total is greater than 6 years, ratio = 1
        (15_000 $/year) * ratio * (1/12 year/month) = 1250 $/month
        (15_000 $/year) * ratio * (1/365 year/day) ~ 41.1 $/day

        total = 60 months * 1250 * (21/30) $/month = 52_500 $
                23 months * 1250 $/month = 28_750 $
                29 days * 41.1 $/day ~ 1192 $       +
              = 82_442 $
        """
        self._test_eos_calculation(
            start_date=date(2018, 8, 28),
            departure_date=date(2025, 8, 31),
            payslip_start=date(2025, 8, 1),
            payslip_end=date(2025, 8, 31),
            expected_eos=82_442.0,
            has_unpaid_leave=True
        )

    def test_payslip_attendance_1(self):
        if self.env['ir.module.module']._get('hr_payroll_attendance').state != 'installed':
            self.skipTest("Skipping test because hr_payroll_attendance is not installed.")

        self.employee.country_id = False
        self.contract.write({
            'contract_date_start': '2025-01-01',
            'work_entry_source': 'attendance',
            'wage': 5000,
            'wage_type': 'monthly',
            'l10n_ae_housing_allowance': 2000,
            'l10n_ae_transportation_allowance': 1000,
            'l10n_ae_other_allowances': 100,
            'l10n_ae_is_dews_applied': False,
        })

        worked_days_vals = [
            {'name': 'Unpaid', 'code': 'LEAVE90', 'number_of_hours': 16, 'number_of_days': 2},
            {'name': 'Paid Time Off', 'code': 'LEAVE120', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Sick Leave 50', 'code': 'AESICKLEAVE50', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Out of Contract', 'code': 'OUT', 'number_of_hours': 32, 'number_of_days': 4},
            {'name': 'Attendance', 'code': 'WORK100', 'number_of_hours': 88, 'number_of_days': 11},
        ]

        payslip = self._generate_payslip('2025-07-01', '2025-07-31')
        payslip.write({
            "worked_days_line_ids": [self._create_worked_days(**vals) for vals in worked_days_vals],
        })
        payslip.compute_sheet()
        payslip_results = {
            'BASIC': 2391.30,
            'HOUALLOW': 956.52,
            'TRAALLOW': 478.26,
            'OTALLOW': 47.83,
            'EOSP': 188.73,
            'ALP': 436.76,
            'AEPAID': 1056.48,
            'AESPAID50': 528.24,
            'GROSS': 5458.63,
            'NET': 5458.63,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_attendance_2(self):
        if self.env['ir.module.module']._get('hr_payroll_attendance').state != 'installed':
            self.skipTest("Skipping test because hr_payroll_attendance is not installed.")

        self.employee.country_id = False
        self.contract.write({
            'contract_date_start': '2025-01-01',
            'work_entry_source': 'attendance',
            'wage': 5000,
            'hourly_wage': 44.02,
            'wage_type': 'hourly',
            'l10n_ae_housing_allowance': 2000,
            'l10n_ae_transportation_allowance': 1000,
            'l10n_ae_other_allowances': 100,
            'l10n_ae_is_dews_applied': False,
        })

        worked_days_vals = [
            {'name': 'Unpaid', 'code': 'LEAVE90', 'number_of_hours': 16, 'number_of_days': 2},
            {'name': 'Paid Time Off', 'code': 'LEAVE120', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Sick Leave 50', 'code': 'AESICKLEAVE50', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Out of Contract', 'code': 'OUT', 'number_of_hours': 32, 'number_of_days': 4},
            {'name': 'Attendance', 'code': 'WORK100', 'number_of_hours': 88, 'number_of_days': 11},
        ]

        payslip = self._generate_payslip('2025-06-01', '2025-06-30')
        payslip.write({
            "worked_days_line_ids": [self._create_worked_days(**vals) for vals in worked_days_vals]
        })
        payslip.compute_sheet()
        payslip_results = {
            'BASIC': 2391.30,
            'EOSP': 188.73,
            'ALP': 436.76,
            'AEPAID': 1056.48,
            'AESPAID50': 528.24,
            'GROSS': 3976.02,
            'NET': 3976.02,
        }
        self._validate_payslip(payslip, payslip_results)
