{
    'name': 'Irish Intrastat Declaration',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Generates Intrastat XML report for declaration based on invoices for Ireland.
    """,
    'depends': ['l10n_ie', 'account_intrastat'],
    'data': [
        'data/account_return_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
