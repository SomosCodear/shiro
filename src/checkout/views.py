import templated_email
from django import urls, http, views as django_views
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
                   views.viewsets.mixins.CreateModelMixin):
    queryset = models.Order.objects.order_by('id')
    serializer_class = serializers.OrderSerializer
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES + [
        authentication.CustomerAuthentication,
    ]
    permission_classes = (permissions.IsCustomer,)

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

                invoice_number, invoice_cae = afip.generate_cae(order)
                models.Invoice.objects.create(order=order, number=invoice_number, cae=invoice_cae)

                templated_email.send_templated_mail(
                    template_name='order_paid',
                    from_email='no-reply@webconf.tech',
                    recipient_list=[order.customer.user.email],
                    context={
                        'order': order,
                    },
                )

        return http.HttpResponse()


class DiscountViewSet(views.viewsets.GenericViewSet, views.viewsets.mixins.ListModelMixin):
    queryset = models.DiscountCode.objects.order_by('id')
    serializer_class = serializers.DiscountCodeSerializer
    filterset_class = filters.DiscountCodeFilterSet
