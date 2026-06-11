import heapq
import math
import random
import requests
from datetime import datetime


# ─── OSRM: DISTANCIA REAL POR CARRETERA ───────────────────────────────────────
def osrm_distancia(lat1, lon1, lat2, lon2):
    """
    Consulta el servidor público de OSRM para obtener
    distancia real (km) y duración (minutos) entre dos puntos.
    Devuelve (distancia_km, duracion_min) o None si falla.
    """
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?overview=false"
    )
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get("code") == "Ok":
            ruta = data["routes"][0]
            distancia_km  = ruta["distance"] / 1000.0
            duracion_min  = ruta["duration"] / 60.0
            return distancia_km, duracion_min
    except Exception:
        pass
    # Fallback: distancia euclidiana si OSRM no responde
    return _distancia_euclidiana(lat1, lon1, lat2, lon2), None


def osrm_geometria(lat1, lon1, lat2, lon2):
    """
    Igual que osrm_distancia pero también devuelve la geometría
    (lista de [lat, lng]) para dibujar la ruta real en el mapa.
    """
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?overview=full&geometries=geojson"
    )
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get("code") == "Ok":
            ruta      = data["routes"][0]
            dist_km   = ruta["distance"] / 1000.0
            dur_min   = ruta["duration"] / 60.0
            coords    = ruta["geometry"]["coordinates"]  # [[lon,lat], ...]
            # OSRM devuelve [lon, lat] → invertimos a [lat, lon] para Leaflet
            polilinea = [[c[1], c[0]] for c in coords]
            return dist_km, dur_min, polilinea
    except Exception:
        pass
    return _distancia_euclidiana(lat1, lon1, lat2, lon2), None, []


# ─── HEURÍSTICAS ──────────────────────────────────────────────────────────────
def _distancia_euclidiana(lat1, lon1, lat2, lon2):
    """Distancia aproximada en km (Pitágoras sobre grados)."""
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) * 111.32


def heuristica_manhattan(lat1, lon1, lat2, lon2):
    """
    Heurística Manhattan adaptada a coordenadas geográficas.
    Suma las diferencias absolutas en latitud y longitud (en km).
    Ideal para ciudades con calles en cuadrícula.
    """
    dlat = abs(lat1 - lat2) * 111.32
    dlon = abs(lon1 - lon2) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    return dlat + dlon


# ─── PENALIZACIONES (casetas + tráfico) ───────────────────────────────────────
def _penalizacion_casetas(lat1, lon1, lat2, lon2, casetas):
    """
    Suma el costo MXN de las casetas que están cerca del segmento.
    casetas: lista de dicts {'lat', 'lng', 'costo'}
    """
    total = 0.0
    for c in casetas:
        # Si la caseta está a menos de 2 km del segmento la contamos
        d1 = _distancia_euclidiana(lat1, lon1, c['lat'], c['lng'])
        d2 = _distancia_euclidiana(lat2, lon2, c['lat'], c['lng'])
        if min(d1, d2) < 2.0:
            total += c['costo']
    return total


def _factor_trafico(lat, lon, zonas_trafico):
    """
    Devuelve un factor multiplicador según las zonas de tráfico activas.
    zonas_trafico: lista de dicts {'lat', 'lng', 'radio_km', 'nivel', 'hora_inicio', 'hora_fin'}
    """
    FACTORES = {'bajo': 1.2, 'medio': 1.5, 'alto': 2.0, 'critico': 3.0}
    hora_actual = datetime.now().time()
    factor = 1.0

    for z in zonas_trafico:
        # ¿Estamos dentro del radio de la zona?
        dist = _distancia_euclidiana(lat, lon, z['lat'], z['lng'])
        if dist > z.get('radio_km', 0.5):
            continue

        # ¿Estamos en el horario de tráfico?
        hi = z.get('hora_inicio')
        hf = z.get('hora_fin')
        if hi and hf:
            if not (hi <= hora_actual <= hf):
                continue

        f = FACTORES.get(z.get('nivel', 'medio'), 1.0)
        factor = max(factor, f)   # tomamos el peor factor que aplique

    return factor


