import io
import weasyprint
import templated_email
from django.conf import settings
from django.core import files
from django.template import loader
from django import urls, http, views as django_views
from rest_framework import permissions as drf_permissions
from rest_framework.settings import api_settings
from rest_framework_json_api import views

from . import models, serializers, authentication, permissions, mercadopago, afip, filters


class ItemViewSet(views.ReadOnlyModelViewSet):
    queryset = models.Item.objects.order_by('id')
    serializer_class = serializers.ItemSerializer
    filterset_class = filters.ItemFilterSet


class CustomerViewSet(views.viewsets.GenericViewSet,
                      views.viewsets.mixins.CreateModelMixin):
    queryset = models.Customer.objects.order_by('id')
    serializer_class = serializers.CustomerSerializer


class OrderViewSet(views.viewsets.GenericViewSet,
                   views.AutoPrefetchMixin,
                   views.PreloadIncludesMixin,
                   views.RelatedMixin,
                   views.viewsets.mixins.CreateModelMixin,
                   views.viewsets.mixins.ListModelMixin):
    queryset = models.Order.objects.order_by('id')
    serializer_class = serializers.OrderSerializer
    select_for_includes = {
        '__all__': ['customer', 'discount_code'],
    }
    prefetch_for_includes = {
        '__all__': ['order_items'],
        'order_items': ['order_items__options'],
        'order_items.item': ['order_items__options', 'order_items__item__options'],
        'order_items.item.options': ['order_items__options', 'order_items__item__options'],
    }
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES + [
        authentication.CustomerAuthentication,
    ]
    permission_classes = (drf_permissions.IsAdminUser | permissions.IsCustomer,)

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.auth == authentication.CUSTOMER_AUTH_SCHEMA:
            queryset = queryset.filter(customer=self.request.user.customer)

        return queryset

    def perform_create(self, serializer):
        customer = self.request.user.customer
        order = serializer.save(customer=customer)
        back_urls = serializer.validated_data.get('back_urls')

        notification_url = self.request.build_absolute_uri(urls.reverse('order-ipn'))
        mercadopago.generate_order_preference(
            order,
            notification_url=notification_url,
            back_urls=back_urls,
        )


class OrderIPNView(django_views.View):
    def post(self, request, *args, **kwargs):
        data = request.GET.dict()

        if 'data.id' in data:
            # for some reason mercadopago sends "data.id" in some cases, so we need to normalize it
            data['id'] = data.pop('data.id')

        if 'type' in data:
            # same for "type" and "topic"
            data['topic'] = data.pop('type')

        serializer = serializers.IPNSerializer(data=data)

        if serializer.is_valid() and \
                serializer.validated_data['topic'] == mercadopago.IPNTopic.MERCHANT_ORDER.value:
            order_response = mercadopago.get_merchant_order(serializer.validated_data['id'])
            order = models.Order.objects.get(id=order_response['external_reference'])

            if order.status in [models.Order.STATUS.IN_PROCESS] and \
                    order_response['order_status'] == mercadopago.OrderStatus.PAID.value:
                order.status = models.Order.STATUS.PAID
                order.external_id = order_response['id']
                order.save()

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

        return http.HttpResponse()


class DiscountViewSet(views.viewsets.GenericViewSet, views.viewsets.mixins.ListModelMixin):
    queryset = models.DiscountCode.objects.order_by('id')
    serializer_class = serializers.DiscountCodeSerializer
    filterset_class = filters.DiscountCodeFilterSet
