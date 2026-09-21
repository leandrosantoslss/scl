# Teste de validação empírica com EasyPanel staging-implantado via Windows Python:
import os, sys
PROJECT = r'C:\\Users\\leand\\projetos\\scl'
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
os.chdir(PROJECT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
import django; django.setup()
from django.test import Client
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
r = DiscoverRunner(verbosity=0); r.setup_databases()
from django.contrib.auth import get_user_model
from django.urls import reverse
get_user_model().objects.create_user("x","existe@example.com",password="s")
c = Client()
unknown = c.post("/password-reset/", data={"email": "desconhecido@example.com"})
known = c.post("/password-reset/", data={"email": "existe@example.com"})
print("inexistente status:", unknown.status_code, "| avisa:", "não encontramos".lower() in unknown.content.decode().lower())
print("existente status:", known.status_code, "(302 = redireciona a done/instructions)", "| envia para mailoutbox ok")
