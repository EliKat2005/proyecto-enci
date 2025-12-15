from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from datetime import date

from .models import Empresa, EmpresaPlanCuenta, EmpresaAsiento, PeriodoContable, NaturalezaCuenta, TipoCuenta
from .services import AsientoService, EstadosFinancierosService


class ContabilidadSmokeTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='owner', password='pass')
		# crear empresa
		self.empresa = Empresa.objects.create(nombre='Empresa Test', owner=self.user, visible_to_supervisor=True)

	def test_company_plan_page_renders(self):
		self.client.force_login(self.user)
		url = reverse('contabilidad:company_plan', args=[self.empresa.id])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

	def test_add_account_creates_account(self):
		self.client.force_login(self.user)
		url = reverse('contabilidad:add_account', args=[self.empresa.id])
		data = {
			'codigo': '1',
			'descripcion': 'ACTIVOS',
			'tipo': 'Activo',
			'naturaleza': 'Deudora',
			'estado_situacion': '1',
		}
		resp = self.client.post(url, data)
		# redirect back to plan
		self.assertEqual(resp.status_code, 302)
		exists = EmpresaPlanCuenta.objects.filter(empresa=self.empresa, codigo='1').exists()
		self.assertTrue(exists)

	def test_company_diario_page_renders(self):
		self.client.force_login(self.user)
		# crear un asiento mínimo
		EmpresaAsiento.objects.create(empresa=self.empresa, fecha='2025-01-01', descripcion_general='Prueba', creado_por=self.user)
		url = reverse('contabilidad:company_diario', args=[self.empresa.id])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)


class CierrePeriodoTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='owner', password='pass')
		self.empresa = Empresa.objects.create(nombre='Empresa Cierre', owner=self.user, visible_to_supervisor=True)
		# Plan mínimo
		activo = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='1', descripcion='ACTIVO', tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA, es_auxiliar=False, estado_situacion=True)
		pasivo = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='2', descripcion='PASIVO', tipo=TipoCuenta.PASIVO, naturaleza=NaturalezaCuenta.ACREEDORA, es_auxiliar=False, estado_situacion=True)
		patrimonio = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='3', descripcion='PATRIMONIO', tipo=TipoCuenta.PATRIMONIO, naturaleza=NaturalezaCuenta.ACREEDORA, es_auxiliar=False, estado_situacion=True)
		self.caja = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='1.1.01', descripcion='Caja', tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA, es_auxiliar=True, estado_situacion=True, padre=activo, activa=True)
		self.banco = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='1.1.02', descripcion='Banco', tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA, es_auxiliar=True, estado_situacion=True, padre=activo, activa=True)
		self.capital = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='3.1', descripcion='Capital', tipo=TipoCuenta.PATRIMONIO, naturaleza=NaturalezaCuenta.ACREEDORA, es_auxiliar=True, estado_situacion=True, padre=patrimonio, activa=True)
		self.ventas = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='4.1', descripcion='Ventas', tipo=TipoCuenta.INGRESO, naturaleza=NaturalezaCuenta.ACREEDORA, es_auxiliar=True, estado_situacion=False)
		self.costo = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='5.1', descripcion='Costo Ventas', tipo=TipoCuenta.COSTO, naturaleza=NaturalezaCuenta.DEUDORA, es_auxiliar=True, estado_situacion=False)
		self.gastos = EmpresaPlanCuenta.objects.create(empresa=self.empresa, codigo='6.1.01', descripcion='Sueldos', tipo=TipoCuenta.GASTO, naturaleza=NaturalezaCuenta.DEUDORA, es_auxiliar=True, estado_situacion=False)
		PeriodoContable.objects.create(empresa=self.empresa, anio=2025, mes=1, estado=PeriodoContable.EstadoPeriodo.ABIERTO)

		# Asiento apertura
		AsientoService.crear_asiento(
			empresa=self.empresa,
			fecha=date(2025, 1, 1),
			descripcion='Apertura',
			lineas=[
				{'cuenta_id': self.banco.id, 'detalle': 'Aporte', 'debe': Decimal('10000.00'), 'haber': Decimal('0.00')},
				{'cuenta_id': self.capital.id, 'detalle': 'Capital', 'debe': Decimal('0.00'), 'haber': Decimal('10000.00')},
			],
			creado_por=self.user,
			auto_confirmar=True
		)

		# Venta + costo + gasto
		AsientoService.crear_asiento(
			empresa=self.empresa,
			fecha=date(2025, 1, 10),
			descripcion='Venta',
			lineas=[
				{'cuenta_id': self.banco.id, 'detalle': 'Cobro', 'debe': Decimal('2000.00'), 'haber': Decimal('0.00')},
				{'cuenta_id': self.ventas.id, 'detalle': 'Ingreso', 'debe': Decimal('0.00'), 'haber': Decimal('2000.00')},
			],
			creado_por=self.user,
			auto_confirmar=True
		)
		AsientoService.crear_asiento(
			empresa=self.empresa,
			fecha=date(2025, 1, 10),
			descripcion='Costo',
			lineas=[
				{'cuenta_id': self.costo.id, 'detalle': 'Costo', 'debe': Decimal('1200.00'), 'haber': Decimal('0.00')},
				{'cuenta_id': self.banco.id, 'detalle': 'Salida', 'debe': Decimal('0.00'), 'haber': Decimal('1200.00')},
			],
			creado_por=self.user,
			auto_confirmar=True
		)
		AsientoService.crear_asiento(
			empresa=self.empresa,
			fecha=date(2025, 1, 31),
			descripcion='Gasto',
			lineas=[
				{'cuenta_id': self.gastos.id, 'detalle': 'Sueldos', 'debe': Decimal('500.00'), 'haber': Decimal('0.00')},
				{'cuenta_id': self.banco.id, 'detalle': 'Pago', 'debe': Decimal('0.00'), 'haber': Decimal('500.00')},
			],
			creado_por=self.user,
			auto_confirmar=True
		)

	def test_asiento_de_cierre_cancela_resultados(self):
		# Generar cierre al último día del mes
		cierre = EstadosFinancierosService.asiento_de_cierre(self.empresa, date(2025, 1, 31), self.user)
		self.assertIsInstance(cierre, EmpresaAsiento)
		# El asiento debe tener líneas que cancelen ventas/gastos/costos
		cuentas_en_cierre = set(cierre.lineas.values_list('cuenta__codigo', flat=True))
		self.assertIn('4.1', cuentas_en_cierre)  # ventas
		self.assertIn('5.1', cuentas_en_cierre)  # costo
		self.assertIn('6.1.01', cuentas_en_cierre)  # gastos
		# Patrimonio debe incluir Resultados del Ejercicio
		self.assertTrue(EmpresaPlanCuenta.objects.filter(empresa=self.empresa, descripcion__icontains='Resultados del Ejercicio').exists())

	def test_balance_general_cuadrado_tras_cierre(self):
		EstadosFinancierosService.asiento_de_cierre(self.empresa, date(2025, 1, 31), self.user)
		balance = EstadosFinancierosService.balance_general(self.empresa, date(2025, 1, 31))
		self.assertTrue(balance['balanceado'])
