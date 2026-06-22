from django.contrib import admin
from .models import Coordenada, RutaPlaneada, PuntoRuta, Caseta, ZonaTrafico


@admin.register(Coordenada)
class CoordenadaAdmin(admin.ModelAdmin):
    list_display = ['latitud', 'longitud', 'velocidad', 'timestamp']


@admin.register(RutaPlaneada)
class RutaPlaneadaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'algoritmo', 'costo_km', 'tiempo_min', 'activa', 'fecha']


@admin.register(PuntoRuta)
class PuntoRutaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruta', 'orden', 'latitud', 'longitud']


@admin.register(Caseta)
class CasetaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'costo', 'latitud', 'longitud', 'activa', 'fecha']
    list_editable = ['activa']


@admin.register(ZonaTrafico)
class ZonaTraficoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nivel', 'radio_km', 'hora_inicio', 'hora_fin', 'activa', 'fecha']
    list_editable = ['activa']
    list_filter = ['nivel', 'activa']
