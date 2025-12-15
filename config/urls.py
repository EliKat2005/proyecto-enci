"""
URL Configuration para el proyecto ENCI
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from contabilidad.api import EmpresaViewSet

# Router para API REST
router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresa')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API REST
    path('api/', include(router.urls)),
    
    # Documentación de API (Swagger/OpenAPI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Apps
    path('', include('core.urls')),
    path('contabilidad/', include('contabilidad.urls')),
]