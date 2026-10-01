from django.urls import path, include
from rest_framework.routers import DefaultRouter
from bookings.views import BookingViewSet

app_name = 'bookings'

router = DefaultRouter()
router.register(r'', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
]