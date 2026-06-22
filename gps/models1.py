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
        ordering = ['-timestamp']


class RutaPlaneada(models.Model):
    """Guarda una ruta calculada por A* Manhattan"""
    nombre       = models.CharField(max_length=100)
    algoritmo    = models.CharField(max_length=50, default='astar_manhattan')
    fecha        = models.DateTimeField(auto_now_add=True)
    costo_km     = models.FloatField(null=True, blank=True)
    tiempo_min   = models.FloatField(null=True, blank=True)
    activa       = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.algoritmo})"


class PuntoRuta(models.Model):
    """Cada punto dentro de una ruta planeada"""
    ruta     = models.ForeignKey(RutaPlaneada, on_delete=models.CASCADE, related_name='puntos')
    nombre   = models.CharField(max_length=100)
    latitud  = models.FloatField()
    longitud = models.FloatField()
    orden    = models.IntegerField()

    def __str__(self):
        return f"{self.nombre} (orden {self.orden})"

    class Meta:
        ordering = ['orden']


# ─── NUEVO: Casetas de cobro ────────────────────────────────────────
class Caseta(models.Model):
    """Caseta de cobro — penaliza rutas que pasan cerca"""
    nombre   = models.CharField(max_length=100, default='Caseta')
    latitud  = models.FloatField()
    longitud = models.FloatField()
    costo    = models.FloatField(help_text="Costo en MXN")
    activa   = models.BooleanField(default=True)
    fecha    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"🛣️ {self.nombre} — ${self.costo} MXN"

    class Meta:
        verbose_name = "Caseta"
        verbose_name_plural = "Casetas"


# ─── NUEVO: Zonas de tráfico ─────────────────────────────────────────
NIVEL_TRAFICO_CHOICES = [
    ('bajo', 'Bajo'),
    ('medio', 'Medio'),
    ('alto', 'Alto'),
    ('critico', 'Crítico'),
]

class ZonaTrafico(models.Model):
    """Zona circular que penaliza rutas según nivel de tráfico y horario"""
    nombre        = models.CharField(max_length=100, default='Zona de tráfico')
    latitud       = models.FloatField()
    longitud      = models.FloatField()
    radio_km      = models.FloatField(default=0.5)
    nivel         = models.CharField(max_length=10, choices=NIVEL_TRAFICO_CHOICES, default='medio')
    hora_inicio   = models.TimeField(null=True, blank=True, help_text="Vacío = aplica todo el día")
    hora_fin      = models.TimeField(null=True, blank=True, help_text="Vacío = aplica todo el día")
    activa        = models.BooleanField(default=True)
    fecha         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"🚦 {self.nombre} ({self.get_nivel_display()})"

    class Meta:
        verbose_name = "Zona de tráfico"
        verbose_name_plural = "Zonas de tráfico"
