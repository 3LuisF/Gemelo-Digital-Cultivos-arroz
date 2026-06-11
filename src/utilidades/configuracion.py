"""
Funciones para leer y escribir los archivos de configuracion YAML del
proyecto (config/settings.yaml y config/suelo.yaml).
"""

import os
import yaml

# Carpeta raiz del proyecto (un nivel arriba de src/)
CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_SETTINGS_YAML = os.path.join(CARPETA_RAIZ, "config", "settings.yaml")
RUTA_SUELO_YAML = os.path.join(CARPETA_RAIZ, "config", "suelo.yaml")


def cargar_settings():
    """
    Lee el archivo "config/settings.yaml" y lo retorna como diccionario.

    Retorna:
        dict: configuracion general (PLC, base de datos, ubicacion,
        intervalos, escalas de entradas).
    """
    with open(RUTA_SETTINGS_YAML, "r", encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def guardar_settings(settings):
    """
    Escribe el diccionario de configuracion en "config/settings.yaml",
    sobrescribiendo el contenido anterior.

    Parametros:
        settings (dict): configuracion completa a guardar (debe tener
            la misma estructura que el archivo original).

    Retorna:
        None

    Efectos secundarios:
        Sobrescribe el archivo "config/settings.yaml".
    """
    with open(RUTA_SETTINGS_YAML, "w", encoding="utf-8") as archivo:
        yaml.safe_dump(settings, archivo, allow_unicode=True, sort_keys=False)


def cargar_suelo():
    """
    Lee el archivo "config/suelo.yaml" y retorna los parametros del
    suelo configurado actualmente.

    Retorna:
        dict: con las llaves "textura", "capacidad_campo",
        "punto_marchitez" y "densidad_aparente" del suelo configurado
        (clave "suelo_franco_arcilloso_sinu").
    """
    with open(RUTA_SUELO_YAML, "r", encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo)

    # Por ahora solo manejamos un tipo de suelo configurado
    return datos["suelo_franco_arcilloso_sinu"]


def guardar_suelo(parametros_suelo):
    """
    Escribe los parametros del suelo en "config/suelo.yaml".

    Parametros:
        parametros_suelo (dict): debe tener las llaves "textura",
            "capacidad_campo", "punto_marchitez" y "densidad_aparente".

    Retorna:
        None

    Efectos secundarios:
        Sobrescribe el archivo "config/suelo.yaml".
    """
    contenido = {"suelo_franco_arcilloso_sinu": parametros_suelo}

    with open(RUTA_SUELO_YAML, "w", encoding="utf-8") as archivo:
        yaml.safe_dump(contenido, archivo, allow_unicode=True, sort_keys=False)
