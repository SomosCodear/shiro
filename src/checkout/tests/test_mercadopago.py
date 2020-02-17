import faker
import requests_mock
from django import test

from .. import models, factories, mercadopago

fake = faker.Faker()
PREFERENCE_ID = fake.lexify(text='?????????????????')


@test.override_settings(MERCADOPAGO_ACCESS_TOKEN='xxxx')
class GenerateOrderPreferenceTestCase(test.TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.order = factories.OrderFactory()

    def setUp(self):
        self.requests = requests_mock.Mocker()
        self.requests.start()
        self.requests.post(
            mercadopago.build_url(mercadopago.PREFERENCE_PATH),
            json={'id': PREFERENCE_ID},
        )

    def tearDown(self):
        self.requests.stop()

    def test_should_include_customer_information(self):
        # arrange
        expected_payer = {
            'name': self.order.customer.user.first_name,
            'surname': self.order.customer.user.last_name,
            'email': self.order.customer.user.email,
        }

        # act
        mercadopago.generate_order_preference(self.order)

        # assert
        self.assertTrue(self.requests.called)
        self.assertEqual(self.requests.last_request.json()['payer'], expected_payer)

    def test_should_include_items_information(self):
        # arrange
        expected_items = [
            {
                'id': str(order_item.id),
                'title': order_item.item.name,
                'currency_id': order_item.price.currency.code,
                'picture_url': None,
                'quantity': order_item.amount,
                'unit_price': float(order_item.price.amount),
            } for order_item in self.order.order_items.all()
        ]

        # act
        mercadopago.generate_order_preference(self.order)

        # assert
        self.assertTrue(self.requests.called)
        self.assertEqual(self.requests.last_request.json()['items'], expected_items)

    def test_should_include_order_as_external_reference(self):
        # act
        mercadopago.generate_order_preference(self.order)

        # assert
        self.assertTrue(self.requests.called)
        self.assertEqual(
            self.requests.last_request.json()['external_reference'],
            str(self.order.id),
        )

    def test_should_create_payment(self):
        # act
        mercadopago.generate_order_preference(self.order)

        # assert
        payment = self.order.payments.first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, models.Payment.STATUS.CREATED)
        self.assertEqual(payment.external_id, PREFERENCE_ID)
