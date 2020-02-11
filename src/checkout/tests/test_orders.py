from django import urls
from rest_framework import test, status

from user import factories as user_factories
from .. import factories, models
from . import utils


class OrderCreateTestCase(test.APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = urls.reverse('order-list')
        cls.customer = factories.CustomerFactory()
        cls.items = [
            *(factories.ItemFactory(type=models.Item.TYPES.PASS) for i in range(2)),
            *(factories.ItemFactory(type=models.Item.TYPES.ADDON) for i in range(5)),
        ]

    def setUp(self):
        self.client.force_login(self.customer.user)

    def test_should_fail_if_not_logged_in(self):
        # arrange
        items = [self.items[0], self.items[2]]
        order_data = {
            'items': [item.id for item in items],
        }
        payload = utils.build_json_api_payload('order', order_data)
        self.client.logout()

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_fail_if_no_associated_customer(self):
        # arrange
        items = [self.items[0], self.items[2]]
        order_data = {
            'items': [item.id for item in items],
        }
        payload = utils.build_json_api_payload('order', order_data)
        other_user = user_factories.UserFactory()
        self.client.force_login(other_user)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_create_order(self):
        # arrange
        items = [self.items[0], self.items[2]]
        order_data = {
            'items': [item.id for item in items],
        }
        payload = utils.build_json_api_payload('order', order_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertIsNotNone(order)

    def test_should_assign_current_user_customer(self):
        # arrange
        items = [self.items[0], self.items[2]]
        order_data = {
            'items': [item.id for item in items],
        }
        payload = utils.build_json_api_payload('order', order_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.customer, self.customer)

    def test_should_create_order_items(self):
        # arrange
        items = [self.items[0], self.items[2]]
        order_data = {
            'items': [item.id for item in items],
        }
        payload = utils.build_json_api_payload('order', order_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.items.count(), 2)
        self.assertListEqual(
            [order_item.item for order_item in order.items.all()],
            items,
        )

    def test_should_allow_to_add_notes(self):
        # arrange
        items = [self.items[0]]
        notes = 'test notes'
        order_data = {
            'items': [item.id for item in items],
            'notes': notes,
        }
        payload = utils.build_json_api_payload('order', order_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.notes, notes)

    def test_should_allow_to_add_discount_code(self):
        # arrange
        items = [self.items[0]]
        discount_code = factories.DiscountCodeFactory()
        order_data = {
            'items': [item.id for item in items],
            'discount_code': utils.build_json_api_identifier('discount-code', discount_code.id),
        }
        payload = utils.build_json_api_payload('order', order_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.discount_code, discount_code)
