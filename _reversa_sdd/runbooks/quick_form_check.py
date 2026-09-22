import os, sys
PROJECT = r'C:\Users\leand\projetos\scl'
os.chdir(PROJECT); sys.path.insert(0, PROJECT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
import django; django.setup()
from django.template.loader import render_to_string
out = render_to_string('licencas/clientes/form.html', {})
print('clientes form ok:', 'lotesis-form-page' in out)
out = render_to_string('licencas/sistemas/form.html', {})
print('sistemas form ok:', 'lotesis-form-page' in out)
out = render_to_string('licencas/assinaturas/form.html', {})
print('assinaturas form ok:', 'lotesis-form-page' in out)
