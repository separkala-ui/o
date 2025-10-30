import logging
from odoo import models
from odoo.fields import Domain

_logger = logging.getLogger(__name__)


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report'

    def render_document(self, device_id_list, res_ids, data=None):
        """Send the dictionary in message to the iot_box via websocket,
        or return the data to be sent by longpolling.
        """
        # only override the method for delivery_iot reports
        if self.report_name not in ['delivery_iot.report_shipping_labels', 'delivery_iot.report_shipping_docs']:
            return super().render_document(device_id_list, res_ids, data)

        domain = [('res_model', '=', 'stock.picking'), ('res_id', 'in', res_ids)]
        if self.report_name == 'delivery_iot.report_shipping_labels':
            domain = Domain.AND([domain, [('name', 'ilike', 'Label%')]])
        elif self.report_name == 'delivery_iot.report_shipping_docs':
            domain = Domain.AND([domain, [('name', 'ilike', 'ShippingDoc%')]])

        attachments = self.env['ir.attachment'].search(domain, order='id desc')
        if not attachments:
            _logger.warning("No attachment found for report %s and res_ids %s", self.report_name, res_ids)
            return []

        device_ids = self.env['iot.device'].sudo().browse(device_id_list)
        return [
            {
                "iotBoxId": device.iot_id.id,
                "deviceId": device.id,
                "deviceIdentifier": device.identifier,
                "deviceName": device.display_name,
                "document": attachment.datas,
            }
            for attachment in attachments
            for device in device_ids
        ]  # As it is called via JS, we format keys to camelCase
