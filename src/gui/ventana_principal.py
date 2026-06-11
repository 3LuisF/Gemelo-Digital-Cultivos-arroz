"""
Ventana principal de la aplicacion. Contiene las 6 pestañas del
sistema y la barra de estado inferior. Tambien se encarga de crear y
arrancar los hilos de fondo (lectura del PLC, clima y gemelo digital),
y de conectar sus señales con los metodos de cada pestaña.
"""

import os

from PyQt5.QtWidgets import QMainWindow, QTabWidget, QLabel
from PyQt5.QtCore import QTimer, QDateTime

from src.plc.conexion_plc import ConexionPLC
from src.gui.hilos import HiloLecturaPLC, HiloClima, HiloGemelo
from src.gui.pestana_estado import PestanaEstado
from src.gui.pestana_gemelo import PestanaGemelo
from src.gui.pestana_manual import PestanaManual
from src.gui.pestana_historico import PestanaHistorico
from src.gui.pestana_clima import PestanaClima
from src.gui.pestana_config import PestanaConfig
from src.utilidades.logger import obtener_logger

logger = obtener_logger("gui")

# Carpeta raiz del proyecto (un nivel arriba de src/)
CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_ESTILOS_QSS = os.path.join(CARPETA_RAIZ, "src", "gui", "recursos", "estilos.qss")


