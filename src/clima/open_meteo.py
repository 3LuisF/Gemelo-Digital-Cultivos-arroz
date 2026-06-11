"""
Modulo para consultar el pronostico del clima usando la API gratuita
de Open-Meteo (no requiere API key).

Documentacion de la API: https://open-meteo.com/en/docs
"""

import requests
from datetime import datetime

from src.utilidades.logger import obtener_logger
from src.database import gestor_db

logger = obtener_logger("clima")

URL_BASE_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"


def obtener_pronostico(latitud, longitud, dias=7):
    """
    Consulta el pronostico del clima para los proximos dias en la
    ubicacion indicada, usando la API de Open-Meteo.

    Parametros:
        latitud (float): latitud del cultivo (ej: 8.7479 para Monteria).
        longitud (float): longitud del cultivo (ej: -75.8814).
        dias (int): cantidad de dias de pronostico a pedir (por defecto 7).

    Retorna:
        list[dict]: lista de diccionarios, uno por dia, con las llaves:
            "fecha_pronostico", "temp_max", "temp_min", "lluvia_mm",
            "humedad_rel", "et0_estimada".
        Si la peticion falla, retorna el ultimo pronostico guardado en
        la base de datos (puede ser una lista vacia si nunca se ha
        consultado nada).

    Efectos secundarios:
        Si la peticion es exitosa, guarda el pronostico en la tabla
        "clima_pronostico" de la base de datos.
    """
    parametros = {
        "latitude": latitud,
        "longitude": longitud,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "et0_fao_evapotranspiration",
            "relative_humidity_2m_mean",
        ],
        "timezone": "America/Bogota",
        "forecast_days": dias,
    }

    try:
        respuesta = requests.get(URL_BASE_OPEN_METEO, params=parametros, timeout=10)
        respuesta.raise_for_status()
        datos_json = respuesta.json()

        pronostico = _convertir_json_a_lista(datos_json)

        gestor_db.guardar_pronostico_clima(pronostico)
        logger.info(f"Pronostico del clima actualizado correctamente ({len(pronostico)} dias).")

        return pronostico

    except Exception as error:
        logger.warning(f"No se pudo consultar Open-Meteo ({error}). Se usara el ultimo pronostico guardado.")
        return gestor_db.obtener_ultimo_pronostico(dias)


def _convertir_json_a_lista(datos_json):
    """
    Convierte la respuesta JSON de Open-Meteo (que viene organizada por
    columnas) en una lista de diccionarios, uno por cada dia.

    Parametros:
        datos_json (dict): respuesta ya convertida de JSON a dict.

    Retorna:
        list[dict]: lista de pronosticos diarios.
    """
    seccion_diaria = datos_json.get("daily", {})

    fechas = seccion_diaria.get("time", [])
    temps_max = seccion_diaria.get("temperature_2m_max", [])
    temps_min = seccion_diaria.get("temperature_2m_min", [])
    lluvias = seccion_diaria.get("precipitation_sum", [])
    humedades = seccion_diaria.get("relative_humidity_2m_mean", [])
    et0_valores = seccion_diaria.get("et0_fao_evapotranspiration", [])

    pronostico = []
    for indice, fecha_texto in enumerate(fechas):
        fecha_pronostico = datetime.strptime(fecha_texto, "%Y-%m-%d")

        pronostico.append({
            "fecha_pronostico": fecha_pronostico,
            "temp_max": temps_max[indice] if indice < len(temps_max) else None,
            "temp_min": temps_min[indice] if indice < len(temps_min) else None,
            "lluvia_mm": lluvias[indice] if indice < len(lluvias) else None,
            "humedad_rel": humedades[indice] if indice < len(humedades) else None,
            "et0_estimada": et0_valores[indice] if indice < len(et0_valores) else None,
        })

    return pronostico
