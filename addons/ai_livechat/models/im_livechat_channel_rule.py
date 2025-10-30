# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons.mail.tools.discuss import Store


class Im_LivechatChannelRule(models.Model):
    _inherit = 'im_livechat.channel.rule'

    chatbot_script_id = fields.Many2one('chatbot.script', string='Scripted Bot')
    ai_agent_id = fields.Many2one(
        'ai.agent',
        string='AI Agent',
        domain="[('is_system_agent', '=', False)]",
        index="btree_not_null"
    )

    def _is_bot_configured(self):
        return super()._is_bot_configured() or bool(self.ai_agent_id)

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [Store.One("ai_agent_id")]
