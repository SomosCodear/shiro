import io
import weasyprint
import templated_email
from django.conf import settings
from django.core import files
from django.template import loader
from zappa import asynchronous

from . import models, afip


@asynchronous.task
def generate_invoice(order_id):
    order = models.Order.objects.get(id=order_id)
    invoice_data = afip.generate_invoice(order)

    invoice_html = loader.render_to_string('invoice.html', context=invoice_data)
    invoice_pdf = io.BytesIO()
    invoice_pdf_font_config = weasyprint.fonts.FontConfiguration()
    invoice_pdf_writer = weasyprint.HTML(string=invoice_html)
    invoice_pdf_writer.write_pdf(invoice_pdf, font_config=invoice_pdf_font_config)

    invoice = models.Invoice.objects.create(
        order=order,
        number=invoice_data['invoice_number'],
        cae=invoice_data['invoice_cae'],
        file=files.File(invoice_pdf, f'{invoice_data["invoice_number"]}.pdf'),
    )

    templated_email.send_templated_mail(
        template_name='order_paid',
        from_email=settings.DEFAULT_EMAIL,
        recipient_list=[order.customer.user.email],
        attachments=[
            ('factura.pdf', invoice.file.read(), 'application/pdf'),
        ],
        context={
            'order': order,
        },
    )
