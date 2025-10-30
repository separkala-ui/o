import odoo.tests
from odoo.addons.iot.tests.common import IotCommonTest
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderIoTKiosk(IotCommonTest, SelfOrderCommonTest):
    def test_self_order_iot_kiosk(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'payment_method_ids': [(4, self.bank_payment_method.id)],
            'available_preset_ids': [(5, 0)],
            'is_posbox': True,
            'iface_print_via_proxy': True,
            'iface_printer_id': self.iot_receipt_printer.id,
        })
        self.pos_config.default_preset_id.service_at = 'counter'
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_order_kiosk_with_iot_printer")
        self.assertEqual(
            len(self.iot_websocket_messages),
            3,
            (
                "`iot.channel.send_message` should be called exactly three times: "
                "webrtc offer, websocket action, then operation confirmation."
                "This time, we received %s" % [next(iter(message.keys())) for message in self.iot_websocket_messages]
            ),
        )
        self.assertIn(
            'webrtc_offer', self.iot_websocket_messages[0], "First ws message should be of type 'webrtc_offer'."
        )
        self.assertIn(
            'iot_action', self.iot_websocket_messages[1], "Second ws message should be of type 'iot_action'."
        )
        self.assertIn(
            'operation_confirmation',
            self.iot_websocket_messages[2],
            "Second ws message should be of type 'operation_confirmation'."
        )
