from py3afipws import wsaa, wsfev1
from django.conf import settings
from django.utils import timezone

from . import models

INVOICE_TYPE = 11
INVOICE_POINT_OF_SALE = 1
INVOICE_CONCEPT = 3
INVOICE_NATIONAL_DOCUMENT_TYPE = 96
INVOICE_PASSPORT_DOCUMENT_TYPE = 94
INVOICE_SERVICE_DATE_START = '20200529'
INVOICE_SERVICE_DATE_END = '20200530'


def get_client():
    assert settings.AFIP_CERTIFICATE, 'AFIP Certificate not set'
    assert settings.AFIP_PRIVATE_KEY, 'AFIP Private Key not set'
    assert settings.AFIP_CUIT, 'AFIP CUIT not set'
    certificate = settings.AFIP_CERTIFICATE.replace('\\n', '\n')
    private_key = settings.AFIP_PRIVATE_KEY.replace('\\n', '\n')

    wsaa_client = wsaa.WSAA()
    tra = wsaa_client.CreateTRA('wsfe', ttl=15000)
    cms = wsaa_client.SignTRA(tra, certificate, private_key)

    wsaa_client.Conectar()
    wsaa_client.LoginCMS(cms)

    wsfev1_client = wsfev1.WSFEv1()
    wsfev1_client.Token = wsaa_client.Token.encode('utf-8')
    wsfev1_client.Sign = wsaa_client.Sign.encode('utf-8')
    wsfev1_client.Cuit = settings.AFIP_CUIT
    wsfev1_client.Conectar()

    return wsfev1_client


def generate_cae(order):
    client = get_client()

    document_type = INVOICE_NATIONAL_DOCUMENT_TYPE \
        if order.customer.identity_document_type == models.Customer.IDENTITY_DOCUMENT_TYPES.DNI \
        else INVOICE_PASSPORT_DOCUMENT_TYPE
    invoice_number = int(client.CompUltimoAutorizado(INVOICE_TYPE, INVOICE_POINT_OF_SALE)) + 1
    invoice_total = order.calculate_total()
    invoice_date = timezone.now().strftime('%Y%m%d')

    client.CrearFactura(
        concepto=INVOICE_CONCEPT,
        tipo_doc=document_type,
        nro_doc=order.customer.identity_document,
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

    return (client.CAE, client.Vencimiento)