def _costo_segmento(nombre_a, nombre_b, coordenadas,
                    casetas=None, zonas_trafico=None, precio_gasolina=20.0,
                    rendimiento_kmL=12.0):
    """
    Costo compuesto de un segmento A→B:
      dist_km (OSRM) + penalización casetas + factor tráfico + costo gasolina
    Devuelve (costo_total, dist_km, duracion_min)
    """
    casetas       = casetas or []
    zonas_trafico = zonas_trafico or []

    lat1, lon1 = coordenadas[nombre_a]
    lat2, lon2 = coordenadas[nombre_b]

    dist_km, dur_min = osrm_distancia(lat1, lon1, lat2, lon2)

    # Costo base en km
    costo = dist_km

    # Penalización por casetas (convertimos MXN a "km equivalentes" /10)
    costo += _penalizacion_casetas(lat1, lon1, lat2, lon2, casetas) / 10.0

    # Factor de tráfico sobre el punto medio del segmento
    lat_mid = (lat1 + lat2) / 2
    lon_mid = (lon1 + lon2) / 2
    costo *= _factor_trafico(lat_mid, lon_mid, zonas_trafico)

    return costo, dist_km, dur_min


# ══════════════════════════════════════════════════════════════════════════════
# ALGORITMO 1 — A* CON HEURÍSTICA MANHATTAN
# ══════════════════════════════════════════════════════════════════════════════
def astar_manhattan(coordenadas, origen, destino,
                    casetas=None, zonas_trafico=None,
                    precio_gasolina=20.0, rendimiento_kmL=12.0):
    """
    A* usando heurística Manhattan y costos reales de OSRM.

    coordenadas : dict  {nombre: (lat, lng)}
    origen      : str   nombre del nodo inicial
    destino     : str   nombre del nodo final
    casetas     : list  [{'lat','lng','costo'}, ...]
    zonas_trafico: list [{'lat','lng','radio_km','nivel','hora_inicio','hora_fin'}, ...]

    Retorna (ruta, distancia_km_total, tiempo_min_total, polilinea)
    """
    casetas       = casetas or []
    zonas_trafico = zonas_trafico or []

    lat_d, lon_d = coordenadas[destino]

    # (f, g, nombre_nodo, camino)
    heap = []
    heapq.heappush(heap, (0.0, 0.0, origen, [origen]))

    visitados    = {}   # nombre → mejor g conocido
    dist_total   = 0.0
    tiempo_total = 0.0

    while heap:
        f, g, nodo_actual, camino = heapq.heappop(heap)

        if nodo_actual in visitados and visitados[nodo_actual] <= g:
            continue
        visitados[nodo_actual] = g

        if nodo_actual == destino:
            dist_total = g
            break

        lat_a, lon_a = coordenadas[nodo_actual]

        # Expandir hacia todos los vecinos conocidos
        for vecino, (lat_b, lon_b) in coordenadas.items():
            if vecino == nodo_actual:
                continue

            costo_seg, dist_seg, dur_seg = _costo_segmento(
                nodo_actual, vecino, coordenadas,
                casetas, zonas_trafico,
                precio_gasolina, rendimiento_kmL
            )

            nuevo_g = g + costo_seg
            h       = heuristica_manhattan(lat_b, lon_b, lat_d, lon_d)
            nuevo_f = nuevo_g + h

            if vecino not in visitados or visitados.get(vecino, float('inf')) > nuevo_g:
                heapq.heappush(heap, (nuevo_f, nuevo_g, vecino, camino + [vecino]))

    # Obtener la geometría completa de la ruta ganadora
    polilinea = []
    for i in range(len(camino) - 1):
        lat1, lon1 = coordenadas[camino[i]]
        lat2, lon2 = coordenadas[camino[i + 1]]
        _, dur, poly_seg = osrm_geometria(lat1, lon1, lat2, lon2)
        polilinea.extend(poly_seg)
        if dur:
            tiempo_total += dur

    return camino, round(dist_total, 2), round(tiempo_total, 1), polilinea


