{
    'name': 'Uruguay - Accounting Reports',
    'version': '1.0',
    'description': """
Accounting reports for Uruguay
============================================
- Corporate tax report
    """,
    'depends': [
        'account_reports',
        'l10n_uy',
    ],
    'data': [
        'data/account_return_data.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
