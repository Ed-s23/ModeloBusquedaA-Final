import math
import heapq
import random
from operator import itemgetter


# ─────────────────────────────────────────
# UTILIDAD — Distancia geodésica (del libro Zamora p.75)
# ─────────────────────────────────────────

def geodist(lat1, lon1, lat2, lon2):
    """
    Distancia en km entre dos coordenadas GPS.
    Usada como heurística h(n) en A* y para calcular ahorros en Clarke & Wright.
    """
    grad_rad = 0.01745329
    rad_grad = 57.29577951
    longitud = lon1 - lon2
    val = (math.sin(lat1 * grad_rad) * math.sin(lat2 * grad_rad)) + \
          (math.cos(lat1 * grad_rad) * math.cos(lat2 * grad_rad) *
           math.cos(longitud * grad_rad))
    return (math.acos(max(-1, min(1, val))) * rad_grad) * 111.32


def construir_grafo(coordenadas):
    """
    Construye un grafo completo conectando todos los puntos entre sí.
    Cada arista tiene como peso la distancia geodésica.
    """
    grafo = {}
    nodos = list(coordenadas.keys())
    for n1 in nodos:
        grafo[n1] = {}
        for n2 in nodos:
            if n1 != n2:
                lat1, lon1 = coordenadas[n1]
                lat2, lon2 = coordenadas[n2]
                grafo[n1][n2] = geodist(lat1, lon1, lat2, lon2)
    return grafo


# ─────────────────────────────────────────
# ALGORITMO A* (Zamora p.73)
# f(n) = g(n) + h(n)
# ─────────────────────────────────────────

def astar(coordenadas, origen, destino):
    """
    Ruta óptima de un punto A a un punto B.
    Ideal para UN solo destino.
    Retorna: (lista_ruta, costo_km)
    """
    grafo = construir_grafo(coordenadas)

    # Cola de prioridad: (f_n, g_n, nodo_actual, camino)
    frontera = [(0, 0, origen, [origen])]
    visitados = {}

    while frontera:
        f_n, g_n, nodo_actual, camino = heapq.heappop(frontera)

        if nodo_actual in visitados:
            continue
        visitados[nodo_actual] = g_n

        if nodo_actual == destino:
            return camino, round(g_n, 2)

        for vecino, distancia in grafo.get(nodo_actual, {}).items():
            if vecino not in visitados:
                nuevo_g = g_n + distancia
                # h(n) = distancia geodésica al destino
                lat1, lon1 = coordenadas[vecino]
                lat2, lon2 = coordenadas[destino]
                h_n    = geodist(lat1, lon1, lat2, lon2)
                nuevo_f = nuevo_g + h_n
                heapq.heappush(
                    frontera,
                    (nuevo_f, nuevo_g, vecino, camino + [vecino])
                )

    return None, None  # Sin solución


# ─────────────────────────────────────────
# CLARKE & WRIGHT (Zamora p.94)
# s(i,j) = d(A,i) + d(A,j) - d(i,j)
# ─────────────────────────────────────────

def clarke_wright(coordenadas, origen_key):
    """
    Optimiza rutas con múltiples destinos minimizando distancia total.
    Ideal para 2 a 15 destinos.
    Retorna: lista de rutas [ [punto1, punto2, ...], ... ]
    """
    almacen  = coordenadas[origen_key]
    clientes = {k: v for k, v in coordenadas.items() if k != origen_key}

    if not clientes:
        return []

    # Paso 1 — calcular ahorros
    ahorros = {}
    for c1 in clientes:
        for c2 in clientes:
            if c1 != c2 and (c2, c1) not in ahorros:
                d_c1_a   = geodist(*clientes[c1], *almacen)
                d_c2_a   = geodist(*clientes[c2], *almacen)
                d_c1_c2  = geodist(*clientes[c1], *clientes[c2])
                ahorros[(c1, c2)] = d_c1_a + d_c2_a - d_c1_c2

    # Paso 2 — ordenar de mayor a menor
    ahorros_ord = sorted(ahorros.items(), key=itemgetter(1), reverse=True)

    # Paso 3 — construir rutas
    rutas = []

    def en_ruta(ciudad):
        for r in rutas:
            if ciudad in r:
                return r
        return None

    for (c1, c2), _ in ahorros_ord:
        rc1 = en_ruta(c1)
        rc2 = en_ruta(c2)

        if rc1 is None and rc2 is None:
            rutas.append([c1, c2])
        elif rc1 is not None and rc2 is None:
            if rc1[0] == c1:
                rutas[rutas.index(rc1)].insert(0, c2)
            elif rc1[-1] == c1:
                rutas[rutas.index(rc1)].append(c2)
        elif rc1 is None and rc2 is not None:
            if rc2[0] == c2:
                rutas[rutas.index(rc2)].insert(0, c1)
            elif rc2[-1] == c2:
                rutas[rutas.index(rc2)].append(c1)
        elif rc1 is not None and rc2 is not None and rc1 != rc2:
            if rc1[-1] == c1 and rc2[0] == c2:
                rutas[rutas.index(rc1)].extend(rc2)
                rutas.remove(rc2)
            elif rc1[0] == c1 and rc2[-1] == c2:
                rutas[rutas.index(rc2)].extend(rc1)
                rutas.remove(rc1)

    # Paso 4 — clientes sin asignar
    for cliente in clientes:
        if en_ruta(cliente) is None:
            rutas.append([cliente])

    return rutas


