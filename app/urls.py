"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin  # noqa: F401 (contingency: default AdminSite)
from django.urls import include, path

from app.admin_site import admin_site
from app.health import health
from integracoes.api.token import IntegrationTokenView

urlpatterns = [
    path('health/', health, name='health'),
    path('', include('portal.urls')),
    path('portal/', include(('portal.portal_urls', 'portal'), namespace='portal')),
    path('licencas/', include('licencas.urls')),
    path('portal/integracoes/', include('integracoes.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('api/v1/payments/', include('financeiro.api.urls')),
    path(
        'api/v1/integrations/',
        include(('integracoes.api.urls', 'integrations'), namespace='integrations'),
    ),
    path('api/v1/integrations/token/', IntegrationTokenView.as_view(), name='integrations-token'),
    path('admin/', admin_site.urls),
]

