import freezegun
from unittest import mock
from django import test
from django.utils import timezone

from .. import factories, afip


@mock.patch('checkout.afip.get_client')
class AfipGenerateCAETestCase(test.TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.order = factories.OrderFactory()

    @freezegun.freeze_time(timezone.now())
    def test_should_create_cae(self, get_client):
        # arrange
        invoice_number = 5
        invoice_total = self.order.calculate_total()
        invoice_date = timezone.now().strftime('%Y%m%d')

        afip_client = mock.MagicMock()
        afip_client.CompUltimoAutorizado.return_value = invoice_number - 1
        afip_client.CAE = 1234
        afip_client.Vencimiento = '20200230'
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
        cae, expiration = afip.generate_cae(self.order)

        # assert
        afip_client.CrearFactura.assert_called_once_with(**expected_invoice)
        afip_client.CAESolicitar.assert_called_once()
        self.assertEqual(cae, afip_client.CAE)
        self.assertEqual(expiration, afip_client.Vencimiento)
