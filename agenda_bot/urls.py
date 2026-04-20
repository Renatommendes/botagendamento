from django.contrib import admin
from django.urls import path, include  # inclua o include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('agendamentos.urls')),         # rota raiz do chat
]
