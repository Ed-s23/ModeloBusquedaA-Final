from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.mapa,                 name='mapa'),
    path('api/gps/',                  views.recibir_gps,          name='recibir_gps'),
    path('api/gps/ultima/',           views.ultima_coordenada,    name='ultima_coordenada'),
    path('api/gps/historial/',        views.historial_coordenadas,name='historial_coordenadas'),
    path('api/ruta/calcular/',        views.calcular_ruta,        name='calcular_ruta'),
    path('api/ruta/desvio/<int:ruta_id>/', views.verificar_desvio, name='verificar_desvio'),
]