import json
from django.http        import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts   import render
from django.conf        import settings

from .models     import Coordenada, RutaPlaneada, PuntoRuta, Caseta, ZonaTrafico
from .algorithms import astar_manhattan, detectar_ruta_critica, calcular_combustible


# ── Recibir coordenadas del ESP32 ──────────────────────────────
@csrf_exempt
def recibir_gps(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            coord = Coordenada.objects.create(
                latitud=data['lat'],
                longitud=data['lng'],
                velocidad=data.get('velocidad', None)
            )
            return JsonResponse({'status': 'ok', 'id': coord.id, 'timestamp': str(coord.timestamp)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)


# ── Última coordenada recibida ─────────────────────────────────
def ultima_coordenada(request):
    try:
        coord = Coordenada.objects.latest('timestamp')
        return JsonResponse({'lat': coord.latitud, 'lng': coord.longitud, 'timestamp': str(coord.timestamp)})
    except Coordenada.DoesNotExist:
        return JsonResponse({'error': 'Sin datos aún'}, status=404)


# ── Historial de coordenadas ───────────────────────────────────
def historial_coordenadas(request):
    coords = Coordenada.objects.all()[:100]
    data   = [{'lat': c.latitud, 'lng': c.longitud, 'timestamp': str(c.timestamp)} for c in coords]
    return JsonResponse({'coordenadas': data})


# ── Calcular ruta óptima con A* Manhattan ───────────────────────
@csrf_exempt
def calcular_ruta(request):
    """
    Body JSON esperado:
    {
        "origen": "NombrePunto",
        "destino": "NombrePunto",
        "puntos": [{"nombre": "...", "lat": .., "lng": ..}, ...],
        "precio_gasolina": 24.5,      (opcional)
        "rendimiento_kmL": 12.0       (opcional)
    }
    """
    if request.method == 'POST':
        try:
            data    = json.loads(request.body)
            origen  = data.get('origen')
            destino = data.get('destino')
            puntos  = data.get('puntos', [])

            precio_gasolina  = data.get('precio_gasolina', 24.5)
            rendimiento_kmL  = data.get('rendimiento_kmL', 12.0)

            if not origen or not destino:
                return JsonResponse({'error': 'Se requiere origen y destino'}, status=400)

            coordenadas = {p['nombre']: (p['lat'], p['lng']) for p in puntos}
            if origen not in coordenadas or destino not in coordenadas:
                return JsonResponse({'error': 'Origen o destino no están en la lista de puntos'}, status=400)

            # Cargar casetas y zonas de tráfico activas desde la BD
            casetas_qs = Caseta.objects.filter(activa=True)
            casetas = [
                {'lat': c.latitud, 'lng': c.longitud, 'costo': c.costo}
                for c in casetas_qs
            ]

            zonas_qs = ZonaTrafico.objects.filter(activa=True)
            zonas_trafico = [
                {
                    'lat': z.latitud, 'lng': z.longitud,
                    'radio_km': z.radio_km, 'nivel': z.nivel,
                    'hora_inicio': z.hora_inicio, 'hora_fin': z.hora_fin
                }
                for z in zonas_qs
            ]

            ruta, dist_km, tiempo_min, polilinea = astar_manhattan(
                coordenadas, origen, destino,
                casetas=casetas,
                zonas_trafico=zonas_trafico,
                precio_gasolina=precio_gasolina,
                rendimiento_kmL=rendimiento_kmL
            )

            litros, costo_gasolina = calcular_combustible(dist_km, rendimiento_kmL, precio_gasolina)

            # Casetas que aplican en esta ruta (informativo)
            casetas_en_ruta = [c.nombre for c in casetas_qs]  # simplificado

            # Guardar en BD
            ruta_obj = RutaPlaneada.objects.create(
                nombre=f"A* Manhattan — {origen} → {destino}",
                algoritmo='astar_manhattan',
                costo_km=dist_km,
                tiempo_min=tiempo_min
            )
            for idx, nombre_punto in enumerate(ruta):
                if nombre_punto in coordenadas:
                    lat, lng = coordenadas[nombre_punto]
                    PuntoRuta.objects.create(ruta=ruta_obj, nombre=nombre_punto, latitud=lat, longitud=lng, orden=idx)

            return JsonResponse({
                'ruta':            ruta,
                'distancia_km':    dist_km,
                'tiempo_min':      tiempo_min,
                'polilinea':       polilinea,   # [[lat,lng], ...] ya calculada en backend
                'litros':          litros,
                'costo_gasolina':  costo_gasolina,
                'ruta_id':         ruta_obj.id,
                'casetas_activas': len(casetas),
                'zonas_activas':   len(zonas_trafico),
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ── Verificar desvío de ruta ───────────────────────────────────
def verificar_desvio(request, ruta_id):
    try:
        coord_actual = Coordenada.objects.latest('timestamp')
        ruta         = RutaPlaneada.objects.get(id=ruta_id)
        puntos       = list(ruta.puntos.values('latitud', 'longitud'))
        es_critica   = detectar_ruta_critica((coord_actual.latitud, coord_actual.longitud), puntos)
        return JsonResponse({
            'es_critica': es_critica,
            'lat_actual': coord_actual.latitud,
            'lng_actual': coord_actual.longitud,
            'ruta_id': ruta_id
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── CASETAS: crear y listar ─────────────────────────────────────
@csrf_exempt
def casetas(request):
    if request.method == 'GET':
        data = [
            {'id': c.id, 'nombre': c.nombre, 'lat': c.latitud, 'lng': c.longitud, 'costo': c.costo}
            for c in Caseta.objects.filter(activa=True)
        ]
        return JsonResponse({'casetas': data})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            c = Caseta.objects.create(
                nombre=data.get('nombre', 'Caseta'),
                latitud=data['lat'],
                longitud=data['lng'],
                costo=data['costo']
            )
            return JsonResponse({'id': c.id, 'nombre': c.nombre, 'lat': c.latitud, 'lng': c.longitud, 'costo': c.costo})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def eliminar_caseta(request, caseta_id):
    if request.method == 'DELETE':
        try:
            Caseta.objects.filter(id=caseta_id).update(activa=False)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ── ZONAS DE TRÁFICO: crear y listar ────────────────────────────
@csrf_exempt
def zonas_trafico(request):
    if request.method == 'GET':
        data = [
            {
                'id': z.id, 'nombre': z.nombre, 'lat': z.latitud, 'lng': z.longitud,
                'radio_km': z.radio_km, 'nivel': z.nivel,
                'hora_inicio': str(z.hora_inicio) if z.hora_inicio else None,
                'hora_fin': str(z.hora_fin) if z.hora_fin else None,
            }
            for z in ZonaTrafico.objects.filter(activa=True)
        ]
        return JsonResponse({'zonas': data})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            z = ZonaTrafico.objects.create(
                nombre=data.get('nombre', 'Zona de tráfico'),
                latitud=data['lat'],
                longitud=data['lng'],
                radio_km=data.get('radio_km', 0.5),
                nivel=data.get('nivel', 'medio'),
                hora_inicio=data.get('hora_inicio') or None,
                hora_fin=data.get('hora_fin') or None,
            )
            return JsonResponse({
                'id': z.id, 'nombre': z.nombre, 'lat': z.latitud, 'lng': z.longitud,
                'radio_km': z.radio_km, 'nivel': z.nivel
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def eliminar_zona(request, zona_id):
    if request.method == 'DELETE':
        try:
            ZonaTrafico.objects.filter(id=zona_id).update(activa=False)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ── Vista principal del mapa ───────────────────────────────────
def mapa(request):
    return render(request, 'gps/mapa.html', {
        'google_maps_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    })
