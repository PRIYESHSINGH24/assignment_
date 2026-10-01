from django.urls import path, include
from rest_framework.routers import DefaultRouter
from diagnostics.views import DiagnosticCentreViewSet, DiagnosticTestViewSet, CentreTestViewSet

app_name = 'diagnostics'

router = DefaultRouter()
router.register(r'centres', DiagnosticCentreViewSet, basename='centre')
router.register(r'tests', DiagnosticTestViewSet, basename='test')
router.register(r'centre-tests', CentreTestViewSet, basename='centre-test')

urlpatterns = [
    path('', include(router.urls)),
]