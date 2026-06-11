"""
Widget simple para mostrar un indicador grande: un titulo, un valor
numerico y su unidad. Se usa en la pestaña "Estado Actual" para mostrar
temperatura, humedad, caudal, etc.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class IndicadorWidget(QWidget):
    """
    Widget que muestra un titulo arriba (ej: "Temperatura") y un valor
    grande abajo (ej: "23.5 °C"). El valor se puede actualizar despues
    con el metodo actualizar_valor().
    """

    def __init__(self, titulo, unidad, parent=None):
        """
        Crea el indicador.

        Parametros:
            titulo (str): nombre del dato que se va a mostrar.
            unidad (str): unidad fisica del dato (ej: "°C", "%", "L/min").
            parent (QWidget|None): widget padre.
        """
        super().__init__(parent)

        self.unidad = unidad

        self.label_titulo = QLabel(titulo)
        self.label_titulo.setAlignment(Qt.AlignCenter)
        self.label_titulo.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.label_valor = QLabel("--")
        self.label_valor.setAlignment(Qt.AlignCenter)
        self.label_valor.setStyleSheet("font-size: 28px; font-weight: bold; color: #2e7d32;")

        layout = QVBoxLayout()
        layout.addWidget(self.label_titulo)
        layout.addWidget(self.label_valor)
        self.setLayout(layout)

        self.setStyleSheet(
            "IndicadorWidget { border: 1px solid #cccccc; border-radius: 8px; background-color: #f5f5f5; }"
        )

    def actualizar_valor(self, valor):
        """
        Actualiza el texto del valor mostrado.

        Parametros:
            valor (float|str|None): nuevo valor a mostrar. Si es None,
                se muestra "--" (sin dato).

        Retorna:
            None
        """
        if valor is None:
            self.label_valor.setText("--")
            return

        if isinstance(valor, float):
            self.label_valor.setText(f"{valor:.1f} {self.unidad}")
        else:
            self.label_valor.setText(f"{valor} {self.unidad}")
