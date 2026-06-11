"""
Pestaña "Control Manual": permite forzar manualmente los valores de
las entradas analogicas (caudal, lluvia, temperatura, humedad de
suelo) y el estado de las salidas digitales (valvulas y bomba).

Esta pestaña se usa principalmente porque la mayoria de los sensores
del proyecto son simulados (no hay hardware real conectado, excepto el
sensor PT100 de temperatura).

Toda accion manual:
  1. Muestra un popup de confirmacion.
  2. Si el usuario confirma, se ejecuta la accion y se registra en la
     tabla "acciones_manuales".
  3. Si el usuario cancela, no se hace nada.
"""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt

from src.database import gestor_db
from src.gui.widgets.popup_confirmacion import mostrar_confirmacion
from src.gui.widgets.indicador import IndicadorWidget
from src.gui.pestana_estado import IndicadorEstadoSalida
from src.utilidades.logger import obtener_logger

logger = obtener_logger("gui")


# Definicion de las entradas analogicas que se pueden forzar
# (nombre interno, etiqueta para el usuario, unidad, valor minimo, valor maximo, llave en lecturas_sensores)
ENTRADAS_FORZABLES = [
    ("AI1", "Caudal (AI1)", "L/min", 0.0, 100.0, "caudal"),
    ("AI2", "Pluviometro (AI2)", "mm/h", 0.0, 50.0, "lluvia_acumulada"),
    ("AI3", "Temperatura PT100 (AI3)", "°C", -20.0, 80.0, "temperatura"),
    ("AI4", "Humedad de suelo (AI4)", "%", 0.0, 100.0, "humedad_suelo"),
]

# Salidas digitales que se pueden forzar
SALIDAS_FORZABLES = [
    ("Q1", "Valvula zona 1 (Q1)"),
    ("Q2", "Valvula zona 2 (Q2)"),
    ("Q3", "Bomba principal (Q3)"),
]


