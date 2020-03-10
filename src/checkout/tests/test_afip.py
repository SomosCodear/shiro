import faker
import freezegun
from unittest import mock
from django import test
from django.utils import timezone
from django.core.cache import caches

from .. import factories, afip
from . import utils

fake = faker.Faker()


@mock.patch('checkout.afip.wsfev1')
@mock.patch('checkout.afip.wsaa')
@test.override_settings(
    AFIP_CERTIFICATE='CERTIFICATE',
    AFIP_PRIVATE_KEY='PRIVATE_KEY',
    AFIP_CUIT='12345',
)
class AfipGetClientTestCase(test.TestCase):
    def test_should_store_token_and_sign_in_cache(self, wsaa, wsfev1):
        # arrange
        token = fake.lexify(text='?????????')
        sign = fake.lexify(text='?????????')
        expiration = fake.date_time_between(start_date='now').strftime(afip.EXPIRATION_DATE_FORMAT)
        wsaa.WSAA.return_value.Token = token
        wsaa.WSAA.return_value.Sign = sign
        wsaa.WSAA.return_value.ObtenerTagXml.return_value = expiration

        # act
        afip.get_client()

        # assert
        self.assertEqual(caches['afip'].get(afip.TOKEN_CACHE_KEY), token)
        self.assertEqual(caches['afip'].get(afip.SIGN_CACHE_KEY), sign)
        self.assertEqual(caches['afip'].get(afip.EXPIRATION_CACHE_KEY), expiration)

    def test_should_use_stored_token_and_sign_from_cache(self, wsaa, wsfev1):
        # arrange
        token = fake.lexify(text='?????????')
        sign = fake.lexify(text='?????????')
        expiration = timezone.make_aware(fake.date_time_between(
            start_date=timezone.now() + timezone.timedelta(hours=1),
            end_date=timezone.now() + timezone.timedelta(days=1),
        )).strftime(afip.EXPIRATION_DATE_FORMAT)
        caches['afip'].set(afip.TOKEN_CACHE_KEY, token)
        caches['afip'].set(afip.SIGN_CACHE_KEY, sign)
        caches['afip'].set(afip.EXPIRATION_CACHE_KEY, expiration)

        # act
        client = afip.get_client()

        # assert
        self.assertEqual(client.Token, token.encode('utf-8'))
        self.assertEqual(client.Sign, sign.encode('utf-8'))

    def test_should_not_use_stored_token_and_sign_if_expired(self, wsaa, wsfev1):
        # arrange
        old_token = fake.lexify(text='?????????')
        old_sign = fake.lexify(text='?????????')
        old_expiration = timezone.make_aware(fake.date_time_between(
            end_date='now',
        )).strftime(afip.EXPIRATION_DATE_FORMAT)
        caches['afip'].set(afip.TOKEN_CACHE_KEY, old_token)
        caches['afip'].set(afip.SIGN_CACHE_KEY, old_sign)
        caches['afip'].set(afip.EXPIRATION_CACHE_KEY, old_expiration)

        new_token = fake.lexify(text='?????????')
        new_sign = fake.lexify(text='?????????')
        new_expiration = fake.date_time_between(
            start_date='now',
        ).strftime(afip.EXPIRATION_DATE_FORMAT)
        wsaa.WSAA.return_value.Token = new_token
        wsaa.WSAA.return_value.Sign = new_sign
        wsaa.WSAA.return_value.ObtenerTagXml.return_value = new_expiration

        # act
        client = afip.get_client()

        # assert
        self.assertEqual(client.Token, new_token.encode('utf-8'))
        self.assertEqual(client.Sign, new_sign.encode('utf-8'))
        self.assertEqual(caches['afip'].get(afip.TOKEN_CACHE_KEY), new_token)
        self.assertEqual(caches['afip'].get(afip.SIGN_CACHE_KEY), new_sign)
        self.assertEqual(caches['afip'].get(afip.EXPIRATION_CACHE_KEY), new_expiration)


@mock.patch('checkout.afip.get_client')
class AfipGenerateInvoiceTestCase(test.TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.order = factories.OrderFactory()

    @freezegun.freeze_time(timezone.now())
    def test_should_create_cae(self, get_client):
        # arrange
        invoice_number = 5
        invoice_total = str(utils.quantize_decimal(self.order.calculate_total().amount))
        invoice_date = timezone.now().strftime('%Y%m%d')

        afip_client = mock.MagicMock()
        afip_client.CompUltimoAutorizado.return_value = invoice_number - 1
        afip_client.CAE = 1234
        afip_client.Vencimiento = '20200309'
        get_client.return_value = afip_client

        expected_invoice = {
            'concepto': afip.INVOICE_CONCEPT,
            'tipo_doc': afip.INVOICE_NATIONAL_DOCUMENT_TYPE,
            'nro_doc': self.order.customer.identity_document,
            'tipo_cbte': afip.INVOICE_TYPE,
            'punto_vta': afip.INVOICE_POINT_OF_SALE,
            'cbt_desde': invoice_number,
            'cbt_hasta': invoice_number,
            'imp_total': invoice_total,
            'imp_neto': invoice_total,
            'fecha_cbte': invoice_date,
            'fecha_venc_pago': invoice_date,
            'fecha_serv_desde': afip.INVOICE_SERVICE_DATE_START,
            'fecha_serv_hasta': afip.INVOICE_SERVICE_DATE_END,
        }

        # act
        invoice = afip.generate_invoice(self.order)

        # assert
        afip_client.CrearFactura.assert_called_once_with(**expected_invoice)
        afip_client.CAESolicitar.assert_called_once()
        self.assertEqual(invoice['invoice_number'], invoice_number)
        self.assertEqual(invoice['invoice_cae'], afip_client.CAE)
