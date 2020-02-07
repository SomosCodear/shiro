from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register('items', views.ItemViewSet, 'item')
router.register('customers', views.CustomerViewSet, 'customer')

urlpatterns = router.urls
