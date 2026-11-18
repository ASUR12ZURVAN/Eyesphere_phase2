from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from rest_framework.test import APITestCase

from optometrist.models import Optometrist, Patient
from patients.models import ScreeningTestResult


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PatientRegistrationPageTests(TestCase):
    def setUp(self):
        self.url = reverse('patient_registration')
        self.data = {
            'name': 'Registration Patient',
            'date_of_birth': '1990-04-15',
            'gender': 'female',
            'phone_number': '+1 (415) 555-0134',
            'email': 'new.patient@example.com',
            'address': '42 Sample Road',
            'diabetes': 'true',
        }

    def test_registration_creates_account_and_emails_generated_credentials(self):
        response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['registration_complete'])
        self.assertEqual(response['Cache-Control'], 'no-store')

        user = Optometrist.objects.get(phone_number='+14155550134')
        patient = Patient.objects.get(phone_number='+14155550134')
        self.assertEqual(user.role, 'patient')
        self.assertTrue(user.check_password(response.context['password']))
        self.assertEqual(patient.patient_account_id, '+14155550134')
        self.assertEqual(patient.date_of_birth.isoformat(), '1990-04-15')
        self.assertTrue(patient.diabetes)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('+14155550134', mail.outbox[0].body)
        self.assertIn(response.context['password'], mail.outbox[0].body)

    def test_rejects_duplicate_phone_number(self):
        Optometrist.objects.create_user(
            phone_number='+14155550134',
            name='Existing Patient',
            password='existing-password',
            role='patient',
        )

        response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'already registered', status_code=400)
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_page_provides_a_scannable_png_qr_code(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('patient_registration_qr'))

        with patch('patients.views.qrcode.make', wraps=__import__('qrcode').make) as make_qr:
            qr_response = self.client.get(reverse('patient_registration_qr'))

        make_qr.assert_called_once_with('https://eyesphere-phase2.onrender.com/patient/register/')
        self.assertEqual(qr_response.status_code, 200)
        self.assertEqual(qr_response['Content-Type'], 'image/png')
        self.assertTrue(qr_response.content.startswith(b'\x89PNG\r\n\x1a\n'))


class AppointmentBookingApiTests(APITestCase):
    def setUp(self):
        self.user = Optometrist.objects.create_user(
            phone_number='9990001113',
            name='Booking Patient',
            password='test-pass-123',
            role='patient',
        )
        self.client.force_authenticate(user=self.user)
        self.url = '/patient/api/bookings/'

    def test_create_and_list_booking(self):
        response = self.client.post(self.url, {
            'date': '08,09,2026',
            'time': '14:30',
            'tests': {'Vision Test': 250, 'Dry Eye': 125.5},
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['booking']['total_price'], '375.50')

        listing = self.client.get(self.url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data['bookings']), 1)

    def test_rejects_non_dd_mm_yyyy_date(self):
        response = self.client.post(self.url, {
            'date': '2026-09-08',
            'time': '14:30',
            'tests': {'Vision Test': 250},
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('dd,mm,yyyy', response.data['error'])


class ScreeningResultsApiTests(APITestCase):
    def setUp(self):
        self.user = Optometrist.objects.create_user(
            phone_number='9990001114',
            name='Screening Patient',
            password='test-pass-123',
            role='patient',
        )
        self.client.force_authenticate(user=self.user)
        self.url = '/patient/api/screening-results/'

    def test_gets_only_authenticated_patient_results(self):
        ScreeningTestResult.objects.create(
            user=self.user,
            test_type='vision',
            result_data={'left_eye': '20/20', 'right_eye': '20/25'},
            score='L:20/20 R:20/25',
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['result'], {
            'left_eye': '20/20',
            'right_eye': '20/25',
        })

    def test_filters_by_test_type(self):
        ScreeningTestResult.objects.create(user=self.user, test_type='vision', score='20/20')
        ScreeningTestResult.objects.create(user=self.user, test_type='blink', score='18')

        response = self.client.get(f'{self.url}?test_type=blink')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['test_type'], 'blink')

    def test_returns_direct_score_for_non_vision_results(self):
        ScreeningTestResult.objects.create(
            user=self.user,
            test_type='dryeye',
            result_data={'osdi_score': 12, 'severity': 'Normal'},
            score='OSDI: 12/100 - Normal',
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['result'], {
            'score': 'OSDI: 12/100 - Normal',
        })
