from django import urls
from django.views.decorators import csrf
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register('items', views.ItemViewSet)
router.register('customers', views.CustomerViewSet)
router.register('orders', views.OrderViewSet)

urlpatterns = router.urls + [
    urls.path('payments/ipn/', csrf.csrf_exempt(views.IPNView.as_view()), name='payment-ipn'),
]
