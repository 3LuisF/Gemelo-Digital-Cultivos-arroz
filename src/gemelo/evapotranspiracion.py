"""
Calculo de la evapotranspiracion de referencia (ET0) usando el metodo
Penman-Monteith FAO-56, version simplificada para datos diarios.

Referencia: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998).
"Crop evapotranspiration - Guidelines for computing crop water
requirements". FAO Irrigation and drainage paper 56.

Si no se cuenta con datos medidos de viento o radiacion solar, se usan
valores por defecto/estimados, tal como recomienda la FAO para zonas
donde no hay estacion meteorologica completa.
"""

import math


# Constante de Stefan-Boltzmann (MJ K^-4 m^-2 dia^-1)
CONSTANTE_STEFAN_BOLTZMANN = 4.903e-9

# Albedo tipico para un cultivo de referencia (pasto)
ALBEDO_CULTIVO_REFERENCIA = 0.23

# Velocidad del viento por defecto si no se tiene medicion (m/s a 2m de altura)
VIENTO_POR_DEFECTO = 2.0


def calcular_dia_juliano(fecha):
    """
    Calcula el dia juliano (numero de dia del año, de 1 a 365/366) a
    partir de una fecha.

    Parametros:
        fecha (datetime): fecha para la cual se quiere el dia juliano.

    Retorna:
        int: dia del año (1-366).
    """
    return fecha.timetuple().tm_yday


def calcular_presion_saturacion_vapor(temperatura):
    """
    Calcula la presion de saturacion de vapor (es) para una temperatura
    dada, usando la formula de la FAO-56 (ecuacion 11).

    Parametros:
        temperatura (float): temperatura del aire en grados Celsius.

    Retorna:
        float: presion de saturacion de vapor en kPa.
    """
    return 0.6108 * math.exp((17.27 * temperatura) / (temperatura + 237.3))


def calcular_pendiente_curva_presion_vapor(temperatura_media):
    """
    Calcula la pendiente de la curva de presion de saturacion de vapor
    (delta), ecuacion 13 de la FAO-56.

    Parametros:
        temperatura_media (float): temperatura media diaria en °C.

    Retorna:
        float: pendiente delta en kPa/°C.
    """
    es = calcular_presion_saturacion_vapor(temperatura_media)
    return (4098 * es) / ((temperatura_media + 237.3) ** 2)


def calcular_constante_psicrometrica(elevacion_m=0.0):
    """
    Calcula la constante psicrometrica (gamma) a partir de la
    elevacion sobre el nivel del mar, ecuaciones 7 y 8 de la FAO-56.

    Parametros:
        elevacion_m (float): elevacion del sitio en metros sobre el
            nivel del mar (por defecto 0, nivel del mar).

    Retorna:
        float: constante psicrometrica en kPa/°C.
    """
    presion_atmosferica = 101.3 * ((293 - 0.0065 * elevacion_m) / 293) ** 5.26
    return 0.665e-3 * presion_atmosferica


def calcular_radiacion_extraterrestre(latitud_grados, dia_juliano):
    """
    Calcula la radiacion extraterrestre (Ra), que es la radiacion solar
    que llegaria a la atmosfera sin nubes, segun la latitud y la epoca
    del año (ecuacion 21 de la FAO-56).

    Parametros:
        latitud_grados (float): latitud del sitio en grados decimales
            (positivo = hemisferio norte, negativo = hemisferio sur).
        dia_juliano (int): dia del año (1-366).

    Retorna:
        float: radiacion extraterrestre Ra en MJ/m2/dia.
    """
    latitud_rad = math.radians(latitud_grados)

    # Distancia relativa inversa Tierra-Sol
    dr = 1 + 0.033 * math.cos((2 * math.pi / 365) * dia_juliano)

    # Declinacion solar
    declinacion = 0.409 * math.sin((2 * math.pi / 365) * dia_juliano - 1.39)

    # Angulo horario de salida del sol
    argumento = -math.tan(latitud_rad) * math.tan(declinacion)
    # Limitamos el argumento entre -1 y 1 para evitar errores en latitudes extremas
    argumento = max(-1.0, min(1.0, argumento))
    angulo_horario = math.acos(argumento)

    # Constante solar (MJ m^-2 min^-1)
    constante_solar = 0.0820

    ra = ((24 * 60) / math.pi) * constante_solar * dr * (
        angulo_horario * math.sin(latitud_rad) * math.sin(declinacion)
        + math.cos(latitud_rad) * math.cos(declinacion) * math.sin(angulo_horario)
    )

    return ra


