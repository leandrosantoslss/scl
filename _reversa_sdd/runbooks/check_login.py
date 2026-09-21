import os, sys
PROJECT = r'C:\\Users\\leand\\projetos\\scl'
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
os.chdir(PROJECT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
import django
django.setup()
from django.test import Client
c = Client(SERVER_NAME='scl.docsdfe.online')
r = c.get('/login/', secure=True)
content = r.content.decode()
print('login status:', r.status_code)
print('checkbox remember:', 'name="remember_me"' in content)
print('reset link:', '/password-reset/' in content)
