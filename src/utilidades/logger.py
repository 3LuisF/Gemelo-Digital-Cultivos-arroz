"""
Modulo de logging basico para el Gemelo Digital.

Crea un archivo de log diario en la carpeta "logs/" con formato
"gemelo_AAAA-MM-DD.log". Todas las partes del sistema (PLC, base de
datos, modelos hidricos, GUI) usan esta misma funcion para registrar
eventos importantes.
"""

import logging
import os
from datetime import datetime


def obtener_logger(nombre_modulo):
    """
    Crea (o devuelve si ya existe) un logger configurado para escribir
    en un archivo dentro de la carpeta "logs/".

    Parametros:
        nombre_modulo (str): nombre del modulo que pide el logger,
            por ejemplo "plc" o "gemelo". Se usa para identificar
            de donde viene cada mensaje en el archivo de log.

    Retorna:
        logging.Logger: objeto logger ya configurado.

    Efectos secundarios:
        Crea la carpeta "logs/" si no existe y crea/abre el archivo
        de log del dia actual.
    """
    # Carpeta logs en la raiz del proyecto (un nivel arriba de src/)
    carpeta_raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    carpeta_logs = os.path.join(carpeta_raiz, "logs")

    if not os.path.exists(carpeta_logs):
        os.makedirs(carpeta_logs)

    # Nombre del archivo de log con la fecha de hoy
    nombre_archivo = "gemelo_" + datetime.now().strftime("%Y-%m-%d") + ".log"
    ruta_archivo = os.path.join(carpeta_logs, nombre_archivo)

    logger = logging.getLogger(nombre_modulo)

    # Si el logger ya tiene handlers configurados, no lo volvemos a configurar
    # (esto evita que se dupliquen los mensajes si se llama varias veces)
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formato = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        manejador_archivo = logging.FileHandler(ruta_archivo, encoding="utf-8")
        manejador_archivo.setFormatter(formato)
        logger.addHandler(manejador_archivo)

        # Tambien mostramos los mensajes en consola, util para depurar
        manejador_consola = logging.StreamHandler()
        manejador_consola.setFormatter(formato)
        logger.addHandler(manejador_consola)

    return logger
