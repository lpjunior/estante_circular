from django.contrib import admin
from django.urls import include, path

handler400 = 'core.views.erro_400'
handler403 = 'core.views.erro_403'
handler404 = 'core.views.erro_404'
handler500 = 'core.views.erro_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
]
