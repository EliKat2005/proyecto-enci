"""
URL Configuration para el proyecto ENCI
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Más adelante, aquí incluiremos las URLs de nuestras apps:
    path('', include('core.urls')),
    path('contabilidad/', include('contabilidad.urls')),
]