"""
Pestaña "Configuracion": permite ver y editar la configuracion del
PLC, del cultivo, del suelo y de la ubicacion del proyecto. Los
cambios se guardan en los archivos YAML de la carpeta "config/" y en
la base de datos (configuracion del cultivo).
"""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QDateEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import QDate

from src.database import gestor_db
from src.plc.conexion_plc import ConexionPLC
from src.utilidades import configuracion as config_utils
from src.utilidades.logger import obtener_logger

logger = obtener_logger("gui")

# Tipos de cultivo disponibles: (texto mostrado al usuario, llave interna)
TIPOS_CULTIVO = [
    ("Arroz secano", "arroz_secano"),
    ("Maiz", "maiz"),
]


class PestanaConfig(QWidget):
    """
    Pestaña de configuracion general del sistema.
    """

    def __init__(self, settings, parent=None):
        """
        Parametros:
            settings (dict): configuracion actual cargada desde
                "config/settings.yaml".
            parent (QWidget|None): widget padre.
        """
        super().__init__(parent)
        self.settings = settings

        # --- Seccion: PLC ---
        grupo_plc = QGroupBox("Configuracion del PLC (LOGO! 8)")
        formulario_plc = QFormLayout()

        self.campo_ip = QLineEdit(self.settings["plc"]["ip"])

        self.campo_rack = QSpinBox()
        self.campo_rack.setRange(0, 10)
        self.campo_rack.setValue(self.settings["plc"]["rack"])

        self.campo_slot = QSpinBox()
        self.campo_slot.setRange(0, 10)
        self.campo_slot.setValue(self.settings["plc"]["slot"])

        self.boton_probar_conexion = QPushButton("Probar conexion PLC")
        self.boton_probar_conexion.clicked.connect(self._probar_conexion_plc)

        formulario_plc.addRow("Direccion IP:", self.campo_ip)
        formulario_plc.addRow("Rack:", self.campo_rack)
        formulario_plc.addRow("Slot:", self.campo_slot)
        formulario_plc.addRow(self.boton_probar_conexion)

        grupo_plc.setLayout(formulario_plc)

        # --- Seccion: cultivo ---
        grupo_cultivo = QGroupBox("Configuracion del cultivo")
        formulario_cultivo = QFormLayout()

        self.combo_tipo_cultivo = QComboBox()
        for texto, _llave in TIPOS_CULTIVO:
            self.combo_tipo_cultivo.addItem(texto)

        self.campo_fecha_siembra = QDateEdit(QDate.currentDate())
        self.campo_fecha_siembra.setCalendarPopup(True)

        self.campo_area = QDoubleSpinBox()
        self.campo_area.setRange(0.0, 10000.0)
        self.campo_area.setDecimals(2)
        self.campo_area.setSuffix(" ha")

        formulario_cultivo.addRow("Tipo de cultivo:", self.combo_tipo_cultivo)
        formulario_cultivo.addRow("Fecha de siembra:", self.campo_fecha_siembra)
        formulario_cultivo.addRow("Area sembrada:", self.campo_area)

        grupo_cultivo.setLayout(formulario_cultivo)

        self._cargar_configuracion_cultivo()

        # --- Seccion: suelo ---
        grupo_suelo = QGroupBox("Parametros del suelo")
        formulario_suelo = QFormLayout()

        suelo_actual = config_utils.cargar_suelo()

        self.campo_capacidad_campo = QDoubleSpinBox()
        self.campo_capacidad_campo.setRange(0.0, 1.0)
        self.campo_capacidad_campo.setDecimals(2)
        self.campo_capacidad_campo.setSingleStep(0.01)
        self.campo_capacidad_campo.setValue(suelo_actual["capacidad_campo"])

        self.campo_punto_marchitez = QDoubleSpinBox()
        self.campo_punto_marchitez.setRange(0.0, 1.0)
        self.campo_punto_marchitez.setDecimals(2)
        self.campo_punto_marchitez.setSingleStep(0.01)
        self.campo_punto_marchitez.setValue(suelo_actual["punto_marchitez"])

        formulario_suelo.addRow("Capacidad de campo (fraccion, ej: 0.32 = 32%):", self.campo_capacidad_campo)
        formulario_suelo.addRow("Punto de marchitez (fraccion, ej: 0.18 = 18%):", self.campo_punto_marchitez)

        grupo_suelo.setLayout(formulario_suelo)

        # --- Seccion: ubicacion ---
        grupo_ubicacion = QGroupBox("Ubicacion del cultivo")
        formulario_ubicacion = QFormLayout()

        self.campo_latitud = QDoubleSpinBox()
        self.campo_latitud.setRange(-90.0, 90.0)
        self.campo_latitud.setDecimals(4)
        self.campo_latitud.setValue(self.settings["ubicacion"]["latitud"])

        self.campo_longitud = QDoubleSpinBox()
        self.campo_longitud.setRange(-180.0, 180.0)
        self.campo_longitud.setDecimals(4)
        self.campo_longitud.setValue(self.settings["ubicacion"]["longitud"])

        formulario_ubicacion.addRow("Latitud:", self.campo_latitud)
        formulario_ubicacion.addRow("Longitud:", self.campo_longitud)

        grupo_ubicacion.setLayout(formulario_ubicacion)

        # --- Boton guardar ---
        self.boton_guardar = QPushButton("Guardar configuracion")
        self.boton_guardar.clicked.connect(self._guardar_configuracion)

        # --- Layout general ---
        layout_principal = QVBoxLayout()
        layout_principal.addWidget(grupo_plc)
        layout_principal.addWidget(grupo_cultivo)
        layout_principal.addWidget(grupo_suelo)
        layout_principal.addWidget(grupo_ubicacion)
        layout_principal.addWidget(self.boton_guardar)
        layout_principal.addStretch()

        self.setLayout(layout_principal)

    def _cargar_configuracion_cultivo(self):
        """
        Carga la configuracion de cultivo activa (si existe) desde la
        base de datos y la muestra en el formulario.

        Retorna:
            None
        """
        config_actual = gestor_db.obtener_configuracion_cultivo_activa()

        if config_actual is None:
            return

        for indice, (_texto, llave) in enumerate(TIPOS_CULTIVO):
            if llave == config_actual["tipo_cultivo"]:
                self.combo_tipo_cultivo.setCurrentIndex(indice)
                break

        fecha_siembra = config_actual["fecha_siembra"]
        self.campo_fecha_siembra.setDate(QDate(fecha_siembra.year, fecha_siembra.month, fecha_siembra.day))

        if config_actual["area_hectareas"] is not None:
            self.campo_area.setValue(config_actual["area_hectareas"])

    def _probar_conexion_plc(self):
        """
        Intenta conectarse al LOGO! 8 con los datos actuales del
        formulario (IP, rack, slot) y muestra el resultado en un popup.
        Esta conexion de prueba se cierra inmediatamente despues.

        Retorna:
            None

        Efectos secundarios:
            Abre y cierra una conexion de red hacia el PLC.
        """
        ip = self.campo_ip.text().strip()
        rack = self.campo_rack.value()
        slot = self.campo_slot.value()

        conexion_prueba = ConexionPLC(ip, rack, slot, self.settings["plc"].get("timeout_ms", 2000))
        conectado = conexion_prueba.conectar()

        if conectado:
            QMessageBox.information(self, "Conexion exitosa", f"Se conecto correctamente al LOGO! 8 en {ip}.")
            conexion_prueba.desconectar()
        else:
            QMessageBox.warning(
                self, "Sin conexion",
                f"No se pudo conectar al LOGO! 8 en {ip}.\n\nEl sistema seguira funcionando en modo simulado."
            )

    def _guardar_configuracion(self):
        """
        Guarda todos los valores del formulario:
          - Configuracion del PLC y ubicacion en "config/settings.yaml".
          - Parametros del suelo en "config/suelo.yaml".
          - Configuracion del cultivo activo en la base de datos.

        Retorna:
            None

        Efectos secundarios:
            Sobrescribe "config/settings.yaml" y "config/suelo.yaml", y
            agrega una nueva fila en "configuracion_cultivo".
        """
        # --- Actualizamos el diccionario de settings en memoria ---
        self.settings["plc"]["ip"] = self.campo_ip.text().strip()
        self.settings["plc"]["rack"] = self.campo_rack.value()
        self.settings["plc"]["slot"] = self.campo_slot.value()

        self.settings["ubicacion"]["latitud"] = self.campo_latitud.value()
        self.settings["ubicacion"]["longitud"] = self.campo_longitud.value()

        config_utils.guardar_settings(self.settings)

        # --- Parametros del suelo ---
        suelo_actual = config_utils.cargar_suelo()
        suelo_actual["capacidad_campo"] = self.campo_capacidad_campo.value()
        suelo_actual["punto_marchitez"] = self.campo_punto_marchitez.value()
        config_utils.guardar_suelo(suelo_actual)

        # --- Configuracion del cultivo ---
        indice_cultivo = self.combo_tipo_cultivo.currentIndex()
        tipo_cultivo = TIPOS_CULTIVO[indice_cultivo][1]

        fecha_siembra_qdate = self.campo_fecha_siembra.date()
        fecha_siembra = datetime(fecha_siembra_qdate.year(), fecha_siembra_qdate.month(), fecha_siembra_qdate.day())

        gestor_db.guardar_configuracion_cultivo(
            tipo_cultivo=tipo_cultivo,
            fecha_siembra=fecha_siembra,
            area_hectareas=self.campo_area.value(),
        )

        QMessageBox.information(
            self, "Configuracion guardada",
            "La configuracion se guardo correctamente.\n\n"
            "Algunos cambios (como la IP del PLC) requieren reiniciar la aplicacion para aplicarse por completo."
        )

        logger.info("Configuracion guardada desde la pestaña de Configuracion")
