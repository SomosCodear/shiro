import faker
from unittest import mock
from django import test

from .. import models, factories, mercadopago

fake = faker.Faker()
PREFERENCE_ID = fake.lexify(text='?????????????????')


@test.override_settings(MERCADOPAGO_CLIENT_ID='xxxx', MERCADOPAGO_CLIENT_SECRET='xxxx')
class GenerateOrderPreferenceTestCase(test.TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.order = factories.OrderFactory()

    def setUp(self):
        self.mp_patcher = mock.patch('checkout.mercadopago.get_mp_client', spec=True)
        get_mp_client = self.mp_patcher.start()
        self.mp = get_mp_client.return_value
        self.mp.create_preference.return_value = {'response': {'id': PREFERENCE_ID}}

    def tearDown(self):
        self.mp_patcher.stop()

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
        self.mp.create_preference.assert_called()
        self.assertEqual(self.mp.create_preference.call_args[0][0]['payer'], expected_payer)

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
        self.mp.create_preference.assert_called()
        self.assertEqual(self.mp.create_preference.call_args[0][0]['items'], expected_items)

    def test_should_include_order_as_external_reference(self):
        # act
        mercadopago.generate_order_preference(self.order)

        # assert
        self.mp.create_preference.assert_called()
        self.assertEqual(
            self.mp.create_preference.call_args[0][0]['external_reference'],
            str(self.order.id),
        )

    def test_should_include_given_notification_url(self):
        # arrange
        notification_url = 'http://test.com'

        # act
        mercadopago.generate_order_preference(self.order, notification_url=notification_url)

        # assert
        self.mp.create_preference.assert_called()
        self.assertEqual(
            self.mp.create_preference.call_args[0][0]['notification_url'],
            notification_url,
        )

    def test_should_update_order(self):
        # act
        mercadopago.generate_order_preference(self.order)

        # assert
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, models.Order.STATUS.IN_PROCESS)
        self.assertEqual(self.order.preference_id, PREFERENCE_ID)
