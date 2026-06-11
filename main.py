"""
Punto de entrada del Gemelo Digital de Riego.

Este script:
  1. Carga la configuracion desde "config/settings.yaml".
  2. Inicializa la base de datos SQLite (crea las tablas si no existen).
  3. Lanza la ventana principal de PyQt5.
  4. La ventana principal se encarga de iniciar los hilos de fondo y de
     cerrar todo correctamente cuando se cierra la aplicacion.
"""

import sys
import os

from PyQt5.QtWidgets import QApplication

from src.utilidades import configuracion as config_utils
from src.utilidades.logger import obtener_logger
from src.database import gestor_db
from src.gui.ventana_principal import VentanaPrincipal

logger = obtener_logger("main")

CARPETA_RAIZ = os.path.dirname(os.path.abspath(__file__))


def main():
    """
    Funcion principal: carga configuracion, inicializa la base de
    datos y lanza la interfaz grafica.

    Retorna:
        None

    Efectos secundarios:
        Crea/abre el archivo de base de datos SQLite y abre la ventana
        de la aplicacion (bloquea hasta que el usuario la cierra).
    """
    logger.info("Iniciando Gemelo Digital de Riego...")

    settings = config_utils.cargar_settings()

    # La ruta de la base de datos en settings.yaml es relativa a la raiz del proyecto
    ruta_db = os.path.join(CARPETA_RAIZ, settings["database"]["ruta"])
    gestor_db.inicializar_base_datos(ruta_db)

    aplicacion = QApplication(sys.argv)

    ventana = VentanaPrincipal(settings)
    ventana.show()

    sys.exit(aplicacion.exec_())


if __name__ == "__main__":
    main()
