import json
import faker
import itertools
from unittest import mock
from django import urls
from django.core import mail
from rest_framework import test, status
from djmoney import money

from user import factories as user_factories
from .. import factories, models, mercadopago
from . import utils

fake = faker.Faker()
PREFERENCE_ID = fake.lexify(text='?????????????????')


@test.override_settings(MERCADOPAGO_CLIENT_ID='xxxx', MERCADOPAGO_CLIENT_SECRET='xxxx')
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

        self.mp_patcher = mock.patch('checkout.mercadopago.get_mp_client', spec=True)
        get_mp_client = self.mp_patcher.start()
        self.mp = get_mp_client.return_value
        self.mp.create_preference.return_value = {'response': {'id': PREFERENCE_ID}}

    def tearDown(self):
        self.mp_patcher.stop()

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

    def test_should_fail_if_not_logged_in(self):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)
        self.client.logout()

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_fail_if_no_associated_customer(self):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)
        other_user = user_factories.UserFactory()
        self.client.force_login(other_user)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_create_order(self):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertIsNotNone(order)

    def test_should_assign_current_user_customer(self):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = models.Order.objects.first()
        self.assertEqual(order.customer, self.customer)

    def test_should_create_order_items(self):
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

    def test_should_allow_to_add_notes(self):
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

    def test_should_allow_to_add_discount_code(self):
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

    def test_should_receive_order_item_options(self):
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

    def test_should_validate_at_least_one_item(self):
        # arrangeorder_itemi
        order_data = {}
        payload = utils.build_json_api_payload('order', order_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0]['source']['pointer'], '/data/attributes/order-items')

    def test_should_validate_at_least_one_pass(self):
        # arrange
        items = [self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0]['source']['pointer'], '/data/attributes/order-items')

    def test_should_validate_required_item_options(self):
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

    def test_should_return_total(self):
        # arrange
        items = [self.items[0], self.items[2]]
        total = sum(item.price for item in items)
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total'], str(total.amount))

    def test_should_return_total_with_fixed_value_discount(self):
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

    def test_should_return_total_with_percentage_discount(self):
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

    def test_should_return_total_with_fixed_value_item_discount(self):
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

    def test_should_return_total_with_percentage_item_discount(self):
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

    def test_should_allow_to_include_order_items(self):
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

    def test_should_allow_to_include_items(self):
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

    def test_should_allow_to_include_options(self):
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

    def test_should_allow_to_include_item_options(self):
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

    def test_should_fail_if_email_item_option_value_is_not_email(self):
        # arrange
        items = [factories.ItemFactory(
            type=models.Item.TYPES.PASS,
            options=[factories.ItemOptionFactory.build(type=models.ItemOption.TYPES.EMAIL)],
        )]
        item_option = items[0].options.first().id
        option = {
            'item_option': utils.build_json_api_identifier('item-option', item_option),
            'value': 'invalid email value',
        }
        options = {'options': [utils.build_json_api_resource('order-item-option', option)]}
        payload = self.build_order_payload(items, items_extra=[options])

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('value', response.data[0]['options'].keys())

    def test_should_not_fail_if_email_item_option_value_is_email(self):
        # arrange
        items = [factories.ItemFactory(
            type=models.Item.TYPES.PASS,
            options=[factories.ItemOptionFactory.build(type=models.ItemOption.TYPES.EMAIL)],
        )]
        item_option = items[0].options.first().id
        option = {
            'item_option': utils.build_json_api_identifier('item-option', item_option),
            'value': fake.email(),
        }
        options = {'options': [utils.build_json_api_resource('order-item-option', option)]}
        payload = self.build_order_payload(items, items_extra=[options])

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_included_order_items_should_return_price(self):
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

    def test_included_items_should_return_price_with_fixed_value_discount(self):
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

    def test_included_items_should_return_price_with_percentage_discount(self):
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

    def test_should_creates_preference_and_sets_in_process_status(self):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.mp.create_preference.assert_called()

        order = models.Order.objects.first()
        self.assertEqual(response.data['preference_id'], PREFERENCE_ID)
        self.assertEqual(response.data['status'], models.Order.STATUS.IN_PROCESS)
        self.assertEqual(order.preference_id, PREFERENCE_ID)
        self.assertEqual(order.status, models.Order.STATUS.IN_PROCESS)

    def test_should_provide_notification_url(self):
        # arrange
        items = [self.items[0], self.items[2]]
        payload = self.build_order_payload(items)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.mp.create_preference.call_args[0][0]['notification_url'],
            f'http://testserver{urls.reverse("order-ipn")}',
        )

    def test_should_provide_back_urls_if_included_in_payload(self):
        # arrange
        items = [self.items[0], self.items[2]]
        back_urls = {
            'success': fake.url(),
            'pending': fake.url(),
            'failure': fake.url(),
        }
        payload = self.build_order_payload(items, back_urls=back_urls)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key, value in back_urls.items():
            self.assertEqual(self.mp.create_preference.call_args[0][0]['back_urls'][key], value)


