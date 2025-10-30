{
    'name': 'PoS IoT Ingenico',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Integrate your POS with an Ingenico payment terminal through IoT',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['pos_iot'],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_iot_ingenico/static/src/**/*',
        ],
    }
}
