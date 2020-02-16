import json
import faker
import itertools
from unittest import mock
from django import urls
from rest_framework import test, status
from djmoney import money

from user import factories as user_factories
from .. import factories, models
from . import utils

fake = faker.Faker()
PREFERENCE_ID = fake.lexify(text='?????????????????')


@mock.patch(
    'checkout.views.mercadopago.generate_order_preference',
    return_value={'id': PREFERENCE_ID},
)
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

    def build_order_payload(self, items, items_extra=None, discount_code=None, **kwargs):
        items_extra = items_extra if items_extra is not None else [{}] * len(items)

        order_data = {
            'order-items': [
                utils.build_json_api_resource(
                    'order-item',
                    {
                        'item': utils.build_json_api_identifier('item', item.id),
                        **item_extra,
                    },
                )
                for item, item_extra in itertools.zip_longest(items, items_extra)
            ],
            'discount_code': utils.build_json_api_identifier(
                'discount-code',
                discount_code.id,
            ) if discount_code is not None else None,
            **kwargs,
        }
        payload = utils.build_json_api_payload('order', order_data)

        return payload

    def test_should_fail_if_not_logged_in(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)
        self.client.logout()

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_fail_if_no_associated_customer(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)
        other_user = user_factories.UserFactory()
        self.client.force_login(other_user)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_create_order(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertIsNotNone(order)

    def test_should_assign_current_user_customer(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.customer, self.customer)

    def test_should_create_order_items(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.order_items.count(), 2)
        self.assertEqual(
            [order_item.item for order_item in order.order_items.all()],
            items,
        )

    def test_should_allow_to_add_notes(self, *args):
        # arrange
        items = [self.items[0]]
        notes = 'test notes'
        payload = self.build_order_payload(items, notes=notes)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.notes, notes)

    def test_should_allow_to_add_discount_code(self, *args):
        # arrange
        items = [self.items[0]]
        discount_code = factories.DiscountCodeFactory()
        payload = self.build_order_payload(items, discount_code=discount_code)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.discount_code, discount_code)

    def test_should_receive_order_item_options(self, *args):
        # arrange
        items = [factories.ItemFactory(
            type=models.Item.TYPES.PASS,
            options=[factories.ItemOptionFactory.build()],
        )]
        option = {
            'item_option': utils.build_json_api_identifier(
                'item-option',
                items[0].options.first().id,
            ),
            'value': 'some value',
        }
        options = {'options': [utils.build_json_api_resource('order-item-option', option)]}
        payload = self.build_order_payload(items, items_extra=[options])

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        order_item_option = order.order_items.first().options.first()
        self.assertEqual(order_item_option.item_option.id, option['item_option']['id'])
        self.assertEqual(order_item_option.value, option['value'])

    def test_should_validate_at_least_one_item(self, *args):
        # arrangeorder_itemi
        order_data = {}
        payload = utils.build_json_api_payload('order', order_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0]['source']['pointer'], '/data/attributes/order-items')

    def test_should_validate_at_least_one_pass(self, *args):
        # arrange
        items = [self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0]['source']['pointer'], '/data/attributes/order-items')

    def test_should_validate_required_item_options(self, *args):
        # arrange
        items = [factories.ItemFactory(
            type=models.Item.TYPES.PASS,
            options=[factories.ItemOptionFactory.build()],
        )]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0]['source']['pointer'], '/data/attributes/order-items')

    def test_should_return_total(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        total = sum(item.price for item in items)
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total'], str(total.amount))

    def test_should_return_total_with_fixed_value_discount(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        total = sum(item.price for item in items)
        discount = money.Money(total.amount / 3, 'ARS')
        discount_code = factories.DiscountCodeFactory(percentage=None, fixed_value=discount)
        payload = self.build_order_payload(items, discount_code=discount_code)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['total'],
            str(utils.quantize_decimal((total - discount).amount)),
        )

    def test_should_return_total_with_percentage_discount(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        total = sum(item.price for item in items)
        discount_code = factories.DiscountCodeFactory()
        payload = self.build_order_payload(items, discount_code=discount_code)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['total'],
            str(utils.quantize_decimal((total - total * discount_code.percentage / 100).amount)),
        )

    def test_should_return_total_with_fixed_value_item_discount(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        discount = self.items[0].price / 3
        discount_code = factories.DiscountCodeFactory(
            type=models.DiscountCode.TYPES.ITEM,
            percentage=None,
            fixed_value=discount,
            items=items[:1],
        )
        item_totals = [
            items[0].price.amount - discount.amount,
            items[1].price.amount,
        ]
        payload = self.build_order_payload(items, discount_code=discount_code)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total'], str(utils.quantize_decimal(sum(item_totals))))

    def test_should_return_total_with_percentage_item_discount(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        discount_code = factories.DiscountCodeFactory(
            type=models.DiscountCode.TYPES.ITEM,
            items=items[:1],
        )
        item_totals = [
            items[0].price.amount - items[0].price.amount * discount_code.percentage / 100,
            items[1].price.amount,
        ]
        payload = self.build_order_payload(items, discount_code=discount_code)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total'], str(utils.quantize_decimal(sum(item_totals))))

    def test_should_allow_to_include_order_items(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(f'{self.url}?include=order-items', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        included = json.loads(response.content)['included']
        self.assertEqual(
            [int(item['id']) for item in included],
            list(order.order_items.values_list('id', flat=True)),
        )

    def test_should_allow_to_include_items(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(f'{self.url}?include=order-items.item', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(
            [
                int(item['id'])
                for item in json.loads(response.content)['included']
                if item['type'] == 'item'
            ],
            list(order.items.values_list('id', flat=True)),
        )

    def test_should_allow_to_include_options(self, *args):
        # arrange
        items = [factories.ItemFactory(
            type=models.Item.TYPES.PASS,
            options=[factories.ItemOptionFactory.build()],
        )]
        item_option = items[0].options.first().id
        option = {
            'item_option': utils.build_json_api_identifier('item-option', item_option),
            'value': 'some value',
        }
        options = {'options': [utils.build_json_api_resource('order-item-option', option)]}
        payload = self.build_order_payload(items, items_extra=[options])

        # act
        response = self.client.post(f'{self.url}?include=order-items.options', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        included_options = [
            included
            for included in json.loads(response.content)['included']
            if included['type'] == 'order-item-option'
        ]
        self.assertEqual(len(included_options), 1)
        self.assertEqual(
            included_options[0]['relationships']['item-option']['data']['id'],
            str(item_option),
        )

    def test_should_allow_to_include_item_options(self, *args):
        # arrange
        items = [factories.ItemFactory(
            type=models.Item.TYPES.PASS,
            options=[factories.ItemOptionFactory.build()],
        )]
        item_option = items[0].options.first().id
        option = {
            'item_option': utils.build_json_api_identifier('item-option', item_option),
            'value': 'some value',
        }
        options = {'options': [utils.build_json_api_resource('order-item-option', option)]}
        payload = self.build_order_payload(items, items_extra=[options])

        # act
        response = self.client.post(f'{self.url}?include=order-items.options.item_option', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        included_options = [
            included
            for included in json.loads(response.content)['included']
            if included['type'] == 'item-option'
        ]
        self.assertEqual(len(included_options), 1)
        self.assertEqual(included_options[0]['id'], str(item_option))

    def test_included_order_items_should_return_price(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(f'{self.url}?include=order-items', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            [item['attributes']['price'] for item in json.loads(response.content)['included']],
            [str(utils.quantize_decimal(item.price.amount)) for item in items],
        )

    def test_included_items_should_return_price_with_fixed_value_discount(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        discount = self.items[0].price / 3
        discount_code = factories.DiscountCodeFactory(
            type=models.DiscountCode.TYPES.ITEM,
            percentage=None,
            fixed_value=discount,
            items=items[:1],
        )
        item_totals = [
            items[0].price.amount - discount.amount,
            items[1].price.amount,
        ]
        payload = self.build_order_payload(items, discount_code=discount_code)

        # act
        response = self.client.post(f'{self.url}?include=order-items', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            [item['attributes']['total'] for item in json.loads(response.content)['included']],
            [str(utils.quantize_decimal(total)) for total in item_totals],
        )

    def test_included_items_should_return_price_with_percentage_discount(self, *args):
        # arrange
        items = [self.items[0], self.items[2]]
        discount_code = factories.DiscountCodeFactory(
            type=models.DiscountCode.TYPES.ITEM,
            items=items[:1],
        )
        item_totals = [
            items[0].price.amount - items[0].price.amount * discount_code.percentage / 100,
            items[1].price.amount,
        ]
        payload = self.build_order_payload(items, discount_code=discount_code)

        # act
        response = self.client.post(f'{self.url}?include=order-items', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            [item['attributes']['total'] for item in json.loads(response.content)['included']],
            [str(utils.quantize_decimal(total)) for total in item_totals],
        )

    def test_should_create_payment(self, generate_order_preference):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        generate_order_preference.assert_called_once_with(order)

        payment = order.payments.first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, models.Payment.STATUS.CREATED)
        self.assertEqual(payment.external_id, PREFERENCE_ID)

    def test_should_allow_to_include_payment(self, generate_order_preference):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(f'{self.url}?include=payments', payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        payment = order.payments.first()
        returned_payment = json.loads(response.content)['included'][0]
        self.assertEqual(returned_payment['type'], 'payment')
        self.assertEqual(returned_payment['id'], str(payment.id))
