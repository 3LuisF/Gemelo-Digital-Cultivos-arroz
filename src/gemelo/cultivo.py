"""
Manejo de los parametros de los cultivos (arroz secano y maiz):
etapas fenologicas, coeficientes de cultivo (Kc) y profundidad de raiz.

Los valores numericos estan definidos en "config/cultivos.yaml" para
que se puedan ajustar sin tocar el codigo.
"""

import os
import yaml

from src.utilidades.logger import obtener_logger

logger = obtener_logger("gemelo")

# Carpeta raiz del proyecto (un nivel arriba de src/)
CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_CULTIVOS_YAML = os.path.join(CARPETA_RAIZ, "config", "cultivos.yaml")


def cargar_parametros_cultivos():
    """
    Lee el archivo "config/cultivos.yaml" y lo retorna como diccionario.

    Retorna:
        dict: diccionario con las claves "arroz_secano" y "maiz", cada
        una con su informacion de etapas, Kc, ciclo y profundidad de
        raiz.
    """
    with open(RUTA_CULTIVOS_YAML, "r", encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def obtener_etapa_actual(tipo_cultivo, dias_desde_siembra):
    """
    Determina en que etapa fenologica se encuentra el cultivo segun los
    dias transcurridos desde la siembra.

    Parametros:
        tipo_cultivo (str): "arroz_secano" o "maiz".
        dias_desde_siembra (int): cantidad de dias desde que se sembro.

    Retorna:
        dict con las llaves "nombre" y "kc" de la etapa actual. Si los
        dias superan el ciclo completo del cultivo, se devuelve la
        ultima etapa definida (etapa "final").
    """
    parametros = cargar_parametros_cultivos()
    cultivo = parametros[tipo_cultivo]

    etapas = cultivo["etapas"]

    for etapa in etapas:
        if etapa["dia_inicio"] <= dias_desde_siembra <= etapa["dia_fin"]:
            return {"nombre": etapa["nombre"], "kc": etapa["kc"]}

    # Si nos pasamos del ciclo completo, devolvemos la ultima etapa (final)
    ultima_etapa = etapas[-1]
    return {"nombre": ultima_etapa["nombre"], "kc": ultima_etapa["kc"]}


def obtener_kc_actual(tipo_cultivo, dias_desde_siembra):
    """
    Devuelve el coeficiente de cultivo (Kc) que corresponde a la etapa
    fenologica actual.

    Parametros:
        tipo_cultivo (str): "arroz_secano" o "maiz".
        dias_desde_siembra (int): cantidad de dias desde que se sembro.

    Retorna:
        float: valor de Kc de la etapa actual.
    """
    etapa = obtener_etapa_actual(tipo_cultivo, dias_desde_siembra)
    return etapa["kc"]


def obtener_profundidad_raiz(tipo_cultivo):
    """
    Devuelve la profundidad efectiva de raiz del cultivo, en metros.
    Este dato se usa en el balance hidrico para saber cuanta agua del
    suelo puede aprovechar la planta.

    Parametros:
        tipo_cultivo (str): "arroz_secano" o "maiz".

    Retorna:
        float: profundidad de raiz en metros.
    """
    parametros = cargar_parametros_cultivos()
    return parametros[tipo_cultivo]["profundidad_raiz_m"]


def calcular_dias_desde_siembra(fecha_siembra, fecha_actual):
    """
    Calcula cuantos dias completos han pasado desde la fecha de
    siembra hasta la fecha actual.

    Parametros:
        fecha_siembra (datetime): fecha en que se sembro el cultivo.
        fecha_actual (datetime): fecha actual (normalmente datetime.now()).

    Retorna:
        int: cantidad de dias desde la siembra (0 si la fecha de
        siembra es hoy o en el futuro).
    """
    diferencia = (fecha_actual - fecha_siembra).days
    return max(0, diferencia)
