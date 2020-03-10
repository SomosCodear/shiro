from py3afipws import wsaa, wsfev1
from django.conf import settings
from django.utils import timezone
from django.core.cache import caches

from . import utils

TRA_TTL = 36000
TOKEN_CACHE_KEY = 'TOKEN'
SIGN_CACHE_KEY = 'SIGN'
EXPIRATION_CACHE_KEY = 'EXPIRATION'
EXPIRATION_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
WSFEV1_DATE_FORMAT = '%Y%m%d'

COMPANY_START_OF_OPERATIONS = timezone.datetime(year=2019, month=10, day=1)
INVOICE_TYPE = 11
INVOICE_POINT_OF_SALE = 1
INVOICE_CONCEPT = 3
INVOICE_CUIT_DOCUMENT_TYPE = 80
INVOICE_NATIONAL_DOCUMENT_TYPE = 96
INVOICE_SERVICE_START_DATE = timezone.datetime(year=2020, month=5, day=29)
INVOICE_SERVICE_END_DATE = timezone.datetime(year=2020, month=5, day=30)


def _authenticate():
    wsaa_client = wsaa.WSAA()
    auth_info = caches['afip'].get_many([TOKEN_CACHE_KEY, SIGN_CACHE_KEY, EXPIRATION_CACHE_KEY])

    if EXPIRATION_CACHE_KEY in auth_info and (
        timezone.datetime.strptime(auth_info[EXPIRATION_CACHE_KEY], EXPIRATION_DATE_FORMAT) <
        timezone.now()
    ):
        auth_info.clear()

    if TOKEN_CACHE_KEY not in auth_info or SIGN_CACHE_KEY not in auth_info:
        assert settings.AFIP_CERTIFICATE, 'AFIP Certificate not set'
        assert settings.AFIP_PRIVATE_KEY, 'AFIP Private Key not set'
        certificate = settings.AFIP_CERTIFICATE.replace('\\n', '\n')
        private_key = settings.AFIP_PRIVATE_KEY.replace('\\n', '\n')

        tra = wsaa_client.CreateTRA('wsfe', ttl=TRA_TTL)
        cms = wsaa_client.SignTRA(tra, certificate, private_key)

        wsaa_client.Conectar()
        wsaa_client.LoginCMS(cms)
        auth_info[TOKEN_CACHE_KEY] = wsaa_client.Token
        auth_info[SIGN_CACHE_KEY] = wsaa_client.Sign
        auth_info[EXPIRATION_CACHE_KEY] = wsaa_client.ObtenerTagXml('expirationTime')

        caches['afip'].set_many(auth_info, TRA_TTL)

    return auth_info[TOKEN_CACHE_KEY], auth_info[SIGN_CACHE_KEY]


def get_client():
    assert settings.AFIP_CUIT, 'AFIP CUIT not set'
    token, sign = _authenticate()

    wsfev1_client = wsfev1.WSFEv1()
    wsfev1_client.Token = token.encode('utf-8')
    wsfev1_client.Sign = sign.encode('utf-8')
    wsfev1_client.Cuit = settings.AFIP_CUIT
    wsfev1_client.Conectar()

    return wsfev1_client


def generate_verification_number(code):
    odd = sum(int(code[index]) for index in range(1, len(code), 2)) * 3
    even = sum(int(code[index]) for index in range(0, len(code), 2))
    total = odd + even

    return 10 - total % 10


def generate_invoice_code(invoice):
    code = '{}{:03d}{:05d}{}'.format(
        invoice['company_cuit'],
        invoice['invoice_type'],
        invoice['invoice_point_of_sale'],
        invoice['invoice_cae'],
        invoice['invoice_payment_date'].strftime(WSFEV1_DATE_FORMAT),
    )

    verification_code = generate_verification_number(code)
    code += str(verification_code)

    return code


def generate_invoice(order):
    client = get_client()
    customer = order.customer
    now = timezone.now()
    invoice = {
        'company_name': 'Comunidad de Desarrolladores de Argentina',
        'company_name_short': 'CoDeAr',
        'company_address': 'TBD',
        'company_cuit': settings.AFIP_CUIT,
        'company_brute_income': 12345678,
        'company_start_of_operations': timezone.datetime.strptime('2019-10-01', '%Y-%m-%d'),
        'client_identity_document': customer.identity_document,
        'client_document_type': INVOICE_NATIONAL_DOCUMENT_TYPE
        if customer.is_identity_document_cuit else INVOICE_CUIT_DOCUMENT_TYPE,
        'client_name': customer.user.first_name,
        'invoice_point_of_sale': INVOICE_POINT_OF_SALE,
        'invoice_type_letter': 'c',
        'invoice_type': INVOICE_TYPE,
        'invoice_number': int(client.CompUltimoAutorizado(INVOICE_TYPE, INVOICE_POINT_OF_SALE)) + 1,
        'invoice_date': now,
        'invoice_payment_date': now,
        'invoice_service_start_date': INVOICE_SERVICE_START_DATE,
        'invoice_service_end_date': INVOICE_SERVICE_END_DATE,
        'invoice_raw_total': str(utils.quantize_decimal(order.calculate_base_total().amount)),
        'invoice_discount': str(utils.quantize_decimal(order.calculate_discount().amount)),
        'invoice_total': str(utils.quantize_decimal(order.calculate_total().amount)),
        'invoice_items': [
            {
                'name': order_item.item.name,
                'amount': order_item.amount,
                'unit_price': str(utils.quantize_decimal(order_item.price.amount)),
                'total_price': str(
                    utils.quantize_decimal(order_item.calculate_base_total().amount),
                ),
            } for order_item in order.order_items.all()
        ],
    }

    formatted_invoice_date = invoice['invoice_date'].strftime(WSFEV1_DATE_FORMAT)
    formatted_service_start_date = invoice['invoice_service_start_date'].strftime(
        WSFEV1_DATE_FORMAT,
    )
    formatted_service_end_date = invoice['invoice_service_end_date'].strftime(
        WSFEV1_DATE_FORMAT,
    )

    client.CrearFactura(
        concepto=INVOICE_CONCEPT,
        tipo_doc=invoice['client_document_type'],
        nro_doc=invoice['client_identity_document'],
        tipo_cbte=invoice['invoice_type'],
        punto_vta=invoice['invoice_point_of_sale'],
        cbt_desde=invoice['invoice_number'],
        cbt_hasta=invoice['invoice_number'],
        imp_total=invoice['invoice_total'],
        imp_neto=invoice['invoice_total'],
        fecha_cbte=formatted_invoice_date,
        fecha_venc_pago=formatted_invoice_date,
        fecha_serv_desde=formatted_service_start_date,
        fecha_serv_hasta=formatted_service_end_date,
    )
    client.CAESolicitar()

    invoice['invoice_cae'] = client.CAE
    invoice['invoice_cae_expiration_date'] = timezone.datetime.strptime(
        client.Vencimiento,
        WSFEV1_DATE_FORMAT,
    )
    invoice['invoice_code'] = generate_invoice_code(invoice)

    return invoice
