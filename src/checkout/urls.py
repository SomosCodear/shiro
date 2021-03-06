from django import urls
from django.views.decorators import csrf
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register('items', views.ItemViewSet)
router.register('customers', views.CustomerViewSet)
router.register('orders', views.OrderViewSet)
router.register('discount-codes', views.DiscountViewSet)

urlpatterns = [
    urls.path('orders/ipn/', csrf.csrf_exempt(views.OrderIPNView.as_view()), name='order-ipn'),
] + router.urls
