from django.urls import path
from . import views

app_name = 'contabilidad'

urlpatterns = [
    path('my/', views.my_companies, name='my_companies'),
    path('<int:empresa_id>/', views.company_detail, name='company_detail'),
    path('create/', views.create_company, name='create_company'),
    path('edit/<int:empresa_id>/', views.edit_company, name='edit_company'),
    path('generate-join/<int:empresa_id>/', views.generate_join_code, name='generate_join_code'),
    path('delete/<int:empresa_id>/', views.delete_company, name='delete_company'),
    path('toggle-visibility/<int:empresa_id>/', views.toggle_visibility, name='toggle_visibility'),
    # AJAX endpoint for toggling visibility without page reload
    path('api/toggle-visibility/<int:empresa_id>/', views.toggle_visibility_api, name='toggle_visibility_api'),
    path('import/', views.import_company, name='import_company'),
    path('<int:empresa_id>/plan/', views.company_plan, name='company_plan'),
    path('<int:empresa_id>/plan/add-account/', views.add_account, name='add_account'),
    path('<int:empresa_id>/diario/', views.company_diario, name='company_diario'),
    path('<int:empresa_id>/diario/add/', views.create_journal_entry, name='create_journal_entry'),
    path('<int:empresa_id>/mayor/', views.company_mayor, name='company_mayor'),
    path('<int:empresa_id>/comment/<str:section>/', views.add_comment, name='add_comment'),
]
