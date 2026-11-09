from rest_framework.test import APITestCase

from optometrist.models import Optometrist
from patients.models import ScreeningTestResult


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
