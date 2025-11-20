from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Mantenemos esto para logout

urlpatterns = [
    path('', views.home_view, name='home'),
    
    # --- ¡CAMBIO IMPORTANTE! ---
    # Ya no usamos 'auth_views.LoginView', usamos nuestra propia vista.
    path('login/', views.login_view, name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        template_name='core/logout.html'
    ), name='logout'),
    
    path('registro/', views.registro_view, name='registro'),

    # Vista para que docentes/admin gestionen estudiantes (activar/desactivar)
    path('docente/alumnos/', views.docente_alumnos_view, name='docente_alumnos'),
    path('docente/dashboard/', views.docente_dashboard_view, name='docente_dashboard'),
    # Notificaciones in-app
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]