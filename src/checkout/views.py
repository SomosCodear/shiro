from rest_framework import decorators, response
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

        mercadopago.generate_order_preference(order)


class PaymentViewSet(views.viewsets.GenericViewSet):
    queryset = models.Payment.objects.none()
    serializer_class = serializers.PaymentSerializer

    @decorators.action(detail=False, methods=['get'])
    def ipn(self, request, *args, **kwargs):
        serializer = serializers.IPNSerializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['topic'] == mercadopago.IPNTopic.PAYMENT.value:
            payment = models.Payment.objects.get(external_id=serializer.validated_data['id'])
            payment_response = mercadopago.get_payment(serializer.validated_data['id'])

            if payment_response['status'] == mercadopago.PaymentStatus.APPROVED.value:
                payment.status = models.Payment.STATUS.APPROVED
                payment.save()

        return response.Response()
