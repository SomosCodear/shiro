from django import urls, http, views as django_views
from rest_framework_json_api import views

from . import models, serializers, permissions, mercadopago


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

        notification_url = self.request.build_absolute_uri(urls.reverse('payment-ipn'))
        mercadopago.generate_order_preference(order, notification_url=notification_url)


class IPNView(django_views.View):
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
                serializer.validated_data['topic'] == mercadopago.IPNTopic.PAYMENT.value:
            payment_response = mercadopago.get_payment(serializer.validated_data['id'])
            payment = models.Payment.objects.get(order__id=payment_response['external_reference'])

            if payment.status in [payment.STATUS.CREATED, payment.STATUS.IN_PROCESS] and \
                    payment_response['status'] == mercadopago.PaymentStatus.APPROVED.value:
                payment.status = models.Payment.STATUS.APPROVED
                payment.external_id = payment_response['id']
                payment.save()

        return http.HttpResponse()
