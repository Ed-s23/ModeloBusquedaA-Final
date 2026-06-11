# from django.contrib import admin

# # Register your models here.
# from django.contrib import admin
# from .models import Coordenada, RutaPlaneada, PuntoRuta

# @admin.register(Coordenada)
# class CoordenadaAdmin(admin.ModelAdmin):
#     list_display = ['latitud', 'longitud', 'velocidad', 'timestamp']

# @admin.register(RutaPlaneada)
# class RutaPlaneadaAdmin(admin.ModelAdmin):
#     list_display = ['nombre', 'algoritmo', 'costo_km', 'activa', 'fecha']

# @admin.register(PuntoRuta)
# class PuntoRutaAdmin(admin.ModelAdmin):
#     list_display = ['nombre', 'ruta', 'orden', 'latitud', 'longitud']


from django.contrib import admin
from .models import Coordenada, RutaPlaneada, PuntoRuta, Vehiculo, Caseta, ZonaTrafico


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'tipo_combustible', 'nivel_combustible',
                     'rendimiento_kmL', 'tanque_litros', 'activo']
    list_editable = ['nivel_combustible', 'activo']
    list_filter   = ['tipo_combustible', 'activo']


@admin.register(Caseta)
class CasetaAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'latitud', 'longitud', 'costo', 'activa']
    list_editable = ['costo', 'activa']
    list_filter   = ['activa']


@admin.register(ZonaTrafico)
class ZonaTraficoAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'nivel_trafico', 'radio_km',
                     'hora_inicio', 'hora_fin', 'activa']
    list_editable = ['nivel_trafico', 'activa']
    list_filter   = ['nivel_trafico', 'activa']


@admin.register(RutaPlaneada)
class RutaPlaneadaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'algoritmo', 'distancia_km',
                    'tiempo_min', 'combustible_L', 'fecha', 'activa']
    list_filter  = ['algoritmo', 'activa', 'es_alterna']
    readonly_fields = ['fecha']


@admin.register(PuntoRuta)
class PuntoRutaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruta', 'orden', 'tipo', 'latitud', 'longitud']
    list_filter  = ['tipo']


@admin.register(Coordenada)
class CoordenadaAdmin(admin.ModelAdmin):
    list_display = ['latitud', 'longitud', 'velocidad', 'timestamp']
    readonly_fields = ['timestamp']  