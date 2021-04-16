import logging
from django.urls import path
from django.db.models.functions import Length
from . import views
from .models import Endpoint
from .utils import TermColor
from django.utils.text import slugify

log = logging.getLogger("ds_app")

urlpatterns = [
    # /_ds/<path>
    # path('<path:url_path>', views.process_endpoint, name='data-endpoint'),
]

# lets try to load our url paths dynamically
endpoints = Endpoint.objects.filter(is_disabled=False).order_by(Length('path').desc())
log.info(f'{TermColor.BOLD}------- dynamically loading endpoints --------{TermColor.ENDC}')
for endpoint in endpoints:
    urlpatterns.append(path(endpoint.path, views.process_endpoint, kwargs={"endpoint_path": endpoint.path}, name='data-endpoint-' + slugify(endpoint.path)))
    log.info(f'     {endpoint.path}')
log.info(f'{TermColor.BOLD}{TermColor.UNDERLINE}------- dynamically loading endpoints --------{TermColor.ENDC}')
