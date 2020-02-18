import enum
import requests
from django.conf import settings

from . import models

API_URL = 'https://api.mercadopago.com'
PREFERENCE_PATH = '/checkout/preferences'
MERCHANT_ORDER_PATH = '/merchant_orders/{id}'


class IPNTopic(enum.Enum):
    PAYMENT = 'payment'
    CHARGEBACK = 'chargebacks'
    MERCHANT_ORDER = 'merchant_order'


class OrderStatus(enum.Enum):
    PAYMENT_REQUIRED = 'payment_required'
    REVERTED = 'reverted'
    PAID = 'paid'
    PARTIALLY_REVERTED = 'partially_reverted'
    PARTIALLY_PAID = 'partially_paid'
    PAYMENT_IN_PROCESS = 'payment_in_process'


def build_url(path, **kwargs):
    assert settings.MERCADOPAGO_ACCESS_TOKEN, 'Access Token for Mercado Pago not set'

    if kwargs:
        path = path.format(**kwargs)

    return f'{API_URL}{path}?access_token={settings.MERCADOPAGO_ACCESS_TOKEN}'


def generate_order_preference(order, notification_url=None):
    url = build_url(PREFERENCE_PATH)
    preference = {
        'payer': {
            'name': order.customer.user.first_name,
            'surname': order.customer.user.last_name,
            'email': order.customer.user.email,
        },
        'items': [
            {
                'id': str(order_item.id),
                'title': order_item.item.name,
                'currency_id': order_item.price.currency.code,
                'picture_url': order_item.item.image.url if order_item.item.image else None,
                'quantity': order_item.amount,
                'unit_price': float(order_item.price.amount),
            } for order_item in order.order_items.all()
        ],
        'external_reference': str(order.id),
        'notification_url': notification_url,
    }

    response = requests.post(url, json=preference)
    response.raise_for_status()

    preference = response.json()
    order.preference_id = preference['id']
    order.status = models.Order.STATUS.IN_PROCESS
    order.save()


def get_merchant_order(id):
    url = build_url(MERCHANT_ORDER_PATH, id=id)

    response = requests.get(url)
    response.raise_for_status()

    return response.json()
