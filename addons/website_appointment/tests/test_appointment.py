# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from datetime import datetime

from odoo import Command, http
from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.website_appointment.controllers.appointment import WebsiteAppointment
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.exceptions import ValidationError
from odoo.tests import users, tagged
from unittest.mock import patch


class WebsiteAppointmentTest(AppointmentCommon, MockVisitor):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.apt_type_bxls_2days.write({'is_published': True})

    def test_apt_type_create_from_website(self):
        """ Test that when creating an appointment type from the website, we use
        the visitor's timezone as fallback for the user's timezone """
        test_user = self.apt_manager
        test_user.write({'tz': False})

        visitor = self.env['website.visitor'].create({
            "name": 'Test Visitor',
            'access_token': test_user.partner_id.id,
            "timezone": False,
        })

        AppointmentType = self.env['appointment.type']
        with self.mock_visitor_from_request(force_visitor=visitor):
            # Test appointment timezone when user and visitor both don't have timezone
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment UTC Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment UTC Timezone')
                ]).appointment_tz, 'UTC'
            )

            # Test appointment timezone when user doesn't have timezone and visitor have timezone
            visitor.timezone = 'Europe/Brussels'
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment Visitor Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment Visitor Timezone')
                ]).appointment_tz, visitor.timezone
            )

            # Test appointment timezone when user has timezone
            test_user.tz = 'Asia/Kolkata'
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment User Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment User Timezone')
                ]).appointment_tz, test_user.tz
            )

    @users('apt_manager')
    def test_apt_type_create_from_website_slots(self):
        """ Test that when creating an appointment type from the website, defaults slots are set."""
        pre_slots = self.env['appointment.slot'].search([])
        # Necessary for appointment type as `create_and_get_website_url` does not return the record.
        pre_appts = self.env['appointment.type'].search([])

        self.env['appointment.type'].create_and_get_website_url(**{
            'name': 'Test Appointment Type has slots',
            'staff_user_ids': [self.staff_user_bxls.id]
        })

        new_appt = self.env['appointment.type'].search([]) - pre_appts
        new_slots = self.env['appointment.slot'].search([]) - pre_slots
        self.assertEqual(new_slots.appointment_type_id, new_appt)

        expected_slots = {
            (str(weekday), start_hour, end_hour) : 1
            for weekday in range(1, 6)
            for start_hour, end_hour in ((9., 12.), (14., 17.))
        }
        created_slots = Counter()
        for slot in new_slots:
            created_slots[(slot.weekday, slot.start_hour, slot.end_hour)] += 1
        self.assertDictEqual(created_slots, expected_slots)

    @users('admin')
    def test_apt_type_is_published(self):
        for category, default in [
                ('custom', False),
                ('punctual', False),
                ('recurring', False),
                ('anytime', False)
            ]:
            appointment_type = self.env['appointment.type'].create({
                'name': 'Custom Appointment',
                'category': category,
                'start_datetime': datetime(2023, 10, 3, 8, 0) if category == 'punctual' else False,
                'end_datetime': datetime(2023, 10, 10, 8, 0) if category == 'punctual' else False,
            })
            self.assertEqual(appointment_type.is_published, default)

            if category in ['custom', 'punctual', 'recurring']:
                appointment_copied = appointment_type.copy()
                self.assertFalse(appointment_copied.is_published, "When we copy an appointment type, the new one should not be published")

                appointment_type.write({'is_published': False})
                appointment_copied = appointment_type.copy()
                self.assertFalse(appointment_copied.is_published)
            else:
                with self.assertRaises(ValidationError):
                    # A maximum of 1 anytime appointment per employee is allowed
                    appointment_type.copy()

    @users('admin')
    def test_apt_type_is_published_update(self):
        appointment = self.env['appointment.type'].create({
            'name': 'Recurring Appointment',
            'category': 'recurring',
        })
        self.assertFalse(appointment.is_published, "A recurring appointment type should not be published at creation")

        appointment.write({'category': 'custom'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

        appointment.write({'category': 'recurring'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

        appointment.write({'category': 'anytime'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

        appointment.write({
            'category': 'punctual',
            'start_datetime': datetime(2022, 2, 14, 8, 0, 0),
            'end_datetime': datetime(2022, 2, 20, 20, 0, 0),
        })
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

    @users('admin')
    def test_apt_videocall_location_multi_company_and_multi_website(self):
        """Check video url matches the website of the appointment type."""
        company_1 = self.env.company
        company_2 = self.env['res.company'].create({
            'country_id': self.env.ref('base.ca').id,
            'currency_id': self.env.ref('base.CAD').id,
            'email': 'company_2@test.example.com',
            'name': 'Company 2',
        })

        website_1 = company_1.website_id
        website_1.domain = 'http://localhost:8069'
        # Ensure custom domains are taken into account for the videocall location
        website_2 = self.env['website'].create({
            'name': 'Website Company 2',
            'company_id': company_2.id,
            'domain': 'http://127.0.0.1:8069',
        })

        appointment_1, appointment_2 = self.env['appointment.type'].create([
            {
                'name': 'Apt Website 1',
                'staff_user_ids': self.staff_user_bxls,
                'event_videocall_source': 'discuss',
                'website_id': website_1.id,
            },
            {
                'name': 'Apt Website 2',
                'staff_user_ids': self.staff_user_bxls,
                'event_videocall_source': 'discuss',
                'website_id': website_2.id,
            },
        ])

        event_1, event_2 = self.env['calendar.event'].create([
            {
                'name': 'Event 1',
                'start': datetime(2023, 11, 23, 8, 0),
                'stop':  datetime(2023, 11, 23, 9, 0),
                'appointment_type_id': appointment_1.id,
            }, {
                'name': 'Event 2',
                'start': datetime(2023, 11, 23, 8, 0),
                'stop':  datetime(2023, 11, 23, 9, 0),
                'appointment_type_id': appointment_2.id,
            },
        ]).with_user(self.apt_user)

        # Should not need to be able to read the appointment type to read the base url
        (event_1 + event_2).invalidate_recordset()
        (appointment_1 + appointment_2).invalidate_recordset()
        self.assertEqual((event_1 + event_2).env.user, self.apt_user)
        self.assertTrue((event_1 + event_2).has_access('read'))
        self.assertFalse((appointment_1 + appointment_2).with_user(self.apt_user).has_access('read'))

        self.assertIn("localhost:8069/", event_1.videocall_location)
        self.assertIn("127.0.0.1:8069/", event_2.videocall_location)

        self.assertIn("localhost:8069/", event_1.videocall_redirection)
        self.assertIn("127.0.0.1:8069/", event_2.videocall_redirection)

    def test_find_customer_country_from_visitor(self):
        self.env.user.tz = "Europe/Brussels"
        belgium = self.env.ref('base.be')
        usa = self.env.ref('base.us')
        current_website = self.env['website'].get_current_website()
        appointments_belgium, appointment_usa = self.env['appointment.type'].create([
            {
                'name': 'Appointment for Belgium',
                'country_ids': [(6, 0, [belgium.id])],
                'website_id': current_website.id
            }, {
                'name': 'Appointment for the US',
                'country_ids': [(6, 0, [usa.id])],
                'website_id': current_website.id
            },
        ])

        visitor_from_the_us = self.env['website.visitor'].create({
            "name": 'Visitor from the US',
            'access_token': self.apt_manager.partner_id.id,
            "country_id": usa.id,
            'website_id': current_website.id
        })

        wa_controller = WebsiteAppointment()

        self.env.user.country_id = False

        class MockGeoIPWithCountryCode:
            country_code = None

        with MockRequest(self.env, website=current_website) as mock_request:
            with self.mock_visitor_from_request(force_visitor=visitor_from_the_us), \
                    patch.object(mock_request, 'geoip', new=MockGeoIPWithCountryCode()):
                # Make sure no country was identified before
                self.assertFalse(mock_request.env.user.country_id)
                self.assertFalse(mock_request.geoip.country_code)
                domain = [
                    '|', ('end_datetime', '=', False), ('end_datetime', '>=', datetime.utcnow())
                ]
                available_appointments = wa_controller._fetch_and_check_private_appointment_types(None, None, None, "", domain=wa_controller._appointments_base_domain(None, False, None, domain, True))

                self.assertNotIn(appointments_belgium, available_appointments,
                                 "US visitor should not have access to an Appointment Type restricted to Belgium.")
                self.assertIn(appointment_usa, available_appointments,
                              "US visitor should have access to an Appointment Type restricted to the US.")

    @tagged("security", "-at_install", "post_install")
    def test_visitor_appointment_booker(self):
        """Check that the calendar events created by a visitor have the same appointment_booker_id.

        This should not be the case when CSRF token is unchecked, such as when used in an iframe.
        """
        visitors = self.env['website.visitor'].create([
            {'access_token': '11111111111111111111111111111111'},
            {'access_token': '22222222222222222222222222222222'},
        ])
        phone_question = self.apt_type_bxls_2days._get_main_phone_question()
        self.assertTrue(phone_question)

        for with_csrf, visitor in zip([True, False], visitors):
            with self.subTest(with_csrf=with_csrf), self.mock_visitor_from_request(force_visitor=visitor):
                self.authenticate(None, None)
                event_values = {
                    'allday': 0,
                    'duration_str': '1.0',
                    'email': 'visitor@test.example.com',
                    'name': 'Visitor',
                    f'question_{phone_question.id}': '+1 555-555-5555',
                    'staff_user_id': self.staff_user_bxls.id,
                } | ({'csrf_token': http.Request.csrf_token(self)} if with_csrf else {})

                for datetime_str in ['2022-02-14 10:00:00', '2022-02-15 10:00:00']:
                    event_values['datetime_str'] = datetime_str
                    self.url_open(f'/appointment/{self.apt_type_bxls_2days.id}/submit', event_values)

                events = self.env['calendar.event'].search([], order='id DESC', limit=2)

                # Check that visitor has been linked to the new events.
                self.assertEqual(len(visitor.calendar_event_ids), 2)
                self.assertEqual(visitor.calendar_event_ids, events)

                # Check that the new events have the same appointment_booker_id.
                self.assertTrue(all(event.appointment_booker_id for event in events))
                self.assertEqual(len(events.appointment_booker_id), 1 if with_csrf else 2)
                events.unlink()

    def test_appointment_no_phone_question(self):
        self.apt_type_bxls_2days.question_ids = False
        values = {
            'datetime_str': '2022-02-14 10:00:00',
            'duration_str': '1.0',
            'email': 'no_phone_test_1@example.com',
            'name': 'No Phone Test',
            'staff_user_id': self.staff_user_bxls.id,
        }
        # New customer is created
        self.authenticate(None, None)
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", values)
        self.assertEqual(res.status_code, 200, "Response should = OK")
        new_partner = self.env['res.partner'].search([('email', '=', values['email'])])
        self.assertTrue(new_partner)
        self.assertFalse(new_partner.phone)

        # Logged partner is matched
        self.authenticate('apt_manager', 'apt_manager')
        values |= {
            'csrf_token': http.Request.csrf_token(self),
            'email': self.apt_manager.partner_id.email,
            'datetime_str': '2022-02-14 11:00:00',
        }
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", values)
        self.assertEqual(res.status_code, 200, "Response should = OK")
        self.assertListEqual(
            self.apt_type_bxls_2days.meeting_ids[0].partner_ids.ids,
            [self.apt_manager.partner_id.id, self.staff_user_bxls.partner_id.id])

    def test_appointment_phone_questions(self):
        """ Ensure that only the first question propagates the phone to the created partner
        when creating a new partner, or to the logged user when they use their data and have
        no phone. """
        phone_question_1, noise_question, phone_question_2 = self.env['appointment.question'].create([{
            'name': 'Phone Question 1',
            'sequence': 10,
            'question_type': 'phone',
        }, {
            'name': 'Noise Question',
            'sequence': 15,
            'question_type': 'char',
        }, {
            'name': 'Phone Question 2',
            'sequence': 20,
            'question_type': 'phone',
            'question_required': True
        }])
        self.apt_type_bxls_2days.question_ids = [Command.set((phone_question_1 | phone_question_2).ids)]

        values = {
            'datetime_str': '2022-02-14 10:00:00',
            'duration_str': '1.0',
            'email': 'appointment_phone_test_1@example.com',
            'name': 'Appointment Phone Test 1',
            f'question_{noise_question.id}': 'noise',
            f'question_{phone_question_2.id}': '012345678910',
            'staff_user_id': self.staff_user_bxls.id,
        }
        # Only first phone question should propagate phone
        self.authenticate(None, None)
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", values)
        self.assertEqual(res.status_code, 200, "Response should = OK")
        new_partner = self.env['res.partner'].search([('email', '=', values['email'])])
        self.assertTrue(new_partner)
        self.assertFalse(new_partner.phone)
        new_partner.unlink()

        # Propagate phone to created partner
        values |= {
            f'question_{phone_question_1.id}': '0123456789101112',
            'datetime_str': '2022-02-14 11:00:00',
        }
        self.authenticate(None, None)
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", values)
        self.assertEqual(res.status_code, 200, "Response should = OK")
        new_partner = self.env['res.partner'].search([('email', '=', values['email'])])
        self.assertTrue(new_partner)
        self.assertEqual(new_partner.phone, '0123456789101112')

        # Logged user without phone: propagate it
        self.assertFalse(self.apt_manager.partner_id.phone)
        self.authenticate('apt_manager', 'apt_manager')
        values |= {
            'csrf_token': http.Request.csrf_token(self),
            'email': self.apt_manager.partner_id.email,
            'datetime_str': '2022-02-14 12:00:00',
        }
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", values)
        self.assertEqual(res.status_code, 200, "Response should = OK")
        self.assertEqual(self.apt_manager.partner_id.phone, '0123456789101112')

        # Logged user with different / no phone given: new partner
        values.pop(f'question_{phone_question_1.id}')
        values['datetime_str'] = '2022-02-14 13:00:00'
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", values)
        new_partner = self.env['res.partner'].search([('email', '=', self.apt_manager.partner_id.email)]) - self.apt_manager.partner_id
        self.assertTrue(bool(new_partner))
        self.assertFalse(new_partner.phone)
        self.assertEqual(new_partner.email, self.apt_manager.partner_id.email)
