import json

from odoo import models


class LithuanianIntrastatIntrastatGoodsSubmissionWizard(models.TransientModel):
    _name = 'l10n_lt_intrastat.intrastat.goods.submission.wizard'
    _inherit = 'account.return.submission.wizard'
    _description = "Intrastat Goods Submission Wizard"

    def action_proceed_with_submission(self):
        self.return_id._mark_completed()
        super().action_proceed_with_submission()

    def print_xml(self):
        options = self.return_id._get_closing_report_options()
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'lt_intrastat_export_to_xml',
                'no_closing_after_download': True,
            }
        }
