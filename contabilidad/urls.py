from django.urls import include, path

from . import views

app_name = "contabilidad"

urlpatterns = [
    # Machine Learning & Analytics APIs
    path("api/ml/", include("contabilidad.urls_api_ml", namespace="api_ml")),
    path("my/", views.my_companies, name="my_companies"),
    path("<int:empresa_id>/", views.company_detail, name="company_detail"),
    path("create/", views.create_company, name="create_company"),
    path("edit/<int:empresa_id>/", views.edit_company, name="edit_company"),
    path("generate-join/<int:empresa_id>/", views.generate_join_code, name="generate_join_code"),
    path("delete/<int:empresa_id>/", views.delete_company, name="delete_company"),
    path("toggle-visibility/<int:empresa_id>/", views.toggle_visibility, name="toggle_visibility"),
    # AJAX endpoint for toggling visibility without page reload
    path(
        "api/toggle-visibility/<int:empresa_id>/",
        views.toggle_visibility_api,
        name="toggle_visibility_api",
    ),
    path("import/", views.import_company, name="import_company"),
    path("<int:empresa_id>/plan/", views.company_plan, name="company_plan"),
    path("<int:empresa_id>/plan/add-account/", views.add_account, name="add_account"),
    path(
        "<int:empresa_id>/plan/<int:cuenta_id>/toggle-status/",
        views.toggle_account_status,
        name="toggle_account_status",
    ),
    path(
        "<int:empresa_id>/plan/<int:cuenta_id>/edit-description/",
        views.edit_account_description,
        name="edit_account_description",
    ),
    path(
        "<int:empresa_id>/plan/<int:cuenta_id>/delete/", views.delete_account, name="delete_account"
    ),
    path("<int:empresa_id>/diario/", views.company_diario, name="company_diario"),
    path("<int:empresa_id>/diario/add/", views.create_journal_entry, name="create_journal_entry"),
    path(
        "<int:empresa_id>/diario/<int:asiento_id>/confirmar/",
        views.confirmar_asiento,
        name="confirmar_asiento",
    ),
    path(
        "<int:empresa_id>/diario/<int:asiento_id>/anular/",
        views.anular_asiento,
        name="anular_asiento",
    ),
    path("<int:empresa_id>/mayor/", views.company_mayor, name="company_mayor"),
    path("<int:empresa_id>/libro-mayor/", views.company_libro_mayor, name="company_libro_mayor"),
    path(
        "<int:empresa_id>/balance/",
        views.company_balance_comprobacion,
        name="company_balance_comprobacion",
    ),
    path(
        "<int:empresa_id>/estados/",
        views.company_estados_financieros,
        name="company_estados_financieros",
    ),
    # Exports - Consolidado (incluye todas las hojas: Balance, Estados, Métricas, etc.)
    path(
        "<int:empresa_id>/export/completo/",
        views.export_empresa_completo_xlsx,
        name="export_empresa_completo",
    ),
    path("<int:empresa_id>/comment/<str:section>/", views.add_comment, name="add_comment"),
    # Machine Learning & AI Dashboard Views
    path("<int:empresa_id>/ml-dashboard/", views.ml_dashboard, name="ml_dashboard"),
    path("<int:empresa_id>/ml-analytics/", views.ml_analytics, name="ml_analytics"),
    path("<int:empresa_id>/ml-predictions/", views.ml_predictions, name="ml_predictions"),
    path("<int:empresa_id>/ml-anomalies/", views.ml_anomalies, name="ml_anomalies"),
    path("<int:empresa_id>/ml-embeddings/", views.ml_embeddings, name="ml_embeddings"),
    path("<int:empresa_id>/ml-health-score/", views.ml_health_score, name="ml_health_score"),
    # ML/AI API Endpoints
    path(
        "api/ml/dashboard/<int:empresa_id>/",
        views.ml_api_dashboard_metrics,
        name="ml_api_dashboard",
    ),
    path("api/ml/analytics/<int:empresa_id>/", views.ml_api_analytics, name="ml_api_analytics"),
    path(
        "api/ml/predictions/<int:empresa_id>/generar/",
        views.ml_api_predictions,
        name="ml_api_predictions",
    ),
    path(
        "api/ml/anomalies/<int:empresa_id>/detectar/",
        views.ml_api_anomalies,
        name="ml_api_anomalies",
    ),
    path(
        "api/ml/embeddings/<int:empresa_id>/buscar/",
        views.ml_api_embeddings,
        name="ml_api_embeddings",
    ),
    # Kardex (Control de Inventarios)
    path(
        "<int:empresa_id>/kardex/",
        views.kardex_lista_productos,
        name="kardex_lista_productos",
    ),
    path(
        "<int:empresa_id>/kardex/<int:producto_id>/",
        views.kardex_producto_detalle,
        name="kardex_producto_detalle",
    ),
    # Crear producto
    path(
        "<int:empresa_id>/kardex/producto/crear/",
        views.kardex_crear_producto,
        name="kardex_crear_producto",
    ),
    # Registrar movimiento
    path(
        "<int:empresa_id>/kardex/<int:producto_id>/movimiento/",
        views.kardex_registrar_movimiento,
        name="kardex_registrar_movimiento",
    ),
]
