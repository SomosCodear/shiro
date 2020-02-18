import enum
import mercadopago
from django.conf import settings

from . import models

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


def get_mp_client():
    assert settings.MERCADOPAGO_CLIENT_ID, 'Client Id for Mercado Pago not set'
    assert settings.MERCADOPAGO_CLIENT_SECRET, 'Client Secret for Mercado Pago not set'

    return mercadopago.MP(settings.MERCADOPAGO_CLIENT_ID, settings.MERCADOPAGO_CLIENT_SECRET)


def build_path(path, **kwargs):
    if kwargs:
        path = path.format(**kwargs)

    return path


def generate_order_preference(order, notification_url=None):
    mp = get_mp_client()
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

    preference = mp.create_preference(preference)
    order.preference_id = preference['response']['id']
    order.status = models.Order.STATUS.IN_PROCESS
    order.save()


def get_merchant_order(id):
    mp = get_mp_client()
    url = build_path(MERCHANT_ORDER_PATH, id=id)

    return mp.get(url)['response']
