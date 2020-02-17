from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register('items', views.ItemViewSet)
router.register('customers', views.CustomerViewSet)
router.register('orders', views.OrderViewSet)
router.register('payments', views.PaymentViewSet)

urlpatterns = router.urls
