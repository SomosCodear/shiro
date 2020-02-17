import faker
import requests_mock
from django import urls
from rest_framework import test, status

from .. import models, factories, mercadopago


@requests_mock.Mocker()
@test.override_settings(MERCADOPAGO_ACCESS_TOKEN='xxxx')
class CustomerCreateTestCase(test.APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = urls.reverse('payment-ipn')
        cls.fake = faker.Faker()

    def setUp(self):
        self.payment = factories.PaymentFactory()
        self.payment_external_id = self.fake.numerify('######')

    def build_notification_url(self):
        return f'{self.url}?type={mercadopago.IPNTopic.PAYMENT.value}&' \
            f'data.id={self.payment_external_id}'

    def test_should_mark_payment_as_paid_if_completed(self, requests):
        # arrange
        payment_payload = {
            'id': self.payment_external_id,
            'status': mercadopago.PaymentStatus.APPROVED.value,
            'external_reference': str(self.payment.order.id),
        }
        requests.get(
            mercadopago.build_url(mercadopago.PAYMENT_PATH, id=self.payment_external_id),
            json=payment_payload,
        )

        # act
        response = self.client.post(self.build_notification_url())

        # assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(requests.called)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, models.Payment.STATUS.APPROVED)
        self.assertEqual(self.payment.external_id, self.payment_external_id)
