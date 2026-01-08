"""
API REST para reportería contable.

Endpoints:
- /api/empresas/ - Listado de empresas
- /api/empresas/{id}/balance/ - Balance de Comprobación (JSON)
- /api/empresas/{id}/estados/ - Balance General / Estado de Resultados (JSON)
- /api/empresas/{id}/libro-mayor/{cuenta_id}/ - Libro Mayor por Cuenta
"""

from datetime import date
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contabilidad.models import Empresa, EmpresaAsiento, EmpresaPlanCuenta, EmpresaTransaccion
from contabilidad.services import EstadosFinancierosService, LibroMayorService


class PlanCuentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmpresaPlanCuenta
        fields = ["id", "codigo", "descripcion", "naturaleza", "es_auxiliar"]


class TransaccionSerializer(serializers.ModelSerializer):
    cuenta_codigo = serializers.CharField(source="cuenta.codigo", read_only=True)
    cuenta_descripcion = serializers.CharField(source="cuenta.descripcion", read_only=True)

    class Meta:
        model = EmpresaTransaccion
        fields = [
            "id",
            "cuenta",
            "cuenta_codigo",
            "cuenta_descripcion",
            "detalle_linea",
            "debe",
            "haber",
        ]


class AsientoSerializer(serializers.ModelSerializer):
    lineas = TransaccionSerializer(source="lineas", many=True, read_only=True)

    class Meta:
        model = EmpresaAsiento
        fields = ["id", "numero", "fecha", "descripcion", "estado", "lineas"]


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ["id", "nombre", "descripcion", "owner", "created_at", "updated_at"]


class BalanceLineSerializer(serializers.Serializer):
    """Serializer para línea del Balance de Comprobación"""

    codigo = serializers.CharField()
    cuenta = serializers.CharField()
    saldo_inicial_deudor = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_inicial_acreedor = serializers.DecimalField(max_digits=15, decimal_places=2)
    debe = serializers.DecimalField(max_digits=15, decimal_places=2)
    haber = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_final_deudor = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_final_acreedor = serializers.DecimalField(max_digits=15, decimal_places=2)


class BalanceGeneralSerializer(serializers.Serializer):
    """Serializer para Balance General"""

    fecha_corte = serializers.DateField()
    activos = serializers.DecimalField(max_digits=15, decimal_places=2)
    pasivos = serializers.DecimalField(max_digits=15, decimal_places=2)
    patrimonio = serializers.DecimalField(max_digits=15, decimal_places=2)
    balanceado = serializers.BooleanField()
    detalle_activos = serializers.ListField()
    detalle_pasivos = serializers.ListField()
    detalle_patrimonio = serializers.ListField()


class EstadoResultadosSerializer(serializers.Serializer):
    """Serializer para Estado de Resultados"""

    ingresos = serializers.DecimalField(max_digits=15, decimal_places=2)
    costos = serializers.DecimalField(max_digits=15, decimal_places=2)
    gastos = serializers.DecimalField(max_digits=15, decimal_places=2)
    utilidad_bruta = serializers.DecimalField(max_digits=15, decimal_places=2)
    utilidad_neta = serializers.DecimalField(max_digits=15, decimal_places=2)
    detalle_ingresos = serializers.ListField()
    detalle_costos = serializers.ListField()
    detalle_gastos = serializers.ListField()


class LibroMayorLineSerializer(serializers.Serializer):
    """Serializer para línea del Libro Mayor"""

    fecha = serializers.DateField()
    numero_asiento = serializers.IntegerField()
    descripcion = serializers.CharField()
    debe = serializers.DecimalField(max_digits=15, decimal_places=2)
    haber = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=15, decimal_places=2)


class EmpresaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para empresas y reportes contables.

    Endpoints:
    - GET /api/empresas/ - Listado
    - GET /api/empresas/{id}/ - Detalle
    - GET /api/empresas/{id}/balance/ - Balance de Comprobación
    - GET /api/empresas/{id}/balance-general/ - Balance General
    - GET /api/empresas/{id}/estado-resultados/ - Estado de Resultados
    - GET /api/empresas/{id}/libro-mayor/{cuenta_id}/ - Libro Mayor
    """

    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar por propietario del usuario"""
        user = self.request.user
        return Empresa.objects.filter(owner=user)

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        """Balance de Comprobación (JSON)"""
        empresa = self.get_object()

        # Parámetros de query
        fecha_inicio_str = request.query_params.get("fecha_inicio")
        fecha_fin_str = request.query_params.get("fecha_fin")

        # Por defecto, incluir todo el historial (sin límites de fecha)
        fecha_inicio = None
        fecha_fin = None

        if fecha_inicio_str:
            try:
                fecha_inicio = date.fromisoformat(fecha_inicio_str)
            except (ValueError, TypeError):
                pass

        if fecha_fin_str:
            try:
                fecha_fin = date.fromisoformat(fecha_fin_str)
            except (ValueError, TypeError):
                pass

        # Calcular balance
        cuentas = empresa.cuentas.filter(es_auxiliar=True).order_by("codigo")
        balance_data = []

        total_debe = Decimal("0.00")
        total_haber = Decimal("0.00")

        for cuenta in cuentas:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin)

            si_d = saldos["saldo_inicial"] if saldos["saldo_inicial"] > 0 else Decimal("0.00")
            si_a = abs(saldos["saldo_inicial"]) if saldos["saldo_inicial"] < 0 else Decimal("0.00")
            sf_d = saldos["saldo_final"] if saldos["saldo_final"] > 0 else Decimal("0.00")
            sf_a = abs(saldos["saldo_final"]) if saldos["saldo_final"] < 0 else Decimal("0.00")

            if si_d or si_a or saldos["debe"] or saldos["haber"] or sf_d or sf_a:
                balance_data.append(
                    {
                        "codigo": cuenta.codigo,
                        "cuenta": cuenta.descripcion,
                        "saldo_inicial_deudor": si_d,
                        "saldo_inicial_acreedor": si_a,
                        "debe": saldos["debe"],
                        "haber": saldos["haber"],
                        "saldo_final_deudor": sf_d,
                        "saldo_final_acreedor": sf_a,
                    }
                )

                total_debe += saldos["debe"]
                total_haber += saldos["haber"]

        return Response(
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "lineas": balance_data,
                "totales": {
                    "debe": total_debe,
                    "haber": total_haber,
                    "cuadrado": total_debe == total_haber,
                },
            }
        )

    @action(detail=True, methods=["get"])
    def balance_general(self, request, pk=None):
        """Balance General (JSON)"""
        empresa = self.get_object()
        fecha_str = request.query_params.get("fecha")

        fecha_corte = date.today()
        if fecha_str:
            try:
                fecha_corte = date.fromisoformat(fecha_str)
            except (ValueError, TypeError):
                pass

        bg = EstadosFinancierosService.balance_general(empresa, fecha_corte)

        # Serializar detalle para JSON
        detalle_activos = [
            {"codigo": d["cuenta"].codigo, "cuenta": d["cuenta"].descripcion, "saldo": d["saldo"]}
            for d in bg["detalle_activos"]
        ]
        detalle_pasivos = [
            {"codigo": d["cuenta"].codigo, "cuenta": d["cuenta"].descripcion, "saldo": d["saldo"]}
            for d in bg["detalle_pasivos"]
        ]
        detalle_patrimonio = [
            {"codigo": d["cuenta"].codigo, "cuenta": d["cuenta"].descripcion, "saldo": d["saldo"]}
            for d in bg["detalle_patrimonio"]
        ]

        return Response(
            {
                "fecha_corte": fecha_corte,
                "activos": bg["activos"],
                "pasivos": bg["pasivos"],
                "patrimonio": bg["patrimonio"],
                "balanceado": bg["balanceado"],
                "detalle_activos": detalle_activos,
                "detalle_pasivos": detalle_pasivos,
                "detalle_patrimonio": detalle_patrimonio,
            }
        )

    @action(detail=True, methods=["get"])
    def estado_resultados(self, request, pk=None):
        """Estado de Resultados (JSON)"""
        empresa = self.get_object()
        fecha_inicio_str = request.query_params.get("fecha_inicio")
        fecha_fin_str = request.query_params.get("fecha_fin")

        hoy = date.today()
        fecha_inicio = date(hoy.year, 1, 1)
        fecha_fin = hoy

        if fecha_inicio_str:
            try:
                fecha_inicio = date.fromisoformat(fecha_inicio_str)
            except (ValueError, TypeError):
                pass

        if fecha_fin_str:
            try:
                fecha_fin = date.fromisoformat(fecha_fin_str)
            except (ValueError, TypeError):
                pass

        er = EstadosFinancierosService.estado_de_resultados(empresa, fecha_inicio, fecha_fin)

        # Serializar detalle
        detalle_ingresos = [
            {"codigo": d["cuenta"].codigo, "cuenta": d["cuenta"].descripcion, "monto": d["monto"]}
            for d in er["detalle_ingresos"]
        ]
        detalle_costos = [
            {"codigo": d["cuenta"].codigo, "cuenta": d["cuenta"].descripcion, "monto": d["monto"]}
            for d in er["detalle_costos"]
        ]
        detalle_gastos = [
            {"codigo": d["cuenta"].codigo, "cuenta": d["cuenta"].descripcion, "monto": d["monto"]}
            for d in er["detalle_gastos"]
        ]

        return Response(
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "ingresos": er["ingresos"],
                "costos": er["costos"],
                "gastos": er["gastos"],
                "utilidad_bruta": er["utilidad_bruta"],
                "utilidad_neta": er["utilidad_neta"],
                "detalle_ingresos": detalle_ingresos,
                "detalle_costos": detalle_costos,
                "detalle_gastos": detalle_gastos,
            }
        )

    @action(detail=True, methods=["get"], url_name="libro-mayor")
    def libro_mayor(self, request, pk=None):
        """Libro Mayor para una cuenta específica"""
        empresa = self.get_object()

        # Obtener el ID de la cuenta de los query params
        cuenta_id = request.query_params.get("cuenta_id")
        if not cuenta_id:
            return Response(
                {"detail": "cuenta_id es requerido"}, status=status.HTTP_400_BAD_REQUEST
            )

        cuenta = get_object_or_404(EmpresaPlanCuenta, id=cuenta_id, empresa=empresa)

        fecha_inicio_str = request.query_params.get("fecha_inicio")
        fecha_fin_str = request.query_params.get("fecha_fin")

        hoy = date.today()
        fecha_inicio = date(hoy.year, 1, 1)
        fecha_fin = hoy

        if fecha_inicio_str:
            try:
                fecha_inicio = date.fromisoformat(fecha_inicio_str)
            except (ValueError, TypeError):
                pass

        if fecha_fin_str:
            try:
                fecha_fin = date.fromisoformat(fecha_fin_str)
            except (ValueError, TypeError):
                pass

        # Obtener transacciones de la cuenta
        transacciones = (
            EmpresaTransaccion.objects.filter(
                cuenta=cuenta,
                asiento__fecha__gte=fecha_inicio,
                asiento__fecha__lte=fecha_fin,
                asiento__anulado=False,
            )
            .select_related("asiento", "cuenta")
            .order_by("asiento__fecha", "asiento__id")
        )

        # Calcular saldos acumulativos
        saldo_acum = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin)[
            "saldo_inicial"
        ]

        lineas = []
        for transaccion in transacciones:
            if transaccion.debe > 0:
                saldo_acum += transaccion.debe
            else:
                saldo_acum -= transaccion.haber

            lineas.append(
                {
                    "fecha": transaccion.asiento.fecha,
                    "numero_asiento": transaccion.asiento.numero_asiento,
                    "descripcion": transaccion.asiento.descripcion_general,
                    "debe": transaccion.debe,
                    "haber": transaccion.haber,
                    "saldo": saldo_acum,
                }
            )

        return Response(
            {
                "cuenta": {
                    "codigo": cuenta.codigo,
                    "descripcion": cuenta.descripcion,
                    "naturaleza": cuenta.naturaleza,
                },
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "lineas": lineas,
            }
        )
