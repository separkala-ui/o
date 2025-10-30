# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp Messaging',
    'category': 'Productivity/WhatsApp',
    'summary': 'Text your Contacts on WhatsApp',
    'version': '1.0',
    'description': """This module integrates Odoo with WhatsApp to use WhatsApp messaging service""",
    'depends': ['mail', 'phone_validation'],
    'data': [
        'data/ir_actions_server_data.xml',
        'data/ir_cron_data.xml',
        'data/res_groups_privilege_data.xml',
        'data/whatsapp_template_data.xml',
        'data/whatsapp_templates_preview.xml',
        'security/res_groups.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'wizard/whatsapp_preview_views.xml',
        'wizard/whatsapp_composer_views.xml',
        'views/discuss_channel_views.xml',
        'views/ir_actions_server_views.xml',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_template_button_views.xml',
        'views/whatsapp_template_variable_views.xml',
        'views/res_config_settings_views.xml',
        'views/whatsapp_menus.xml',
        'views/res_partner_views.xml',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
        'apt': {
            'phonenumbers': 'python3-phonenumbers',
        },
    },
    'assets': {
        "im_livechat.assets_embed_core": [
            "whatsapp/static/src/core/common/**/*",
            "whatsapp/static/src/**/common/**/*",
        ],
        "mail.assets_public": [
            "whatsapp/static/src/core/common/**/*",
            "whatsapp/static/src/core/public_web/**/*",
            "whatsapp/static/src/**/common/**/*",
        ],
        'web.assets_backend': [
            'whatsapp/static/src/scss/*.scss',
            'whatsapp/static/src/core/common/**/*',
            'whatsapp/static/src/core/web/**/*',
            'whatsapp/static/src/core/public_web/**/*',
            'whatsapp/static/src/**/common/**/*',
            'whatsapp/static/src/**/web/**/*',
            'whatsapp/static/src/components/**/*',
            'whatsapp/static/src/views/**/*',
            # Don't include dark mode files in light mode
            ('remove', 'whatsapp/static/src/**/*.dark.scss'),
        ],
        "web.assets_web_dark": [
            'whatsapp/static/src/**/*.dark.scss',
        ],
        'web.assets_unit_tests': [
            'whatsapp/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
    'application': True,
    'installable': True,
}
