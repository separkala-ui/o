# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hong Kong - Payroll with Accounting',
    'version': '1.0',
    'countries': ['hk'],
    'category': 'Human Resources/Payroll',
    'description': """
Accounting Data for Hong Kong Payroll Rules
===========================================
    """,
    'depends': ['hr_payroll_account', 'l10n_hk', 'l10n_hk_hr_payroll'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/hr_salary_rule_data.xml',
    ],
    'demo': [
        'data/l10n_hk_hr_payroll_account_demo.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
    'auto_install': True,
}
