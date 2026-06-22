# from django.urls import path
# from . import views

# urlpatterns = [
#     path('',                              views.mapa,                  name='mapa'),

#     # GPS
#     path('api/gps/',                      views.recibir_gps,           name='recibir_gps'),
#     path('api/gps/ultima/',               views.ultima_coordenada,     name='ultima_coordenada'),
#     path('api/gps/historial/',            views.historial_coordenadas, name='historial_coordenadas'),

#     # Ruta A* Manhattan
#     path('api/ruta/calcular/',            views.calcular_ruta,         name='calcular_ruta'),
#     path('api/ruta/desvio/<int:ruta_id>/',views.verificar_desvio,      name='verificar_desvio'),

#     # Casetas
#     path('api/casetas/',                  views.casetas,               name='casetas'),
#     path('api/casetas/<int:caseta_id>/',  views.eliminar_caseta,       name='eliminar_caseta'),

#     # Zonas de tráfico
#     path('api/zonas/',                    views.zonas_trafico,         name='zonas_trafico'),
#     path('api/zonas/<int:zona_id>/',      views.eliminar_zona,         name='eliminar_zona'),
# ]
from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.mapa,                  name='mapa'),

    # GPS
    path('api/gps/',                      views.recibir_gps,           name='recibir_gps'),
    path('api/gps/ultima/',               views.ultima_coordenada,     name='ultima_coordenada'),
    path('api/gps/historial/',            views.historial_coordenadas, name='historial_coordenadas'),

    # Ruta A* Manhattan
    path('api/ruta/calcular/',            views.calcular_ruta,         name='calcular_ruta'),
    path('api/ruta/desvio/<int:ruta_id>/',views.verificar_desvio,      name='verificar_desvio'),

    # Casetas
    path('api/casetas/',                  views.casetas,               name='casetas'),
    path('api/casetas/<int:caseta_id>/',  views.eliminar_caseta,       name='eliminar_caseta'),

    # Zonas de tráfico
    path('api/zonas/',                    views.zonas_trafico,         name='zonas_trafico'),
    path('api/zonas/<int:zona_id>/',      views.eliminar_zona,         name='eliminar_zona'),
]