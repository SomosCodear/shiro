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

INVOICE_TYPE = 11
INVOICE_POINT_OF_SALE = 1
INVOICE_CONCEPT = 3
INVOICE_CUIT_DOCUMENT_TYPE = 80
INVOICE_NATIONAL_DOCUMENT_TYPE = 96
INVOICE_SERVICE_DATE_START = '20200529'
INVOICE_SERVICE_DATE_END = '20200530'


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


def generate_cae(order):
    client = get_client()
    customer = order.customer

    identity_document = customer.identity_document
    document_type = INVOICE_NATIONAL_DOCUMENT_TYPE \
        if customer.is_identity_document_cuit else INVOICE_CUIT_DOCUMENT_TYPE
    invoice_number = int(client.CompUltimoAutorizado(INVOICE_TYPE, INVOICE_POINT_OF_SALE)) + 1
    invoice_total = str(utils.quantize_decimal(order.calculate_total().amount))
    invoice_date = timezone.now().strftime('%Y%m%d')

    client.CrearFactura(
        concepto=INVOICE_CONCEPT,
        tipo_doc=document_type,
        nro_doc=identity_document,
        tipo_cbte=INVOICE_TYPE,
        punto_vta=INVOICE_POINT_OF_SALE,
        cbt_desde=invoice_number,
        cbt_hasta=invoice_number,
        imp_total=invoice_total,
        imp_neto=invoice_total,
        fecha_cbte=invoice_date,
        fecha_venc_pago=invoice_date,
        fecha_serv_desde=INVOICE_SERVICE_DATE_START,
        fecha_serv_hasta=INVOICE_SERVICE_DATE_END,
    )
    client.CAESolicitar()

    return invoice_number, client.CAE
