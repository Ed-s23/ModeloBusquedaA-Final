from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Coordenada, RutaPlaneada, PuntoRuta

@admin.register(Coordenada)
class CoordenadaAdmin(admin.ModelAdmin):
    list_display = ['latitud', 'longitud', 'velocidad', 'timestamp']

@admin.register(RutaPlaneada)
class RutaPlaneadaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'algoritmo', 'costo_km', 'activa', 'fecha']

@admin.register(PuntoRuta)
class PuntoRutaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruta', 'orden', 'latitud', 'longitud']