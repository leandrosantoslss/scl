import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

import django

django.setup()
from django.contrib.staticfiles import finders  # noqa: E402

print("portal.css ->", finders.find("css/portal.css"))
print("theme.min.css ->", finders.find("vendor/duralux/css/theme.min.css"))
