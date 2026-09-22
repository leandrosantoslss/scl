import os, sys
PROJECT = r'C:\Users\leand\projetos\scl'
os.chdir(PROJECT); sys.path.insert(0, PROJECT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
os.environ['SECRET_KEY'] = 'x'*44
os.environ['DEBUG'] = 'true'
os.environ['ALLOWED_HOSTS'] = 'localhost'
os.environ['DATABASE_URL'] = 'sqlite://'
import django; django.setup()
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
from django.conf import settings
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
setup_test_environment()
runner = DiscoverRunner(verbosity=0); runner.setup_databases()
from django.core.management import call_command; call_command('migrate', verbosity=0)
from django.contrib.auth import get_user_model
from django.test import Client
user = get_user_model().objects.create_user('cad','c@example.com','s')
from django.contrib.auth.models import Group
group, _ = Group.objects.get_or_create(name='Cadastro')
user.groups.add(group)
c = Client(); c.force_login(user)

# POST com dados
payload = {
    "nome": "Empresa Testadora",
    "cnpjcpf": "12.345.678/0001-95",
    "email": "test@example.com",
    "telefone": "11999999999",
    "ativo": "on",
    "cep": "01001-000",
    "endereco": "Praça da Sé",
    "endnumero": "1",
    "endbairro": "Sé",
    "endcomplemento": "-",
    "endUF": "SP",
    "endcidade": "São Paulo",
    "endcodpais": "55",
    "endpais": "Brasil",
}
r = c.post('/licencas/clientes/novo/', data=payload)
print('POST status:', r.status_code)
from licencas.models import Cliente
print('Cliente.count:', Cliente.objects.count())
print('Cliente first:', Cliente.objects.first())

from licencas.forms.clientes import ClienteForm
form2 = ClienteForm(data=payload)
form2.is_valid()
print('formulier errors:', dict(form2.errors))
