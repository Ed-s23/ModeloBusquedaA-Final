import json
from django.http        import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts   import render
from django.conf        import settings

from .models     import Coordenada, RutaPlaneada, PuntoRuta
from .algorithms import astar, clarke_wright, algoritmo_genetico, detectar_ruta_critica


# ── Recibir coordenadas del ESP32 ──────────────────────────────
@csrf_exempt
def recibir_gps(request):
    """El ESP32 hace POST aquí con lat/lng en tiempo real"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            coord = Coordenada.objects.create(
                latitud=data['lat'],
                longitud=data['lng'],
                velocidad=data.get('velocidad', None)
            )
            return JsonResponse({
                'status': 'ok',
                'id': coord.id,
                'timestamp': str(coord.timestamp)
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)


# ── Última coordenada recibida ─────────────────────────────────
def ultima_coordenada(request):
    """Retorna la coordenada GPS más reciente"""
    try:
        coord = Coordenada.objects.latest('timestamp')
        return JsonResponse({
            'lat': coord.latitud,
            'lng': coord.longitud,
            'timestamp': str(coord.timestamp)
        })
    except Coordenada.DoesNotExist:
        return JsonResponse({'error': 'Sin datos aún'}, status=404)


# ── Historial de coordenadas ───────────────────────────────────
def historial_coordenadas(request):
    """Retorna las últimas 100 coordenadas para dibujar la ruta recorrida"""
    coords = Coordenada.objects.all()[:100]
    data   = [{'lat': c.latitud, 'lng': c.longitud,
                'timestamp': str(c.timestamp)} for c in coords]
    return JsonResponse({'coordenadas': data})


# ── Calcular ruta óptima ───────────────────────────────────────
@csrf_exempt
def calcular_ruta(request):
    """
    Recibe puntos y algoritmo, devuelve la ruta óptima.

    Body JSON esperado:
    {
        "algoritmo": "astar" | "clarke_wright" | "genetico",
        "origen": "NombrePunto",
        "puntos": [
            {"nombre": "Punto A", "lat": 19.43, "lng": -99.13},
            {"nombre": "Punto B", "lat": 19.45, "lng": -99.19}
        ]
    }
    """
    if request.method == 'POST':
        try:
            data       = json.loads(request.body)
            algoritmo  = data.get('algoritmo', 'astar')
            origen_key = data.get('origen')
            puntos     = data.get('puntos', [])

            # Construir diccionario de coordenadas
            coordenadas = {p['nombre']: (p['lat'], p['lng']) for p in puntos}

            if algoritmo == 'astar':
                destinos = [p['nombre'] for p in puntos if p['nombre'] != origen_key]
                if not destinos:
                    return JsonResponse({'error': 'Se necesita al menos un destino'}, status=400)
                destino       = destinos[-1]
                ruta, costo   = astar(coordenadas, origen_key, destino)
                resultado     = {'rutas': [ruta], 'costo_km': costo}

            elif algoritmo == 'clarke_wright':
                rutas     = clarke_wright(coordenadas, origen_key)
                costo     = sum(
                    sum(
                        __import__('math').sqrt(
                            (coordenadas[rutas[i][j]][0] - coordenadas[rutas[i][j+1]][0])**2 +
                            (coordenadas[rutas[i][j]][1] - coordenadas[rutas[i][j+1]][1])**2
                        ) * 111.32
                        for j in range(len(rutas[i]) - 1)
                    ) for i in range(len(rutas))
                )
                resultado = {'rutas': rutas, 'costo_km': round(costo, 2)}

            elif algoritmo == 'genetico':
                ruta, costo = algoritmo_genetico(coordenadas)
                resultado   = {'rutas': [ruta], 'costo_km': costo}

            else:
                return JsonResponse({'error': 'Algoritmo no válido'}, status=400)

            # Guardar ruta en base de datos
            ruta_obj = RutaPlaneada.objects.create(
                nombre=f"Ruta {algoritmo} — {origen_key}",
                algoritmo=algoritmo,
                costo_km=resultado['costo_km']
            )
            for idx, nombre_punto in enumerate(resultado['rutas'][0] or []):
                lat, lng = coordenadas[nombre_punto]
                PuntoRuta.objects.create(
                    ruta=ruta_obj,
                    nombre=nombre_punto,
                    latitud=lat,
                    longitud=lng,
                    orden=idx
                )

            resultado['ruta_id'] = ruta_obj.id
            return JsonResponse(resultado)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ── Verificar desvío de ruta ───────────────────────────────────
def verificar_desvio(request, ruta_id):
    """Compara la posición actual del GPS con la ruta planeada"""
    try:
        coord_actual = Coordenada.objects.latest('timestamp')
        ruta         = RutaPlaneada.objects.get(id=ruta_id)
        puntos       = list(ruta.puntos.values('latitud', 'longitud'))

        es_critica = detectar_ruta_critica(
            (coord_actual.latitud, coord_actual.longitud),
            puntos
        )
        return JsonResponse({
            'es_critica': es_critica,
            'lat_actual': coord_actual.latitud,
            'lng_actual': coord_actual.longitud,
            'ruta_id': ruta_id
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── Vista principal del mapa ───────────────────────────────────
def mapa(request):
    """Renderiza el template del mapa con Google Maps"""
    return render(request, 'gps/mapa.html', {
        'google_maps_key': settings.GOOGLE_MAPS_API_KEY
    })