# ══════════════════════════════════════════════════════════════════════════════
# ALGORITMO 2 — COSTO UNIFORME (UCS / DIJKSTRA)
# ══════════════════════════════════════════════════════════════════════════════
def costo_uniforme(coordenadas, origen, destino,
                   casetas=None, zonas_trafico=None,
                   precio_gasolina=20.0, rendimiento_kmL=12.0):
    """
    UCS: expande siempre el nodo de menor costo acumulado g(n).
    No usa heurística — garantiza el camino de menor costo real.

    Retorna (ruta, distancia_km_total, tiempo_min_total, polilinea)
    """
    casetas       = casetas or []
    zonas_trafico = zonas_trafico or []

    heap = []
    heapq.heappush(heap, (0.0, origen, [origen]))

    visitados    = {}
    tiempo_total = 0.0
    camino       = [origen]

    while heap:
        g, nodo_actual, camino = heapq.heappop(heap)

        if nodo_actual in visitados:
            continue
        visitados[nodo_actual] = g

        if nodo_actual == destino:
            break

        for vecino in coordenadas:
            if vecino == nodo_actual or vecino in visitados:
                continue

            costo_seg, _, _ = _costo_segmento(
                nodo_actual, vecino, coordenadas,
                casetas, zonas_trafico,
                precio_gasolina, rendimiento_kmL
            )
            heapq.heappush(heap, (g + costo_seg, vecino, camino + [vecino]))

    # Geometría
    polilinea = []
    for i in range(len(camino) - 1):
        lat1, lon1 = coordenadas[camino[i]]
        lat2, lon2 = coordenadas[camino[i + 1]]
        _, dur, poly_seg = osrm_geometria(lat1, lon1, lat2, lon2)
        polilinea.extend(poly_seg)
        if dur:
            tiempo_total += dur

    dist_total = visitados.get(destino, 0.0)
    return camino, round(dist_total, 2), round(tiempo_total, 1), polilinea


# ══════════════════════════════════════════════════════════════════════════════
# ALGORITMO 3 — GENÉTICO EVOLUTIVO (TSP multi-destino)
# ══════════════════════════════════════════════════════════════════════════════
def _distancia_ruta(ruta, coordenadas, casetas=None, zonas_trafico=None):
    """Evalúa el costo total de una ruta completa."""
    casetas       = casetas or []
    zonas_trafico = zonas_trafico or []
    total = 0.0
    for i in range(len(ruta) - 1):
        costo, _, _ = _costo_segmento(
            ruta[i], ruta[i + 1], coordenadas,
            casetas, zonas_trafico
        )
        total += costo
    return total


def _seleccion_ruleta(poblacion, aptitudes):
    """Selecciona un individuo por ruleta proporcional a su aptitud."""
    total = sum(aptitudes)
    if total == 0:
        return random.choice(poblacion)
    r = random.uniform(0, total)
    acum = 0.0
    for ind, apt in zip(poblacion, aptitudes):
        acum += apt
        if acum >= r:
            return ind
    return poblacion[-1]


def _cruce_orden(padre1, padre2):
    """
    Cruce OX (Order Crossover) — preserva el orden relativo
    de las ciudades respetando las restricciones del TSP.
    """
    n     = len(padre1)
    hijo  = [None] * n
    i, j  = sorted(random.sample(range(n), 2))

    # Copia segmento del padre1
    hijo[i:j+1] = padre1[i:j+1]

    # Rellena con el orden del padre2
    pos   = (j + 1) % n
    for gen in padre2[j+1:] + padre2[:j+1]:
        if gen not in hijo:
            hijo[pos] = gen
            pos = (pos + 1) % n

    return hijo


def _mutacion_intercambio(ruta, prob=0.1):
    """Intercambia dos ciudades aleatorias con probabilidad prob."""
    ruta = ruta[:]
    if random.random() < prob:
        i, j = random.sample(range(len(ruta)), 2)
        ruta[i], ruta[j] = ruta[j], ruta[i]
    return ruta


