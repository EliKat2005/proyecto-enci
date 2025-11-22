from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    
    # --- ¡CAMBIO IMPORTANTE! ---
    # Ya no usamos 'auth_views.LoginView', usamos nuestra propia vista.
    path('login/', views.login_view, name='login'),
    
    # Vista personalizada de logout que limpia los mensajes
    path('logout/', views.logout_view, name='logout'),
    
    path('registro/', views.registro_view, name='registro'),

    # Vista para que docentes/admin gestionen estudiantes (activar/desactivar)
    path('docente/alumnos/', views.docente_alumnos_view, name='docente_alumnos'),
    path('docente/dashboard/', views.docente_dashboard_view, name='docente_dashboard'),
    # Notificaciones in-app
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/delete-all/', views.delete_all_notifications, name='delete_all_notifications'),
]