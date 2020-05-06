from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('run', views.run, name='run'),
    path('status/<int:task_id>', views.status, name='status'),
    path('peek/<int:task_id>', views.peek, name='peek'),
    path('cancel/<int:task_id>', views.cancel, name='cancel'),
    path('download/<int:task_id>', views.download, name='download'),
    path('admin/', admin.site.urls),
] + static('/static/', document_root=settings.STATIC_ROOT)