# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Hr_TimesheetMergeWizard(models.TransientModel):
    _name = 'hr_timesheet.merge.wizard'
    _description = 'Merge Timesheets'

    name = fields.Char('Description', compute='_compute_name', readonly=False, store=True)
    timesheet_ids = fields.Many2many('account.analytic.line', string='Timesheets', domain="[('project_id', '!=', False), ('validated', '=', False)]", export_string_translation=False)

    date = fields.Date('Date')
    unit_amount = fields.Float('Quantity', compute='_compute_unit_amount', readonly=False, store=True)
    encoding_uom_id = fields.Many2one('uom.uom', readonly=True, export_string_translation=False)

    project_id = fields.Many2one('project.project', string='Project', domain=[('is_template', '=', False)])
    task_id = fields.Many2one('project.task', string='Task', domain="[('project_id.allow_timesheets', '=', True), ('project_id', '=?', project_id)]", compute='_compute_task_id', readonly=False, store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')

    @api.constrains('timesheet_ids')
    def _check_timesheet_ids(self):
        for wizard in self:
            if len(set(wizard.timesheet_ids.mapped('encoding_uom_id'))) > 1:
                raise ValidationError(_('The timesheets must have the same encoding unit'))

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_ids = self.env.context.get('active_ids')

        if 'timesheet_ids' in fields and active_ids:
            timesheets = self.env['account.analytic.line'].browse(active_ids)
            timesheets = timesheets.filtered(lambda l: l.project_id and not l.validated and not l.is_timer_running)
            if timesheets:
                res['timesheet_ids'] = timesheets.ids

                if 'date' in fields:
                    res['date'] = timesheets[0].date

                for f in ['encoding_uom_id', 'project_id', 'task_id', 'employee_id']:
                    if f in fields:
                        res[f] = timesheets[0][f].id

        return res

    @api.depends('project_id')
    def _compute_task_id(self):
        for entry in self:
            if entry.project_id != entry.task_id.project_id:
                entry.task_id = False

    @api.depends('timesheet_ids')
    def _compute_name(self):
        for entry in self:
            all_names = set(entry.timesheet_ids.mapped('name'))
            entry.name = ' / '.join([name for name in sorted(all_names) if name and name != '/'])

    @api.depends('timesheet_ids')
    def _compute_unit_amount(self):
        for entry in self:
            entry.unit_amount = sum(entry.timesheet_ids.mapped('unit_amount'))

    def action_merge(self):
        self.ensure_one()

        self.env['account.analytic.line'].create(self._prepare_merged_timesheet_values())
        self.timesheet_ids.unlink()

        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("The timesheets have successfully been merged."),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def _prepare_merged_timesheet_values(self):
        return {
            'name': self.name,
            'date': self.date,
            'unit_amount': self.unit_amount,
            'encoding_uom_id': self.encoding_uom_id.id,
            'project_id': self.project_id.id,
            'task_id': self.task_id.id,
            'employee_id': self.employee_id.id,
        }
