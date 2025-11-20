from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


class CoreSmokeTests(TestCase):
	def test_home_renders(self):
		User = get_user_model()
		u = User.objects.create_user(username='u1', password='p')
		self.client.force_login(u)
		resp = self.client.get(reverse('home'))
		self.assertEqual(resp.status_code, 200)
