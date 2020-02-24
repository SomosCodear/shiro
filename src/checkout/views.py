from django import urls, http, views as django_views
from rest_framework_json_api import views

from . import models, serializers, permissions, mercadopago, afip


class ItemViewSet(views.ReadOnlyModelViewSet):
    queryset = models.Item.objects.order_by('id')
    serializer_class = serializers.ItemSerializer


class CustomerViewSet(views.viewsets.GenericViewSet,
                      views.viewsets.mixins.CreateModelMixin):
    queryset = models.Customer.objects.order_by('id')
    serializer_class = serializers.CustomerSerializer


class OrderViewSet(views.viewsets.GenericViewSet,
                   views.viewsets.mixins.CreateModelMixin):
    queryset = models.Order.objects.order_by('id')
    serializer_class = serializers.OrderSerializer
    permission_classes = (permissions.IsCustomer,)

    def perform_create(self, serializer):
        customer = self.request.user.customer
        order = serializer.save(customer=customer)

        notification_url = self.request.build_absolute_uri(urls.reverse('order-ipn'))
        mercadopago.generate_order_preference(order, notification_url=notification_url)


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

        return http.HttpResponse()
