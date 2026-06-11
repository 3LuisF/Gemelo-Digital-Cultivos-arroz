"""
Widget que envuelve una grafica de matplotlib para poder mostrarla
dentro de una ventana de PyQt5.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class GraficaWidget(QWidget):
    """
    Widget reutilizable que contiene una figura de matplotlib
    embebida. Otros widgets pueden pedir los "ejes" (axes) con
    obtener_ejes(), dibujar lo que necesiten, y luego llamar a
    redibujar() para que se actualice la pantalla.
    """

    def __init__(self, parent=None, ancho=5, alto=4):
        """
        Crea la figura y el lienzo (canvas) donde se va a dibujar.

        Parametros:
            parent (QWidget|None): widget padre.
            ancho (float): ancho de la figura en pulgadas.
            alto (float): alto de la figura en pulgadas.
        """
        super().__init__(parent)

        self.figura = Figure(figsize=(ancho, alto))
        self.canvas = FigureCanvas(self.figura)
        self.ejes = self.figura.add_subplot(111)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def obtener_ejes(self):
        """
        Devuelve los ejes (axes) de matplotlib donde se puede dibujar
        (plot, bar, etc).

        Retorna:
            matplotlib.axes.Axes: los ejes de la grafica.
        """
        return self.ejes

    def limpiar(self):
        """
        Borra todo lo dibujado en los ejes, para volver a graficar
        desde cero.

        Retorna:
            None
        """
        self.ejes.clear()

    def redibujar(self):
        """
        Actualiza el lienzo para mostrar los cambios hechos en los ejes.

        Retorna:
            None
        """
        self.figura.tight_layout()
        self.canvas.draw()
