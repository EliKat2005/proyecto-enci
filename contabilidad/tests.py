from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Empresa, EmpresaPlanCuenta, EmpresaAsiento


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
