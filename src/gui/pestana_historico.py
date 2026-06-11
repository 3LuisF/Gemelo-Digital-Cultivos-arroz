"""
Pestaña "Historico": permite consultar las lecturas de sensores
guardadas en la base de datos, graficar una variable en un rango de
fechas, ver las ultimas 50 lecturas en una tabla y exportarlas a CSV.
"""

from datetime import datetime, timedelta

import pandas as pd

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox
)
from PyQt5.QtCore import QDate

from src.database import gestor_db
from src.gui.widgets.grafica import GraficaWidget
from src.utilidades.logger import obtener_logger

logger = obtener_logger("gui")

# Variables que se pueden graficar/consultar, con su etiqueta en
# español y la llave correspondiente en las lecturas de sensores
VARIABLES_DISPONIBLES = [
    ("Temperatura (°C)", "temperatura"),
    ("Humedad del suelo (%)", "humedad_suelo"),
    ("Caudal (L/min)", "caudal"),
    ("Lluvia (mm)", "lluvia_acumulada"),
]

COLUMNAS_TABLA = ["Fecha/hora", "Fuente", "Temperatura (°C)", "Humedad suelo (%)", "Caudal (L/min)", "Lluvia (mm)"]


class PestanaHistorico(QWidget):
    """
    Pestaña que permite revisar el historico de lecturas de sensores:
    grafica por variable, tabla con las ultimas lecturas y exportacion
    a CSV.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Controles de seleccion ---
        self.fecha_desde = QDateEdit(QDate.currentDate().addDays(-7))
        self.fecha_desde.setCalendarPopup(True)

        self.fecha_hasta = QDateEdit(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)

        self.combo_variable = QComboBox()
        for etiqueta, _llave in VARIABLES_DISPONIBLES:
            self.combo_variable.addItem(etiqueta)

        self.boton_consultar = QPushButton("Consultar")
        self.boton_consultar.clicked.connect(self.consultar_historico)

        self.boton_exportar = QPushButton("Exportar a CSV")
        self.boton_exportar.clicked.connect(self._exportar_csv)

        layout_controles = QHBoxLayout()
        layout_controles.addWidget(QLabel("Desde:"))
        layout_controles.addWidget(self.fecha_desde)
        layout_controles.addWidget(QLabel("Hasta:"))
        layout_controles.addWidget(self.fecha_hasta)
        layout_controles.addWidget(QLabel("Variable:"))
        layout_controles.addWidget(self.combo_variable)
        layout_controles.addWidget(self.boton_consultar)
        layout_controles.addWidget(self.boton_exportar)

        # --- Grafica ---
        self.grafica = GraficaWidget()

        # --- Tabla de ultimas lecturas ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(COLUMNAS_TABLA))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS_TABLA)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        # --- Layout general ---
        layout_principal = QVBoxLayout()
        layout_principal.addLayout(layout_controles)
        layout_principal.addWidget(self.grafica)
        layout_principal.addWidget(QLabel("Ultimas 50 lecturas:"))
        layout_principal.addWidget(self.tabla)

        self.setLayout(layout_principal)

        # Cargamos datos iniciales
        self.consultar_historico()

    def consultar_historico(self):
        """
        Consulta las lecturas de sensores en el rango de fechas
        seleccionado, dibuja la grafica de la variable elegida y
        actualiza la tabla con las ultimas 50 lecturas.

        Retorna:
            None
        """
        fecha_inicio = datetime.combine(self.fecha_desde.date().toPyDate(), datetime.min.time())
        # Sumamos un dia a "hasta" para incluir todo el dia seleccionado
        fecha_fin = datetime.combine(self.fecha_hasta.date().toPyDate(), datetime.min.time()) + timedelta(days=1)

        lecturas = gestor_db.obtener_lecturas_rango(fecha_inicio, fecha_fin)

        self._dibujar_grafica(lecturas)
        self._llenar_tabla()

    def _dibujar_grafica(self, lecturas):
        """
        Dibuja la grafica de la variable seleccionada en el rango de
        fechas consultado.

        Parametros:
            lecturas (list[dict]): lecturas de sensores en el rango
                seleccionado, ordenadas por fecha.

        Retorna:
            None
        """
        indice_variable = self.combo_variable.currentIndex()
        etiqueta_variable, llave_variable = VARIABLES_DISPONIBLES[indice_variable]

        ejes = self.grafica.obtener_ejes()
        self.grafica.limpiar()

        if lecturas:
            fechas = [lectura["timestamp"] for lectura in lecturas]
            valores = [lectura[llave_variable] for lectura in lecturas]
            ejes.plot(fechas, valores, color="#1565c0", marker=".")

        ejes.set_title(etiqueta_variable)
        ejes.tick_params(axis="x", rotation=30)

        self.grafica.redibujar()

    def _llenar_tabla(self):
        """
        Llena la tabla con las ultimas 50 lecturas de sensores
        guardadas en la base de datos (sin importar el rango de
        fechas seleccionado para la grafica).

        Retorna:
            None
        """
        ultimas_lecturas = gestor_db.obtener_ultimas_n_lecturas(50)

        self.tabla.setRowCount(len(ultimas_lecturas))

        for fila, lectura in enumerate(ultimas_lecturas):
            valores_fila = [
                lectura["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                lectura["fuente"],
                self._formatear(lectura["temperatura"]),
                self._formatear(lectura["humedad_suelo"]),
                self._formatear(lectura["caudal"]),
                self._formatear(lectura["lluvia_acumulada"]),
            ]

            for columna, valor in enumerate(valores_fila):
                self.tabla.setItem(fila, columna, QTableWidgetItem(valor))

        self.tabla.resizeColumnsToContents()

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

    def _exportar_csv(self):
        """
        Exporta las lecturas del rango de fechas seleccionado a un
        archivo CSV elegido por el usuario.

        Retorna:
            None

        Efectos secundarios:
            Crea un archivo CSV en la ruta que elija el usuario.
        """
        fecha_inicio = datetime.combine(self.fecha_desde.date().toPyDate(), datetime.min.time())
        fecha_fin = datetime.combine(self.fecha_hasta.date().toPyDate(), datetime.min.time()) + timedelta(days=1)

        lecturas = gestor_db.obtener_lecturas_rango(fecha_inicio, fecha_fin)

        if not lecturas:
            QMessageBox.information(self, "Sin datos", "No hay lecturas en el rango de fechas seleccionado.")
            return

        ruta_archivo, _filtro = QFileDialog.getSaveFileName(
            self, "Exportar a CSV", "lecturas_sensores.csv", "Archivos CSV (*.csv)"
        )

        if not ruta_archivo:
            return

        try:
            tabla_pandas = pd.DataFrame(lecturas)
            tabla_pandas.to_csv(ruta_archivo, index=False, encoding="utf-8")
            QMessageBox.information(self, "Exportacion exitosa", f"Datos exportados a:\n{ruta_archivo}")
            logger.info(f"Lecturas exportadas a CSV: {ruta_archivo}")
        except Exception as error:
            QMessageBox.critical(self, "Error al exportar", f"No se pudo exportar el archivo:\n{error}")
            logger.error(f"Error exportando CSV: {error}")