@test.override_settings(MERCADOPAGO_ACCESS_TOKEN='xxxx')
class OrderIPNTestCase(test.APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = urls.reverse('order-ipn')

    def setUp(self):
        self.order = factories.OrderFactory(status=models.Order.STATUS.IN_PROCESS)
        self.order_external_id = fake.numerify('######')
        self.invoice_number = 5
        self.invoice_cae = '1234'

        self.mp_patcher = mock.patch('checkout.mercadopago.get_mp_client', spec=True)
        get_mp_client = self.mp_patcher.start()
        self.mp = get_mp_client.return_value
        self.mp.create_preference.return_value = {'id': PREFERENCE_ID}

        self.afip_patcher = mock.patch('checkout.views.afip', spec=True)
        self.afip = self.afip_patcher.start()
        self.afip.generate_invoice.return_value = {
            'invoice_number': self.invoice_number,
            'invoice_cae': self.invoice_cae,
            'invoice_code': fake.numerify('######'),
        }

        self.weasyprint_patcher = mock.patch('checkout.views.weasyprint')
        self.weasyprint = self.weasyprint_patcher.start()

    def tearDown(self):
        self.weasyprint.stop()
        self.afip_patcher.stop()
        self.mp_patcher.stop()

    def build_notification_url(self):
        return f'{self.url}?topic={mercadopago.IPNTopic.MERCHANT_ORDER.value}&' \
            f'id={self.order_external_id}'

    def test_should_mark_order_as_paid_if_completed(self):
        # arrange
        order_payload = {
            'id': self.order_external_id,
            'order_status': mercadopago.OrderStatus.PAID.value,
            'external_reference': str(self.order.id),
        }
        url = mercadopago.build_path(mercadopago.MERCHANT_ORDER_PATH, id=self.order_external_id)
        self.mp.get.return_value = {'response': order_payload}

        # act
        response = self.client.post(self.build_notification_url())

        # assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mp.get.assert_called_with(url)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, models.Order.STATUS.PAID)
        self.assertEqual(self.order.external_id, self.order_external_id)

    def test_should_generate_invoice_if_completed(self):
        # arrange
        order_payload = {
            'id': self.order_external_id,
            'order_status': mercadopago.OrderStatus.PAID.value,
            'external_reference': str(self.order.id),
        }
        self.mp.get.return_value = {'response': order_payload}

        # act
        response = self.client.post(self.build_notification_url())

        # assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.afip.generate_invoice.assert_called_once_with(self.order)
        self.weasyprint.HTML.return_value.write_pdf.assert_called_once()

        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.invoice)
        self.assertEqual(self.order.invoice.number, self.invoice_number)
        self.assertEqual(self.order.invoice.cae, self.invoice_cae)

    def test_should_send_email_to_customer_if_completed(self):
        # arrange
        order_payload = {
            'id': self.order_external_id,
            'order_status': mercadopago.OrderStatus.PAID.value,
            'external_reference': str(self.order.id),
        }
        self.mp.get.return_value = {'response': order_payload}

        # act
        self.client.post(self.build_notification_url())

        # assert
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(), [self.order.customer.user.email])
        self.assertEqual(mail.outbox[0].subject, '¡Gracias por tu compra!')

    @mock.patch('checkout.models.signals.order_paid')
    def test_should_fire_an_order_paid_signal(self, order_paid):
        # arrange
        order_payload = {
            'id': self.order_external_id,
            'order_status': mercadopago.OrderStatus.PAID.value,
            'external_reference': str(self.order.id),
        }
        self.mp.get.return_value = {'response': order_payload}

        # act
        self.client.post(self.build_notification_url())

        # assert
        order_paid.send.assert_called_once_with(sender=models.Order, order=self.order)
