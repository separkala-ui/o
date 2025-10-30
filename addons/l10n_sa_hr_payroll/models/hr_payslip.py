# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_sa_wps_file_reference = fields.Char(string="WPS File Reference", copy=False)

    @api.depends('employee_id', 'version_id', 'struct_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        res = super()._compute_input_line_ids()
        balance_by_employee = self._get_salary_advance_balances()
        sal_adv_type = self.env.ref('l10n_sa_hr_payroll.l10n_sa_input_salary_advance')
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to or slip.country_code != 'SA':
                continue
            if slip.struct_id.code == 'SALARYADVANDLOAN':
                lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id == sal_adv_type)
                to_remove_vals = [(3, line.id, False) for line in lines_to_remove]
                to_add_vals = [(0, 0, {
                    'name': self.env._('Salary Advance'),
                    'amount': 0,
                    'input_type_id': sal_adv_type.id,
                })]
                slip.write({'input_line_ids': to_remove_vals + to_add_vals})
            else:
                balance = balance_by_employee[slip.employee_id]
                if balance <= 0:
                    continue
                lines_to_remove = slip.input_line_ids.filtered(
                    lambda x: x.input_type_id == sal_adv_type
                )
                to_remove_vals = [(3, line.id, False) for line in lines_to_remove]
                to_add_vals = [(0, 0, {
                    'name': self.env._('Salary Advance'),
                    'amount': balance,
                    'input_type_id': sal_adv_type.id,
                })]
                slip.write({'input_line_ids': to_remove_vals + to_add_vals})
        return res

    def _get_salary_advance_balances(self):
        balance_by_employee = super()._get_salary_advance_balances()
        payslips_by_employee = self._read_group(
            domain=[
                ('struct_id.country_id', '=', 'SA'),
                ('state', 'in', ('validated', 'paid')),
                ('employee_id', 'in', self.employee_id.ids),
                ('input_line_ids.code', '=', 'ADV'),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset']
        )
        for employee_id, payslips in payslips_by_employee:
            for input_line in payslips.input_line_ids:
                if input_line.code != 'ADV':
                    continue
                if input_line.payslip_id.struct_id.code == 'SALARYADVANDLOAN':
                    balance_by_employee[employee_id] += input_line.amount
                else:
                    balance_by_employee[employee_id] -= input_line.amount
        return balance_by_employee

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_sa_hr_payroll', [
                'data/hr_salary_rule_saudi_data.xml',
                'data/hr_payslip_input_type_data.xml',
                'data/hr_rule_parameter_data.xml',
            ])]

    def _l10n_sa_wps_generate_file_reference(self):
        # if all were previously printed together, dont increment sequence
        if not all(self.mapped('l10n_sa_wps_file_reference')) or len(set(self.mapped('l10n_sa_wps_file_reference'))) != 1:
            # else make a new sequence
            self.l10n_sa_wps_file_reference = self.env['ir.sequence'].next_by_code("l10n_sa.wps")
        return self[:1].l10n_sa_wps_file_reference

    @api.model
    def _l10n_sa_format_float(self, val):
        currency = self.env.ref('base.SAR')
        return f'{currency.round(val):.{currency.decimal_places}f}'

    def _l10n_sa_get_wps_data(self):
        header = [
            "[32B-AMT]",
            "[59-ACC]",
            "[59-NAME]",
            "[57-BANK]",
            "[70-DET]",
            "[RET-CODE]",
            "[MOL-BAS]",
            "[MOL-HAL]",
            "[MOL-OEA]",
            "[MOL-DED]",
            "[MOL-ID]",
            "[TRN-REF]",
            "[TRN-STATUS]",
            "[TRN-DATE]"
        ]
        rows = []

        all_codes = ['BASIC', 'GROSS', 'NET', 'HOUALLOW']
        all_line_values = self._get_line_values(all_codes)

        for payslip in self:
            employee_id = payslip.employee_id

            net = all_line_values['NET'][payslip.id]['total']
            basic = all_line_values['BASIC'][payslip.id]['total']
            gross = all_line_values['GROSS'][payslip.id]['total']
            housing = all_line_values['HOUALLOW'][payslip.id]['total']

            extra_income = gross - basic - housing
            deductions = gross - net

            rows.append([
                self._l10n_sa_format_float(net),
                employee_id.primary_bank_account_id.acc_number or "",
                employee_id.name or "",
                (employee_id.primary_bank_account_id.bank_id.l10n_sa_sarie_code or "") if employee_id.primary_bank_account_id.bank_id != payslip.company_id.l10n_sa_bank_account_id.bank_id else "",
                employee_id.version_id.l10n_sa_wps_description or "",
                '',  # [RET-CODE]: Required blank cell
                self._l10n_sa_format_float(basic),
                self._l10n_sa_format_float(housing),
                self._l10n_sa_format_float(extra_income),
                self._l10n_sa_format_float(deductions),
                employee_id.l10n_sa_employee_code or "",
                '',  # [TRN-REF]: Required blank cell
                '',  # [TRN-STATUS]: Required blank cell
                '',  # [TRN-DATE]: Required blank cell
            ])
        return [header, *rows]

    def action_payslip_payment_report(self, export_format='l10n_sa_wps'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.payment.report.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_payslip_ids': self.ids,
                'default_payslip_run_id': self.payslip_run_id.id,
                'default_export_format': export_format,
            },
        }
