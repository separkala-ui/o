# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, Command, _
from odoo.addons.resource.models.utils import filter_domain_leaf
from odoo.fields import Domain


class PlanningSend(models.TransientModel):
    _name = 'planning.send'
    _inherit = ['hr.mixin']
    _description = "Send Planning"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'slot_ids' in res and 'employee_ids' in fields:
            employees = self.env['planning.slot'].browse(res['slot_ids'][0][2]).employee_id
            res['employee_ids'] = [Command.set(employees.sudo().sorted('name').ids)]
        return res

    start_datetime = fields.Datetime("Period", required=True)
    end_datetime = fields.Datetime("Stop Date", required=True)
    include_unassigned = fields.Boolean("Include Open Shifts", default=True)
    note = fields.Text("Extra Message", help="Additional message displayed in the email sent to employees")
    employee_ids = fields.Many2many('hr.employee', string="Employees", compute_sudo=True,
                                    compute='_compute_slots_data', inverse='_inverse_employee_ids', store=True)
    slot_ids = fields.Many2many('planning.slot', compute='_compute_slots_data', store=True, export_string_translation=False)
    employees_no_email = fields.Many2many('hr.employee', string="Employees without email", compute_sudo=True,
                                    compute="_compute_employees_no_email", inverse="_inverse_employees_no_email", export_string_translation=False)

    def _get_slot_domain(self):
        self.ensure_one()

        # Our datetime conditions (these will override any from active_domain)
        datetime_domain = [
            ('start_datetime', '>=', self.start_datetime),
            ('end_datetime', '<=', self.end_datetime)
        ]

        active_domain = self.env.context.get('active_domain', [])

        if not active_domain:
            return datetime_domain

        # Remove conditions with 'start_datetime' or 'end_datetime' where the value is not False,
        cleaned_active_domain = filter_domain_leaf(active_domain, lambda field: field not in ['start_datetime', 'end_datetime'])

        # Combine domains: cleaned active_domain + our datetime
        return Domain.AND([cleaned_active_domain, datetime_domain])

    @api.depends('start_datetime', 'end_datetime')
    def _compute_slots_data(self):
        for wiz in self:
            wiz.slot_ids = self.env['planning.slot'].with_user(self.env.user).search(self._get_slot_domain(), order='employee_id')
            wiz.employee_ids = wiz.slot_ids.filtered(lambda s: s.resource_type == 'user').mapped('employee_id')

    def _inverse_employee_ids(self):
        for wiz in self:
            wiz.slot_ids = self.env['planning.slot'].with_user(self.env.user).search(self._get_slot_domain())

    @api.depends('employee_ids')
    def _compute_employees_no_email(self):
        for planning in self:
            planning.employees_no_email = planning.employee_ids.filtered(lambda employee: not employee.work_email)

    def _inverse_employees_no_email(self):
        for planning in self:
            planning.employee_ids = planning.employees_no_email + planning.employee_ids.filtered('work_email')

    def get_employees_without_work_email(self):
        self.ensure_one()
        if not self.employee_ids.has_access('write'):
            return None
        employee_ids_without_work_email = self.employee_ids.filtered(lambda employee: not employee.work_email).ids
        if not employee_ids_without_work_email:
            return None
        context = dict(self.env.context, force_email=True, form_view_ref='planning.hr_employee_view_form_simplified')
        return {
            'relation': 'hr.employee',
            'res_ids': employee_ids_without_work_email,
            'context': context,
        }

    def action_check_emails(self):
        if self.employees_no_email:
            return {
                'name': _('No Email Address for Some Employees'),
                'view_mode': 'form',
                'res_model': 'planning.send',
                'views': [(self.env.ref('planning.employee_no_email_list_wizard').id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': self.id,
                'target': 'new',
            }
        else:
            return self.action_send()

    def action_send(self):
        if not all(employee.work_email for employee in self.employee_ids):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("The work email is missing for the following employees:"),
                }
            }

        if self.include_unassigned:
            slot_to_send = self.slot_ids.filtered(lambda s: not s.employee_id or s.employee_id in self.employee_ids)
        else:
            slot_to_send = self.slot_ids.filtered(lambda s: s.employee_id in self.employee_ids)
        if not slot_to_send:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("The shifts have already been published, or there are no shifts to publish."),
                }
            }

        planning = self.env['planning.planning']._get_preview_planning(self.start_datetime, self.end_datetime, self.include_unassigned)
        planning.is_planning_preview = False
        planning.include_unassigned = self.include_unassigned

        slot_employees = slot_to_send.mapped('employee_id')
        open_slots = slot_to_send.filtered(lambda s: not s.employee_id and not s.is_past)
        employees_to_send = self.env['hr.employee']
        for employee in self.employee_ids:
            if employee in slot_employees:
                employees_to_send |= employee
            else:
                for slot in open_slots:
                    if not employee.planning_role_ids or not slot.role_id or slot.role_id in employee.planning_role_ids:
                        employees_to_send |= employee
        res = planning._send_planning(slots=slot_to_send, message=self.note, employees=employees_to_send)
        if res:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("Schedule sent to your employees"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
