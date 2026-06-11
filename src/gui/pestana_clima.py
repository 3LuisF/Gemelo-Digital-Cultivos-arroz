"""
Pestaña "Clima": muestra el pronostico de 7 dias obtenido de
Open-Meteo, una grafica de barras con la lluvia esperada por dia y
alertas simples (lluvia fuerte o sequia proyectada).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt

from src.clima import open_meteo
from src.gui.widgets.grafica import GraficaWidget
from src.utilidades.logger import obtener_logger

logger = obtener_logger("gui")

COLUMNAS_TABLA = ["Fecha", "T° max (°C)", "T° min (°C)", "Lluvia (mm)", "Humedad (%)", "ET0 (mm/dia)"]

# Umbrales para las alertas simples
UMBRAL_LLUVIA_FUERTE_MM = 50.0
DIAS_SEQUIA_ALERTA = 5


class PestanaClima(QWidget):
    """
    Pestaña de pronostico del clima. Permite consultar Open-Meteo
    manualmente y muestra el pronostico en tabla, grafica de barras de
    lluvia y alertas de lluvia fuerte / sequia proyectada.
    """

    def __init__(self, settings, parent=None):
        """
        Parametros:
            settings (dict): configuracion general (incluye latitud y
                longitud del cultivo).
            parent (QWidget|None): widget padre.
        """
        super().__init__(parent)
        self.settings = settings
        self.ultimo_pronostico = []

        # --- Boton de actualizacion ---
        self.boton_actualizar = QPushButton("Actualizar pronostico")
        self.boton_actualizar.clicked.connect(self._actualizar_manual)

        layout_botones = QHBoxLayout()
        layout_botones.addWidget(self.boton_actualizar)
        layout_botones.addStretch()

        # --- Tabla de pronostico ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(COLUMNAS_TABLA))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS_TABLA)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        # --- Grafica de lluvia esperada ---
        self.grafica = GraficaWidget()

        # --- Texto de alertas ---
        self.label_alertas = QLabel("Sin alertas por ahora.")
        self.label_alertas.setWordWrap(True)
        self.label_alertas.setAlignment(Qt.AlignCenter)
        self.label_alertas.setStyleSheet("font-size: 14px; padding: 8px;")

        # --- Layout general ---
        layout_principal = QVBoxLayout()
        layout_principal.addLayout(layout_botones)
        layout_principal.addWidget(self.tabla)
        layout_principal.addWidget(self.grafica)
        layout_principal.addWidget(self.label_alertas)

        self.setLayout(layout_principal)

    def _actualizar_manual(self):
        """
        Consulta Open-Meteo de inmediato (al presionar el boton) y
        actualiza la tabla, la grafica y las alertas.

        Retorna:
            None

        Efectos secundarios:
            Hace una peticion HTTP a Open-Meteo y guarda el resultado
            en la base de datos (ver clima/open_meteo.py).
        """
        ubicacion = self.settings.get("ubicacion", {})
        latitud = ubicacion.get("latitud", 8.7479)
        longitud = ubicacion.get("longitud", -75.8814)

        pronostico = open_meteo.obtener_pronostico(latitud, longitud, dias=7)
        self.actualizar_pronostico(pronostico)

    def actualizar_pronostico(self, pronostico):
        """
        Actualiza la tabla, la grafica de barras y las alertas con un
        nuevo pronostico.

        Parametros:
            pronostico (list[dict]): lista de pronosticos diarios (ver
                clima/open_meteo.py).

        Retorna:
            None
        """
        self.ultimo_pronostico = pronostico

        self._llenar_tabla(pronostico)
        self._dibujar_grafica(pronostico)
        self._actualizar_alertas(pronostico)

    def _llenar_tabla(self, pronostico):
        """
        Llena la tabla con los datos diarios del pronostico.

        Parametros:
            pronostico (list[dict]): pronostico diario.

        Retorna:
            None
        """
        self.tabla.setRowCount(len(pronostico))

        for fila, dia in enumerate(pronostico):
            valores_fila = [
                dia["fecha_pronostico"].strftime("%Y-%m-%d"),
                self._formatear(dia.get("temp_max")),
                self._formatear(dia.get("temp_min")),
                self._formatear(dia.get("lluvia_mm")),
                self._formatear(dia.get("humedad_rel")),
                self._formatear(dia.get("et0_estimada")),
            ]

            for columna, valor in enumerate(valores_fila):
                self.tabla.setItem(fila, columna, QTableWidgetItem(valor))

        self.tabla.resizeColumnsToContents()

    def _dibujar_grafica(self, pronostico):
        """
        Dibuja una grafica de barras con la lluvia esperada para cada
        dia del pronostico.

        Parametros:
            pronostico (list[dict]): pronostico diario.

        Retorna:
            None
        """
        ejes = self.grafica.obtener_ejes()
        self.grafica.limpiar()

        if pronostico:
            etiquetas_fechas = [dia["fecha_pronostico"].strftime("%d-%m") for dia in pronostico]
            lluvias = [dia.get("lluvia_mm") or 0.0 for dia in pronostico]

            ejes.bar(etiquetas_fechas, lluvias, color="#1565c0")

        ejes.set_title("Lluvia esperada por dia (mm)")
        ejes.set_ylabel("mm")

        self.grafica.redibujar()

    def _actualizar_alertas(self, pronostico):
        """
        Revisa el pronostico y genera mensajes de alerta si se espera
        lluvia fuerte (> 50 mm en un dia) o sequia proyectada (mas de
        5 dias seguidos sin lluvia).

        Parametros:
            pronostico (list[dict]): pronostico diario.

        Retorna:
            None
        """
        alertas = []

        for dia in pronostico:
            lluvia = dia.get("lluvia_mm") or 0.0
            if lluvia > UMBRAL_LLUVIA_FUERTE_MM:
                fecha_texto = dia["fecha_pronostico"].strftime("%Y-%m-%d")
                alertas.append(f"Lluvia fuerte esperada el {fecha_texto}: {lluvia:.1f} mm.")

        # Contamos la racha mas larga de dias sin lluvia (lluvia <= 0.1 mm)
        racha_actual = 0
        racha_maxima = 0
        for dia in pronostico:
            lluvia = dia.get("lluvia_mm") or 0.0
            if lluvia <= 0.1:
                racha_actual += 1
                racha_maxima = max(racha_maxima, racha_actual)
            else:
                racha_actual = 0

        if racha_maxima > DIAS_SEQUIA_ALERTA:
            alertas.append(
                f"Posible sequia proyectada: se esperan {racha_maxima} dias seguidos sin lluvia significativa."
            )

        if alertas:
            self.label_alertas.setText(" | ".join(alertas))
            self.label_alertas.setStyleSheet("font-size: 14px; padding: 8px; color: #c62828; font-weight: bold;")
        else:
            self.label_alertas.setText("Sin alertas por ahora.")
            self.label_alertas.setStyleSheet("font-size: 14px; padding: 8px; color: #2e7d32;")

    def _formatear(self, valor):
        """
        Convierte un valor numerico (o None) a texto para mostrarlo en
        la tabla.

        Parametros:
            valor (float|None): valor a formatear.

        Retorna:
            str: "--" si el valor es None, o el numero con 1 decimal.
        """
        if valor is None:
            return "--"
        return f"{valor:.1f}"
