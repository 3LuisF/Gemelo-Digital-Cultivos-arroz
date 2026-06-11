"""
Pestaña "Estado Actual": muestra en una grilla los valores actuales de
los sensores (temperatura, humedad de suelo, caudal, lluvia) y el
estado de las valvulas y la bomba (Q1, Q2, Q3).
"""

from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from src.gui.widgets.indicador import IndicadorWidget


class IndicadorEstadoSalida(QWidget):
    """
    Pequeño widget que muestra el nombre de una salida (ej: "Bomba
    principal (Q3)") y un circulo/etiqueta de color verde (encendido)
    o rojo (apagado).
    """

    def __init__(self, titulo, parent=None):
        super().__init__(parent)

        self.label_titulo = QLabel(titulo)
        self.label_titulo.setAlignment(Qt.AlignCenter)
        self.label_titulo.setStyleSheet("font-weight: bold;")

        self.label_estado = QLabel("DESCONOCIDO")
        self.label_estado.setAlignment(Qt.AlignCenter)
        self.label_estado.setStyleSheet(
            "background-color: #9e9e9e; color: white; border-radius: 6px; padding: 6px; font-weight: bold;"
        )

        layout = QVBoxLayout()
        layout.addWidget(self.label_titulo)
        layout.addWidget(self.label_estado)
        self.setLayout(layout)

    def actualizar_estado(self, encendido):
        """
        Cambia el color y el texto del indicador segun el estado de la
        salida.

        Parametros:
            encendido (bool|None): True = encendido (verde), False =
                apagado (rojo), None = sin dato (gris).

        Retorna:
            None
        """
        if encendido is None:
            self.label_estado.setText("DESCONOCIDO")
            self.label_estado.setStyleSheet(
                "background-color: #9e9e9e; color: white; border-radius: 6px; padding: 6px; font-weight: bold;"
            )
        elif encendido:
            self.label_estado.setText("ENCENDIDO")
            self.label_estado.setStyleSheet(
                "background-color: #2e7d32; color: white; border-radius: 6px; padding: 6px; font-weight: bold;"
            )
        else:
            self.label_estado.setText("APAGADO")
            self.label_estado.setStyleSheet(
                "background-color: #c62828; color: white; border-radius: 6px; padding: 6px; font-weight: bold;"
            )


class PestanaEstado(QWidget):
    """
    Pestaña principal de monitoreo. Muestra los valores actuales de los
    sensores y el estado de las valvulas/bomba en una grilla 2x3.
    """

    # Señal emitida cuando el usuario presiona "Actualizar ahora"
    solicitar_actualizacion = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Indicadores de sensores ---
        self.indicador_temperatura = IndicadorWidget("Temperatura ambiente", "°C")
        self.indicador_humedad = IndicadorWidget("Humedad del suelo", "%")
        self.indicador_caudal = IndicadorWidget("Caudal actual", "L/min")
        self.indicador_lluvia = IndicadorWidget("Lluvia hoy", "mm")

        # --- Indicadores de salidas (valvulas y bomba) ---
        grupo_valvulas = QGroupBox("Estado de valvulas")
        self.indicador_q1 = IndicadorEstadoSalida("Valvula zona 1 (Q1)")
        self.indicador_q2 = IndicadorEstadoSalida("Valvula zona 2 (Q2)")
        layout_valvulas = QHBoxLayout()
        layout_valvulas.addWidget(self.indicador_q1)
        layout_valvulas.addWidget(self.indicador_q2)
        grupo_valvulas.setLayout(layout_valvulas)

        grupo_bomba = QGroupBox("Estado de la bomba")
        self.indicador_q3 = IndicadorEstadoSalida("Bomba principal (Q3)")
        layout_bomba = QVBoxLayout()
        layout_bomba.addWidget(self.indicador_q3)
        grupo_bomba.setLayout(layout_bomba)

        # --- Grilla 2x3 ---
        grilla = QGridLayout()
        grilla.addWidget(self.indicador_temperatura, 0, 0)
        grilla.addWidget(self.indicador_humedad, 0, 1)
        grilla.addWidget(self.indicador_caudal, 0, 2)
        grilla.addWidget(self.indicador_lluvia, 1, 0)
        grilla.addWidget(grupo_valvulas, 1, 1)
        grilla.addWidget(grupo_bomba, 1, 2)

        # --- Boton de actualizacion manual ---
        self.boton_actualizar = QPushButton("Actualizar ahora")
        self.boton_actualizar.clicked.connect(self.solicitar_actualizacion.emit)

        # --- Etiqueta con la ultima actualizacion ---
        self.label_ultima_actualizacion = QLabel("Sin datos todavia")
        self.label_ultima_actualizacion.setAlignment(Qt.AlignCenter)

        layout_principal = QVBoxLayout()
        layout_principal.addLayout(grilla)
        layout_principal.addWidget(self.boton_actualizar)
        layout_principal.addWidget(self.label_ultima_actualizacion)

        self.setLayout(layout_principal)

    def actualizar_datos(self, lectura):
        """
        Actualiza todos los indicadores de la pestaña con una nueva
        lectura de sensores.

        Parametros:
            lectura (dict): diccionario con las llaves "timestamp",
                "temperatura", "humedad_suelo", "caudal",
                "lluvia_acumulada" y "salidas" (dict con "Q1", "Q2",
                "Q3", "Q4" o None si no se pudo leer).

        Retorna:
            None
        """
        self.indicador_temperatura.actualizar_valor(lectura.get("temperatura"))
        self.indicador_humedad.actualizar_valor(lectura.get("humedad_suelo"))
        self.indicador_caudal.actualizar_valor(lectura.get("caudal"))
        self.indicador_lluvia.actualizar_valor(lectura.get("lluvia_acumulada"))

        salidas = lectura.get("salidas")
        if salidas is not None:
            self.indicador_q1.actualizar_estado(salidas.get("Q1"))
            self.indicador_q2.actualizar_estado(salidas.get("Q2"))
            self.indicador_q3.actualizar_estado(salidas.get("Q3"))
        else:
            self.indicador_q1.actualizar_estado(None)
            self.indicador_q2.actualizar_estado(None)
            self.indicador_q3.actualizar_estado(None)

        timestamp = lectura.get("timestamp")
        if timestamp is not None:
            texto_hora = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            fuente = lectura.get("fuente", "?")
            self.label_ultima_actualizacion.setText(f"Ultima actualizacion: {texto_hora} (fuente: {fuente})")