def algoritmo_genetico(coordenadas, origen=None,
                       casetas=None, zonas_trafico=None,
                       max_iter=200, tam_poblacion=60,
                       prob_mutacion=0.08):
    """
    Algoritmo genético evolutivo para el problema de múltiples destinos (TSP).

    Retorna (mejor_ruta, distancia_km, tiempo_min, polilinea)
    """
    casetas       = casetas or []
    zonas_trafico = zonas_trafico or []
    ciudades      = list(coordenadas.keys())

    if len(ciudades) < 2:
        return ciudades, 0.0, 0.0, []

    # Fijar origen si se especifica
    ciudades_libres = [c for c in ciudades if c != origen] if origen else ciudades[:]

    # ── Población inicial aleatoria ──────────────────────────────
    poblacion = []
    for _ in range(tam_poblacion):
        ind = ciudades_libres[:]
        random.shuffle(ind)
        if origen:
            ind = [origen] + ind
        poblacion.append(ind)

    mejor_ruta  = poblacion[0]
    mejor_costo = _distancia_ruta(mejor_ruta, coordenadas, casetas, zonas_trafico)

    # ── Ciclo evolutivo ──────────────────────────────────────────
    for _ in range(max_iter):
        costos   = [_distancia_ruta(ind, coordenadas, casetas, zonas_trafico)
                    for ind in poblacion]

        # Aptitud inversa: menor costo = mayor aptitud
        max_c    = max(costos) + 1e-9
        aptitudes = [max_c - c for c in costos]

        # Actualizar mejor global
        for ind, c in zip(poblacion, costos):
            if c < mejor_costo:
                mejor_costo = c
                mejor_ruta  = ind[:]

        # Generar nueva generación
        nueva_gen = [mejor_ruta[:]]   # elitismo: conservar el mejor

        while len(nueva_gen) < tam_poblacion:
            p1 = _seleccion_ruleta(poblacion, aptitudes)
            p2 = _seleccion_ruleta(poblacion, aptitudes)

            # Cruce solo sobre la parte libre (no el origen fijo)
            if origen:
                hijo = [origen] + _cruce_orden(p1[1:], p2[1:])
            else:
                hijo = _cruce_orden(p1, p2)

            hijo = _mutacion_intercambio(hijo, prob_mutacion)
            nueva_gen.append(hijo)

        poblacion = nueva_gen

    # ── Geometría de la mejor ruta ───────────────────────────────
    polilinea    = []
    tiempo_total = 0.0
    for i in range(len(mejor_ruta) - 1):
        lat1, lon1 = coordenadas[mejor_ruta[i]]
        lat2, lon2 = coordenadas[mejor_ruta[i + 1]]
        _, dur, poly_seg = osrm_geometria(lat1, lon1, lat2, lon2)
        polilinea.extend(poly_seg)
        if dur:
            tiempo_total += dur

    return mejor_ruta, round(mejor_costo, 2), round(tiempo_total, 1), polilinea


# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES GENERALES
# ══════════════════════════════════════════════════════════════════════════════
def detectar_ruta_critica(pos_actual, puntos_ruta, umbral_km=0.3):
    """
    Devuelve True si la posición actual se desvió más de `umbral_km`
    de todos los puntos de la ruta planeada.
    """
    lat, lon = pos_actual
    for p in puntos_ruta:
        d = _distancia_euclidiana(lat, lon, p['latitud'], p['longitud'])
        if d <= umbral_km:
            return False
    return True


def calcular_combustible(distancia_km, rendimiento_kmL, precio_litro=20.0):
    """Estima litros necesarios y costo en MXN para recorrer distancia_km."""
    litros = distancia_km / rendimiento_kmL if rendimiento_kmL > 0 else 0
    costo  = litros * precio_litro
    return round(litros, 2), round(costo, 2)


def rutas_alternas(coordenadas, origen, destino,
                   casetas=None, zonas_trafico=None, n_alternas=2):
    """
    Genera n_alternas rutas adicionales usando A* con penalizaciones
    crecientes sobre los segmentos de la ruta principal,
    para forzar caminos diferentes.
    """
    alternas = []
    zonas_extra = list(zonas_trafico or [])

    ruta_principal, _, _, _ = astar_manhattan(
        coordenadas, origen, destino, casetas, zonas_extra
    )

    for k in range(n_alternas):
        # Penalizar el segmento central de la ruta anterior
        if len(ruta_principal) >= 2:
            mid   = len(ruta_principal) // 2
            lat_m, lon_m = coordenadas[ruta_principal[mid]]
            zonas_extra.append({
                'lat': lat_m, 'lng': lon_m,
                'radio_km': 1.0,
                'nivel': 'critico',
                'hora_inicio': None, 'hora_fin': None
            })

        ruta_alt, dist_alt, tiempo_alt, poly_alt = astar_manhattan(
            coordenadas, origen, destino, casetas, zonas_extra
        )

        if ruta_alt != ruta_principal:
            alternas.append({
                'ruta': ruta_alt,
                'distancia_km': dist_alt,
                'tiempo_min': tiempo_alt,
                'polilinea': poly_alt
            })
            ruta_principal = ruta_alt

    return alternas