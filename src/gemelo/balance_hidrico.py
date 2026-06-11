"""
Modelo de balance hidrico del suelo, basado en el metodo de
Thornthwaite-Mather (modelo de "balde" o "tanque" de agua del suelo).

Idea general del modelo:
    Agua_suelo(t+1) = Agua_suelo(t) + Lluvia + Riego - ETc - Drenaje

Donde:
    - ETc = ET0 * Kc  (evapotranspiracion del cultivo)
    - Drenaje: el agua que sobra cuando el suelo ya esta a capacidad
      de campo se pierde por drenaje profundo (no se acumula).

El "tanque" tiene un limite superior (capacidad de campo) y un limite
inferior (punto de marchitez). El agua "util" para la planta es la que
esta entre esos dos limites.
"""

from src.utilidades.logger import obtener_logger

logger = obtener_logger("gemelo")


def calcular_agua_total_util_mm(profundidad_raiz_m, capacidad_campo, punto_marchitez):
    """
    Calcula la cantidad maxima de agua "util" que puede almacenar el
    suelo dentro de la zona de raices, en milimetros.

    Parametros:
        profundidad_raiz_m (float): profundidad efectiva de raiz, en metros.
        capacidad_campo (float): capacidad de campo del suelo, como
            fraccion de volumen (ej: 0.32 = 32%).
        punto_marchitez (float): punto de marchitez del suelo, como
            fraccion de volumen (ej: 0.18 = 18%).

    Retorna:
        float: agua total util en milimetros.
    """
    # 1 m de profundidad con 1% de humedad equivale a 10 mm de agua
    return (capacidad_campo - punto_marchitez) * profundidad_raiz_m * 1000


def calcular_agua_actual_desde_humedad(humedad_suelo_porcentaje, profundidad_raiz_m, punto_marchitez):
    """
    Convierte una lectura de humedad del suelo (en %, medida por el
    sensor) a milimetros de agua disponible por encima del punto de
    marchitez.

    Parametros:
        humedad_suelo_porcentaje (float): humedad volumetrica del
            suelo, en porcentaje (0-100).
        profundidad_raiz_m (float): profundidad efectiva de raiz, en metros.
        punto_marchitez (float): punto de marchitez del suelo, como
            fraccion de volumen (ej: 0.18 = 18%).

    Retorna:
        float: agua disponible en milimetros (nunca negativo).
    """
    humedad_fraccion = humedad_suelo_porcentaje / 100.0
    agua_mm = (humedad_fraccion - punto_marchitez) * profundidad_raiz_m * 1000

    return max(0.0, agua_mm)


def actualizar_balance_diario(agua_actual_mm, lluvia_mm, riego_mm, etc_mm, agua_total_util_mm):
    """
    Aplica un paso del modelo Thornthwaite-Mather: a partir del agua
    que habia en el suelo, suma la lluvia y el riego, resta la
    evapotranspiracion del cultivo, y si el resultado supera la
    capacidad maxima del suelo, el excedente se pierde como drenaje.

    Parametros:
        agua_actual_mm (float): agua disponible en el suelo al inicio
            del dia, en mm.
        lluvia_mm (float): lluvia del dia, en mm.
        riego_mm (float): riego aplicado en el dia, en mm.
        etc_mm (float): evapotranspiracion del cultivo (ET0 * Kc) del
            dia, en mm.
        agua_total_util_mm (float): capacidad maxima de agua util del
            suelo, en mm (limite superior del "tanque").

    Retorna:
        tuple (agua_nueva_mm, drenaje_mm):
            agua_nueva_mm (float): agua disponible al final del dia,
                entre 0 y agua_total_util_mm.
            drenaje_mm (float): agua perdida por drenaje (0 si no hubo
                exceso).
    """
    agua_sin_limites = agua_actual_mm + lluvia_mm + riego_mm - etc_mm

    if agua_sin_limites > agua_total_util_mm:
        drenaje_mm = agua_sin_limites - agua_total_util_mm
        agua_nueva_mm = agua_total_util_mm
    else:
        drenaje_mm = 0.0
        agua_nueva_mm = max(0.0, agua_sin_limites)

    return agua_nueva_mm, drenaje_mm


def calcular_estado_hidrico(lecturas, parametros_cultivo, parametros_suelo):
    """
    Calcula el estado hidrico actual del cultivo a partir de la lectura
    de humedad del suelo, la evapotranspiracion del dia y los
    parametros del cultivo y del suelo.

    Parametros:
        lecturas (dict): debe tener las llaves:
            - "humedad_suelo": humedad del suelo en % (0-100), del sensor.
            - "et0": evapotranspiracion de referencia del dia, en mm/dia.
        parametros_cultivo (dict): debe tener las llaves:
            - "kc": coeficiente de cultivo actual.
            - "profundidad_raiz_m": profundidad efectiva de raiz, en metros.
        parametros_suelo (dict): debe tener las llaves:
            - "capacidad_campo": fraccion (ej: 0.32).
            - "punto_marchitez": fraccion (ej: 0.18).

    Retorna:
        dict con las llaves:
            - "agua_disponible_mm": agua util actual en el suelo, en mm.
            - "agua_total_util_mm": capacidad maxima de agua util, en mm.
            - "porcentaje_agua_util": porcentaje de agua util respecto
              al total (0-100).
            - "deficit_mm": cuanta agua falta para llegar a capacidad
              de campo, en mm.
            - "evapotranspiracion_mm": ETc del dia (ET0 * Kc), en mm.
            - "esta_en_estres": True si el agua disponible es menor al
              50% del agua util total.
    """
    profundidad_raiz_m = parametros_cultivo["profundidad_raiz_m"]
    kc = parametros_cultivo["kc"]

    capacidad_campo = parametros_suelo["capacidad_campo"]
    punto_marchitez = parametros_suelo["punto_marchitez"]

    et0 = lecturas["et0"]
    humedad_suelo = lecturas["humedad_suelo"]

    agua_total_util_mm = calcular_agua_total_util_mm(profundidad_raiz_m, capacidad_campo, punto_marchitez)
    agua_disponible_mm = calcular_agua_actual_desde_humedad(humedad_suelo, profundidad_raiz_m, punto_marchitez)

    # No dejamos que el agua disponible supere el total util (por si la
    # lectura del sensor esta por encima de capacidad de campo)
    agua_disponible_mm = min(agua_disponible_mm, agua_total_util_mm)

    etc_mm = et0 * kc

    if agua_total_util_mm > 0:
        porcentaje_agua_util = (agua_disponible_mm / agua_total_util_mm) * 100
    else:
        porcentaje_agua_util = 0.0

    deficit_mm = agua_total_util_mm - agua_disponible_mm

    esta_en_estres = agua_disponible_mm < (0.5 * agua_total_util_mm)

    return {
        "agua_disponible_mm": round(agua_disponible_mm, 2),
        "agua_total_util_mm": round(agua_total_util_mm, 2),
        "porcentaje_agua_util": round(porcentaje_agua_util, 2),
        "deficit_mm": round(deficit_mm, 2),
        "evapotranspiracion_mm": round(etc_mm, 2),
        "esta_en_estres": esta_en_estres,
    }
