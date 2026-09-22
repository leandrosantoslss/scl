import os, sys, re
PROJECT = r'C:\Users\leand\projetos\scl'
os.chdir(PROJECT)
sys.path.insert(0, PROJECT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
import django; django.setup()
from django.template.loader import render_to_string
out = render_to_string('partials/_topbar.html', {'user': None})
print('fullscreen:', 'fullscreen-toggle' in out)
print('tema:', 'theme-toggle' in out)
print('logout dropdown:', 'dropdown' in out)
