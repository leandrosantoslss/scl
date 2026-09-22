import sys
sys.path.insert(0, r'C:\\Users\\leand\\projetos\\scl')
import os; os.chdir(r'C:\\Users\\leand\\projetos\\scl')
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
import django; django.setup()
from django.template.loader import render_to_string
out = render_to_string('404.html', {'request': None})
print('404 ok em', 'error-page' in out)
