import requests
from django.conf import settings

API_URL = 'https://api.mercadolibre.com'
PREFERENCE_PATH = '/checkout/preferences'


def build_url(path):
    assert settings.MERCADOPAGO_ACCESS_TOKEN, 'Access Token for Mercado Pago not set'

    return f'{API_URL}{path}?access_token={settings.MERCADOPAGO_ACCESS_TOKEN}'


def generate_order_preference(order):
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
    }

    response = requests.post(url, json=preference)
    response.raise_for_status()

    preference = response.json()
    return order.payments.create(external_id=preference['id'])
