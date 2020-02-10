from rest_framework_json_api import views

from . import models, serializers


class ItemViewSet(views.ReadOnlyModelViewSet):
    queryset = models.Item.objects.order_by('id')
    serializer_class = serializers.ItemSerializer


class CustomerViewSet(views.viewsets.GenericViewSet,
                      views.viewsets.mixins.CreateModelMixin):
    queryset = models.Customer.objects.order_by('id')
    serializer_class = serializers.CustomerSerializer