def estimar_radiacion_solar(temp_max, temp_min, radiacion_extraterrestre, factor_ajuste=0.16):
    """
    Estima la radiacion solar (Rs) a partir de la diferencia entre la
    temperatura maxima y minima diaria, usando la formula de Hargreaves
    (ecuacion 50 de la FAO-56). Se usa cuando no hay un piranometro
    para medir la radiacion directamente.

    Parametros:
        temp_max (float): temperatura maxima diaria en °C.
        temp_min (float): temperatura minima diaria en °C.
        radiacion_extraterrestre (float): Ra en MJ/m2/dia.
        factor_ajuste (float): coeficiente de Hargreaves. La FAO
            recomienda 0.16 para zonas de interior (continentales) y
            0.19 para zonas costeras. Por defecto se usa 0.16.

    Retorna:
        float: radiacion solar Rs en MJ/m2/dia.
    """
    diferencia_temperaturas = max(0.0, temp_max - temp_min)
    return factor_ajuste * math.sqrt(diferencia_temperaturas) * radiacion_extraterrestre


def calcular_et0_penman_monteith(temp_max, temp_min, humedad_rel_media, fecha,
                                   latitud, viento=None, radiacion_solar=None,
                                   elevacion_m=0.0):
    """
    Calcula la evapotranspiracion de referencia ET0 (mm/dia) usando el
    metodo Penman-Monteith FAO-56 (ecuacion 6).

    Parametros:
        temp_max (float): temperatura maxima diaria en °C.
        temp_min (float): temperatura minima diaria en °C.
        humedad_rel_media (float): humedad relativa media diaria en %.
        fecha (datetime): fecha del calculo (se usa para la radiacion).
        latitud (float): latitud del sitio en grados decimales.
        viento (float|None): velocidad del viento a 2m de altura en m/s.
            Si es None, se usa el valor por defecto de 2 m/s.
        radiacion_solar (float|None): radiacion solar medida en
            MJ/m2/dia. Si es None, se estima a partir de temp_max y
            temp_min (formula de Hargreaves).
        elevacion_m (float): elevacion del sitio sobre el nivel del
            mar, en metros (por defecto 0).

    Retorna:
        float: ET0 en mm/dia, redondeado a 2 decimales. Nunca retorna
        un valor negativo (se limita a 0 como minimo).
    """
    if viento is None:
        viento = VIENTO_POR_DEFECTO

    temperatura_media = (temp_max + temp_min) / 2.0

    # --- Presiones de vapor ---
    es_max = calcular_presion_saturacion_vapor(temp_max)
    es_min = calcular_presion_saturacion_vapor(temp_min)
    es = (es_max + es_min) / 2.0

    # Presion de vapor real, a partir de la humedad relativa media
    ea = es * (humedad_rel_media / 100.0)

    # --- Pendiente de la curva de presion de vapor y constante psicrometrica ---
    delta = calcular_pendiente_curva_presion_vapor(temperatura_media)
    gamma = calcular_constante_psicrometrica(elevacion_m)

    # --- Radiacion ---
    dia_juliano = calcular_dia_juliano(fecha)
    ra = calcular_radiacion_extraterrestre(latitud, dia_juliano)

    if radiacion_solar is None:
        rs = estimar_radiacion_solar(temp_max, temp_min, ra)
    else:
        rs = radiacion_solar

    # Radiacion solar en condiciones de cielo despejado
    rso = (0.75 + 2e-5 * elevacion_m) * ra

    # Radiacion neta de onda corta (albedo = 0.23 para cultivo de referencia)
    rns = (1 - ALBEDO_CULTIVO_REFERENCIA) * rs

    # Radiacion neta de onda larga (ecuacion 39 de la FAO-56)
    temp_max_kelvin = temp_max + 273.16
    temp_min_kelvin = temp_min + 273.16

    # Evitamos division por cero si rso es 0
    relacion_rs_rso = rs / rso if rso > 0 else 0
    relacion_rs_rso = max(0.0, min(1.0, relacion_rs_rso))

    rnl = (
        CONSTANTE_STEFAN_BOLTZMANN
        * ((temp_max_kelvin ** 4 + temp_min_kelvin ** 4) / 2)
        * (0.34 - 0.14 * math.sqrt(max(0.0, ea)))
        * (1.35 * relacion_rs_rso - 0.35)
    )

    # Radiacion neta total
    rn = rns - rnl

    # Flujo de calor del suelo: se asume 0 para calculos diarios (FAO-56)
    g = 0.0

    # --- Ecuacion de Penman-Monteith FAO-56 ---
    numerador = (0.408 * delta * (rn - g)) + (
        gamma * (900 / (temperatura_media + 273)) * viento * (es - ea)
    )
    denominador = delta + gamma * (1 + 0.34 * viento)

    et0 = numerador / denominador

    # La ET0 no puede ser negativa
    et0 = max(0.0, et0)

    return round(et0, 2)
