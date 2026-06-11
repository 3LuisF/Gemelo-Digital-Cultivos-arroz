"""
Funcion auxiliar para mostrar popups de confirmacion antes de ejecutar
acciones criticas (riego, forzamiento manual de entradas/salidas, etc).
"""

from PyQt5.QtWidgets import QMessageBox


def mostrar_confirmacion(parent, titulo, texto, texto_detallado=None):
    """
    Muestra un popup de confirmacion con botones "Si" / "No".

    Parametros:
        parent (QWidget): ventana o widget padre del popup.
        titulo (str): titulo de la ventana del popup.
        texto (str): texto principal explicando que accion se va a
            realizar.
        texto_detallado (str|None): texto tecnico adicional, que el
            usuario puede ver al hacer clic en "Show Details" (opcional).

    Retorna:
        bool: True si el usuario presiono "Si", False si presiono "No"
        o cerro el popup.
    """
    cuadro = QMessageBox(parent)
    cuadro.setIcon(QMessageBox.Warning)
    cuadro.setWindowTitle(titulo)
    cuadro.setText(texto)

    if texto_detallado:
        cuadro.setDetailedText(texto_detallado)

    cuadro.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    cuadro.setDefaultButton(QMessageBox.No)

    respuesta = cuadro.exec_()

    return respuesta == QMessageBox.Yes