class PestanaManual(QWidget):
    """
    Pestaña de control manual. Permite forzar entradas (simuladas) y
    salidas (valvulas/bomba) del sistema, siempre pidiendo confirmacion
    al usuario antes de aplicar cualquier cambio.
    """

    def __init__(self, conexion_plc, parent=None):
        """
        Parametros:
            conexion_plc (ConexionPLC): conexion al LOGO! 8. Se usa
                para escribir el estado de las salidas Q1-Q3 cuando el
                PLC esta conectado.
            parent (QWidget|None): widget padre.
        """
        super().__init__(parent)
        self.conexion_plc = conexion_plc

        # Guardamos los widgets de cada entrada/salida para poder
        # consultarlos despues (spinboxes, indicadores, botones)
        self.spinboxes_entradas = {}
        self.indicadores_entradas = {}
        self.botones_salidas = {}
        self.indicadores_salidas = {}

        # Estado simulado de las salidas (se usa cuando el PLC esta offline)
        self.estado_simulado_salidas = {"Q1": False, "Q2": False, "Q3": False}

        # --- Advertencia roja arriba ---
        self.label_advertencia = QLabel("MODO MANUAL — Use con precaucion")
        self.label_advertencia.setObjectName("tituloAdvertencia")
        self.label_advertencia.setAlignment(Qt.AlignCenter)

        # --- Columna izquierda: forzar entradas ---
        grupo_entradas = QGroupBox("Forzar entradas (sensores simulados)")
        layout_entradas = QGridLayout()

        for fila, (codigo, etiqueta, unidad, minimo, maximo, _llave) in enumerate(ENTRADAS_FORZABLES):
            label_nombre = QLabel(etiqueta)

            spinbox = QDoubleSpinBox()
            spinbox.setRange(minimo, maximo)
            spinbox.setDecimals(1)
            spinbox.setSuffix(f" {unidad}")
            self.spinboxes_entradas[codigo] = spinbox

            boton_aplicar = QPushButton("Aplicar valor")
            boton_aplicar.clicked.connect(
                lambda _checked, c=codigo: self._aplicar_entrada(c)
            )

            indicador = IndicadorWidget(f"Valor actual {codigo}", unidad)
            self.indicadores_entradas[codigo] = indicador

            layout_entradas.addWidget(label_nombre, fila, 0)
            layout_entradas.addWidget(spinbox, fila, 1)
            layout_entradas.addWidget(boton_aplicar, fila, 2)
            layout_entradas.addWidget(indicador, fila, 3)

        grupo_entradas.setLayout(layout_entradas)

        # --- Columna derecha: forzar salidas ---
        grupo_salidas = QGroupBox("Forzar salidas (valvulas / bomba)")
        layout_salidas = QGridLayout()

        for fila, (codigo, etiqueta) in enumerate(SALIDAS_FORZABLES):
            label_nombre = QLabel(etiqueta)

            boton_toggle = QPushButton("Encender")
            boton_toggle.setCheckable(True)
            boton_toggle.clicked.connect(
                lambda _checked, c=codigo: self._aplicar_salida(c)
            )
            self.botones_salidas[codigo] = boton_toggle

            indicador = IndicadorEstadoSalida(etiqueta)
            indicador.actualizar_estado(False)
            self.indicadores_salidas[codigo] = indicador

            layout_salidas.addWidget(label_nombre, fila, 0)
            layout_salidas.addWidget(boton_toggle, fila, 1)
            layout_salidas.addWidget(indicador, fila, 2)

        grupo_salidas.setLayout(layout_salidas)

        # --- Boton para volver a modo automatico ---
        self.boton_modo_automatico = QPushButton("Volver a modo automatico")
        self.boton_modo_automatico.clicked.connect(self._volver_a_automatico)

        # --- Layout general: dos columnas ---
        layout_columnas = QHBoxLayout()
        layout_columnas.addWidget(grupo_entradas)
        layout_columnas.addWidget(grupo_salidas)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.label_advertencia)
        layout_principal.addLayout(layout_columnas)
        layout_principal.addWidget(self.boton_modo_automatico)

        self.setLayout(layout_principal)

    def actualizar_indicadores_entradas(self, lectura):
        """
        Actualiza los indicadores de "valor actual" de las entradas con
        la ultima lectura de sensores.

        Parametros:
            lectura (dict): diccionario con las llaves "temperatura",
                "humedad_suelo", "caudal", "lluvia_acumulada".

        Retorna:
            None
        """
        mapa_valores = {
            "AI1": lectura.get("caudal"),
            "AI2": lectura.get("lluvia_acumulada"),
            "AI3": lectura.get("temperatura"),
            "AI4": lectura.get("humedad_suelo"),
        }

        for codigo, valor in mapa_valores.items():
            self.indicadores_entradas[codigo].actualizar_valor(valor)

    def _aplicar_entrada(self, codigo):
        """
        Aplica (fuerza) el valor del spinbox de una entrada despues de
        que el usuario confirma la accion. Guarda una nueva lectura
        "manual" en la base de datos y registra la accion en
        "acciones_manuales".

        Parametros:
            codigo (str): "AI1", "AI2", "AI3" o "AI4".

        Retorna:
            None

        Efectos secundarios:
            Escribe en las tablas "lecturas_sensores" y
            "acciones_manuales" de la base de datos.
        """
        info_entrada = next(item for item in ENTRADAS_FORZABLES if item[0] == codigo)
        _codigo, etiqueta, unidad, _minimo, _maximo, llave_lectura = info_entrada

        valor_nuevo = self.spinboxes_entradas[codigo].value()

        confirmado = mostrar_confirmacion(
            self,
            "Confirmar accion",
            f"¿Desea forzar el valor de '{etiqueta}' a {valor_nuevo} {unidad}?",
            texto_detallado=(
                f"Esta accion guardara una nueva lectura manual en la base de datos "
                f"y quedara registrada como una accion manual sobre {codigo}."
            ),
        )

        if not confirmado:
            return

        # Tomamos la ultima lectura para no perder los otros valores
        ultima_lectura = gestor_db.obtener_ultima_lectura()

        valores_actuales = {
            "temperatura": ultima_lectura["temperatura"] if ultima_lectura else None,
            "humedad_suelo": ultima_lectura["humedad_suelo"] if ultima_lectura else None,
            "caudal": ultima_lectura["caudal"] if ultima_lectura else None,
            "lluvia_acumulada": ultima_lectura["lluvia_acumulada"] if ultima_lectura else None,
        }

        valor_anterior = valores_actuales[llave_lectura]
        valores_actuales[llave_lectura] = valor_nuevo

        gestor_db.guardar_lectura_sensor(
            fuente="manual",
            temperatura=valores_actuales["temperatura"],
            humedad_suelo=valores_actuales["humedad_suelo"],
            caudal=valores_actuales["caudal"],
            lluvia_acumulada=valores_actuales["lluvia_acumulada"],
        )

        gestor_db.guardar_accion_manual(
            componente=codigo,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
        )

        self.indicadores_entradas[codigo].actualizar_valor(valor_nuevo)
        logger.info(f"Entrada {codigo} forzada manualmente a {valor_nuevo} {unidad}")

    def _aplicar_salida(self, codigo):
        """
        Cambia el estado de una salida digital (Q1, Q2, Q3) despues de
        que el usuario confirma la accion. Si el PLC esta conectado, se
        escribe la salida fisica; si no, se actualiza un estado
        simulado interno. Registra la accion en "acciones_manuales".

        Parametros:
            codigo (str): "Q1", "Q2" o "Q3".

        Retorna:
            None

        Efectos secundarios:
            Puede escribir en el PLC real (salida fisica) y siempre
            escribe en la tabla "acciones_manuales" de la base de datos.
        """
        boton = self.botones_salidas[codigo]
        valor_anterior = self.estado_simulado_salidas[codigo]
        valor_nuevo = boton.isChecked()

        etiqueta = next(item[1] for item in SALIDAS_FORZABLES if item[0] == codigo)

        confirmado = mostrar_confirmacion(
            self,
            "Confirmar accion",
            f"¿Desea {'ENCENDER' if valor_nuevo else 'APAGAR'} '{etiqueta}'?",
            texto_detallado=f"Esta accion forzara el estado de la salida {codigo} y quedara registrada.",
        )

        if not confirmado:
            # El usuario cancelo: regresamos el boton a su estado anterior
            boton.setChecked(valor_anterior)
            return

        # Si el PLC esta conectado, escribimos la salida fisica
        if self.conexion_plc.conectado:
            self.conexion_plc.escribir_salida_digital(codigo, valor_nuevo)

        self.estado_simulado_salidas[codigo] = valor_nuevo
        self.indicadores_salidas[codigo].actualizar_estado(valor_nuevo)
        boton.setText("Apagar" if valor_nuevo else "Encender")

        gestor_db.guardar_accion_manual(
            componente=codigo,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
        )

        logger.info(f"Salida {codigo} forzada manualmente a {'ON' if valor_nuevo else 'OFF'}")

    def _volver_a_automatico(self):
        """
        Apaga todas las salidas forzadas y vuelve los botones a su
        estado por defecto, despues de confirmar con el usuario.

        Retorna:
            None

        Efectos secundarios:
            Puede escribir en el PLC real (apaga Q1, Q2, Q3) y registra
            la accion en "acciones_manuales".
        """
        confirmado = mostrar_confirmacion(
            self,
            "Confirmar accion",
            "¿Desea volver a modo automatico? Esto apagara todas las salidas forzadas (Q1, Q2, Q3).",
        )

        if not confirmado:
            return

        for codigo, boton in self.botones_salidas.items():
            valor_anterior = self.estado_simulado_salidas[codigo]

            if self.conexion_plc.conectado:
                self.conexion_plc.escribir_salida_digital(codigo, False)

            self.estado_simulado_salidas[codigo] = False
            self.indicadores_salidas[codigo].actualizar_estado(False)
            boton.setChecked(False)
            boton.setText("Encender")

            if valor_anterior:
                gestor_db.guardar_accion_manual(
                    componente=codigo,
                    valor_anterior=valor_anterior,
                    valor_nuevo=False,
                )

        logger.info("Sistema regresado a modo automatico desde Control Manual")