class VentanaPrincipal(QMainWindow):
    """
    Ventana principal del Gemelo Digital de Riego. Organiza las
    pestañas, la barra de estado y los hilos de fondo.
    """

    def __init__(self, settings):
        """
        Parametros:
            settings (dict): configuracion general cargada desde
                "config/settings.yaml".
        """
        super().__init__()
        self.settings = settings

        self.setWindowTitle("Gemelo Digital de Riego - Cordoba")
        self.resize(1100, 750)

        self._aplicar_estilos()

        # --- Conexion al PLC (puede quedar en modo simulado si falla) ---
        plc_config = self.settings["plc"]
        self.conexion_plc = ConexionPLC(
            ip=plc_config["ip"],
            rack=plc_config["rack"],
            slot=plc_config["slot"],
            timeout_ms=plc_config.get("timeout_ms", 2000),
        )
        self.conexion_plc.conectar()

        # --- Creacion de las pestañas ---
        self.pestana_estado = PestanaEstado()
        self.pestana_gemelo = PestanaGemelo()
        self.pestana_manual = PestanaManual(self.conexion_plc)
        self.pestana_historico = PestanaHistorico()
        self.pestana_clima = PestanaClima(self.settings)
        self.pestana_config = PestanaConfig(self.settings)

        pestañas = QTabWidget()
        pestañas.addTab(self.pestana_estado, "Estado actual")
        pestañas.addTab(self.pestana_gemelo, "Gemelo digital")
        pestañas.addTab(self.pestana_manual, "Control manual")
        pestañas.addTab(self.pestana_historico, "Historico")
        pestañas.addTab(self.pestana_clima, "Clima")
        pestañas.addTab(self.pestana_config, "Configuracion")

        self.setCentralWidget(pestañas)

        # --- Barra de estado ---
        self.label_hora = QLabel()
        self.label_estado_plc = QLabel()
        self.label_ultima_actualizacion = QLabel("Ultima actualizacion: --")

        self.statusBar().addPermanentWidget(self.label_hora)
        self.statusBar().addPermanentWidget(QLabel(" | "))
        self.statusBar().addPermanentWidget(self.label_estado_plc)
        self.statusBar().addPermanentWidget(QLabel(" | "))
        self.statusBar().addPermanentWidget(self.label_ultima_actualizacion)

        # Reloj de la barra de estado, se actualiza cada segundo
        self.temporizador_reloj = QTimer(self)
        self.temporizador_reloj.timeout.connect(self._actualizar_reloj)
        self.temporizador_reloj.start(1000)
        self._actualizar_reloj()
        self._actualizar_estado_plc(self.conexion_plc.conectado)

        # --- Conexion de señales entre pestañas ---
        self.pestana_estado.solicitar_actualizacion.connect(self._solicitar_lectura_inmediata)

        # --- Hilos de fondo ---
        intervalos = self.settings.get("intervalos", {})

        self.hilo_lectura_plc = HiloLecturaPLC(
            self.conexion_plc, self.settings,
            intervalo_segundos=intervalos.get("lectura_plc_segundos", 5),
        )
        self.hilo_lectura_plc.nueva_lectura.connect(self._on_nueva_lectura)

        self.hilo_clima = HiloClima(
            self.settings,
            intervalo_minutos=intervalos.get("consulta_clima_minutos", 60),
        )
        self.hilo_clima.nuevo_pronostico.connect(self._on_nuevo_pronostico)

        self.hilo_gemelo = HiloGemelo(
            self.settings,
            intervalo_segundos=intervalos.get("recalculo_gemelo_segundos", 30),
        )
        self.hilo_gemelo.nuevo_estado.connect(self.pestana_gemelo.actualizar_estado)

        self.hilo_lectura_plc.start()
        self.hilo_clima.start()
        self.hilo_gemelo.start()

        logger.info("Ventana principal iniciada y hilos de fondo en marcha.")

    def _aplicar_estilos(self):
        """
        Carga y aplica la hoja de estilos QSS de la aplicacion.

        Retorna:
            None
        """
        try:
            with open(RUTA_ESTILOS_QSS, "r", encoding="utf-8") as archivo:
                self.setStyleSheet(archivo.read())
        except Exception as error:
            logger.warning(f"No se pudo cargar la hoja de estilos: {error}")

    def _actualizar_reloj(self):
        """
        Actualiza el texto de la hora en la barra de estado.

        Retorna:
            None
        """
        ahora = QDateTime.currentDateTime()
        self.label_hora.setText(ahora.toString("yyyy-MM-dd HH:mm:ss"))

    def _actualizar_estado_plc(self, conectado):
        """
        Actualiza el indicador de estado del PLC en la barra de estado.

        Parametros:
            conectado (bool): True si el PLC esta conectado, False si
                el sistema esta en modo simulado/offline.

        Retorna:
            None
        """
        if conectado:
            self.label_estado_plc.setText("PLC: ONLINE")
            self.label_estado_plc.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self.label_estado_plc.setText("PLC: OFFLINE (modo simulado)")
            self.label_estado_plc.setStyleSheet("color: #c62828; font-weight: bold;")

    def _solicitar_lectura_inmediata(self):
        """
        Atiende el boton "Actualizar ahora" de la pestaña de Estado:
        hace una lectura inmediata del PLC (o de la BD si esta
        offline).

        Retorna:
            None
        """
        self.hilo_lectura_plc.leer_y_emitir_una_vez()

    def _on_nueva_lectura(self, lectura):
        """
        Slot que recibe una nueva lectura de sensores (desde
        HiloLecturaPLC) y actualiza la pestaña de Estado, la pestaña de
        Control Manual y la barra de estado.

        Parametros:
            lectura (dict): ver HiloLecturaPLC._leer_una_vez().

        Retorna:
            None
        """
        self.pestana_estado.actualizar_datos(lectura)
        self.pestana_manual.actualizar_indicadores_entradas(lectura)

        self._actualizar_estado_plc(lectura["conectado"])

        timestamp = lectura["timestamp"]
        self.label_ultima_actualizacion.setText(f"Ultima actualizacion: {timestamp.strftime('%H:%M:%S')}")

    def _on_nuevo_pronostico(self, pronostico):
        """
        Slot que recibe un nuevo pronostico del clima (desde
        HiloClima) y actualiza la pestaña de Clima y la pestaña de
        Gemelo Digital.

        Parametros:
            pronostico (list[dict]): ver clima/open_meteo.py.

        Retorna:
            None
        """
        self.pestana_clima.actualizar_pronostico(pronostico)
        self.pestana_gemelo.actualizar_pronostico(pronostico)

    def closeEvent(self, evento):
        """
        Se ejecuta cuando el usuario cierra la ventana. Detiene los
        hilos de fondo y cierra la conexion con el PLC de forma
        ordenada.

        Parametros:
            evento (QCloseEvent): evento de cierre de la ventana.

        Retorna:
            None

        Efectos secundarios:
            Detiene los QThread y cierra el socket del PLC.
        """
        logger.info("Cerrando la aplicacion...")

        self.hilo_lectura_plc.detener()
        self.hilo_clima.detener()
        self.hilo_gemelo.detener()

        self.hilo_lectura_plc.wait(2000)
        self.hilo_clima.wait(2000)
        self.hilo_gemelo.wait(2000)

        self.conexion_plc.desconectar()

        evento.accept()