# ─────────────────────────────────────────
# ALGORITMO GENÉTICO (Zamora p.126)
# ─────────────────────────────────────────

def distancia_ruta(ruta, coordenadas):
    """Función fitness — distancia total de la ruta (menor = mejor)"""
    total = 0
    for i in range(len(ruta) - 1):
        total += geodist(*coordenadas[ruta[i]], *coordenadas[ruta[i+1]])
    # Regresar al origen
    total += geodist(*coordenadas[ruta[-1]], *coordenadas[ruta[0]])
    return total


def seleccion_ruleta(poblacion, coordenadas):
    """Selección proporcional al fitness (Zamora p.129)"""
    puntuaciones = [1 / distancia_ruta(ind, coordenadas) for ind in poblacion]
    total        = sum(puntuaciones)
    probabilidades = [p / total for p in puntuaciones]
    r = random.random()
    acumulado = 0
    for individuo, prob in zip(poblacion, probabilidades):
        acumulado += prob
        if r <= acumulado:
            return individuo
    return poblacion[-1]


def cruce_ox(padre1, padre2):
    """Cruce de orden OX — conserva el orden relativo de los genes"""
    n      = len(padre1)
    inicio = random.randint(0, n - 2)
    fin    = random.randint(inicio + 1, n - 1)
    hijo   = [None] * n
    hijo[inicio:fin] = padre1[inicio:fin]
    restantes = [g for g in padre2 if g not in hijo]
    j = 0
    for i in range(n):
        if hijo[i] is None:
            hijo[i] = restantes[j]
            j += 1
    return hijo


def mutacion(individuo, prob=0.1):
    """Intercambia dos puntos al azar con probabilidad prob"""
    if random.random() < prob:
        i, j = random.sample(range(len(individuo)), 2)
        individuo[i], individuo[j] = individuo[j], individuo[i]
    return individuo


def algoritmo_genetico(coordenadas, tam_poblacion=40, generaciones=150, prob_mutacion=0.1):
    """
    Optimización de rutas con múltiples destinos (15+ puntos).
    Retorna: (mejor_ruta, costo_km)
    """
    puntos    = list(coordenadas.keys())
    poblacion = [random.sample(puntos, len(puntos)) for _ in range(tam_poblacion)]

    mejor_ruta = min(poblacion, key=lambda r: distancia_ruta(r, coordenadas))
    mejor_dist = distancia_ruta(mejor_ruta, coordenadas)

    for gen in range(generaciones):
        nueva_pob = []
        for _ in range(tam_poblacion // 2):
            p1   = seleccion_ruleta(poblacion, coordenadas)
            p2   = seleccion_ruleta(poblacion, coordenadas)
            h1   = mutacion(cruce_ox(p1, p2), prob_mutacion)
            h2   = mutacion(cruce_ox(p2, p1), prob_mutacion)
            nueva_pob.extend([h1, h2])

        # Mantener los mejores
        poblacion = sorted(
            poblacion + nueva_pob,
            key=lambda r: distancia_ruta(r, coordenadas)
        )[:tam_poblacion]

        candidato = poblacion[0]
        dist_cand = distancia_ruta(candidato, coordenadas)
        if dist_cand < mejor_dist:
            mejor_ruta = candidato
            mejor_dist = dist_cand

        # Criterio de convergencia γ = 95% (Zamora p.127)
        distancias = [distancia_ruta(r, coordenadas) for r in poblacion]
        media      = sum(distancias) / len(distancias)
        similares  = sum(1 for d in distancias if abs(d - media) / media < 0.05)
        if similares / tam_poblacion >= 0.95:
            break

    return mejor_ruta, round(mejor_dist, 2)


# ─────────────────────────────────────────
# DETECCIÓN DE RUTA CRÍTICA
# ─────────────────────────────────────────

def detectar_ruta_critica(coord_real, puntos_ruta, umbral_km=0.5):
    """
    Verifica si una coordenada GPS se desvió de la ruta planeada.
    Retorna True si el desvío supera el umbral.
    """
    lat_r, lon_r = coord_real
    distancia_min = min(
        geodist(lat_r, lon_r, p['latitud'], p['longitud'])
        for p in puntos_ruta
    )
    return distancia_min > umbral_km