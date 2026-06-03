from django.db import models

# Create your models here.
from django.db import models

class Coordenada(models.Model):
    """Guarda cada punto GPS recibido del ESP32"""
    latitud   = models.FloatField()
    longitud  = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    velocidad = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"({self.latitud}, {self.longitud}) — {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']  # más reciente primero


class RutaPlaneada(models.Model):
    """Guarda una ruta calculada por los algoritmos"""
    nombre      = models.CharField(max_length=100)
    algoritmo   = models.CharField(max_length=50)  # 'astar', 'clarke_wright', 'genetico'
    fecha       = models.DateTimeField(auto_now_add=True)
    costo_km    = models.FloatField(null=True, blank=True)
    activa      = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.algoritmo})"


class PuntoRuta(models.Model):
    """Cada punto dentro de una ruta planeada"""
    ruta     = models.ForeignKey(RutaPlaneada, on_delete=models.CASCADE,
                                  related_name='puntos')
    nombre   = models.CharField(max_length=100)
    latitud  = models.FloatField()
    longitud = models.FloatField()
    orden    = models.IntegerField()  # posición en la ruta

    def __str__(self):
        return f"{self.nombre} (orden {self.orden})"

    class Meta:
        ordering = ['orden']