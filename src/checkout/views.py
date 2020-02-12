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

        preference = mercadopago.generate_order_preference(order)
        order.payments.create(external_id=preference['id'])
