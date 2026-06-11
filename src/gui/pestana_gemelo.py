"""
Pestaña "Gemelo Digital": muestra el estado hidrico actual del
cultivo, la informacion fenologica (etapa, Kc, dias desde siembra), la
recomendacion de riego generada por el simulador, y una grafica con el
balance hidrico de los ultimos 7 dias mas la proyeccion de los
proximos 7 dias.
"""

from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, QMessageBox
)
from PyQt5.QtCore import Qt

from src.database import gestor_db
from src.gemelo import simulador
from src.gui.widgets.grafica import GraficaWidget
from src.gui.widgets.popup_confirmacion import mostrar_confirmacion
from src.utilidades.logger import obtener_logger

logger = obtener_logger("gui")

# Nombres legibles de los tipos de cultivo (para mostrar en pantalla)
NOMBRES_CULTIVOS = {
    "arroz_secano": "Arroz secano",
    "maiz": "Maiz",
}


class PestanaGemelo(QWidget):
    """
    Pestaña que muestra el "gemelo digital" del cultivo: balance
    hidrico actual, datos fenologicos, recomendacion de riego y
    grafica historica + proyectada.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ultimo_estado = None
        self.ultimo_pronostico = None

        # --- Seccion: estado hidrico actual ---
        grupo_hidrico = QGroupBox("Estado hidrico actual")
        layout_hidrico = QGridLayout()

        self.label_agua_disponible = QLabel("--")
        self.label_deficit = QLabel("--")
        self.label_porcentaje_util = QLabel("--")

        layout_hidrico.addWidget(QLabel("Agua disponible:"), 0, 0)
        layout_hidrico.addWidget(self.label_agua_disponible, 0, 1)
        layout_hidrico.addWidget(QLabel("Deficit hidrico:"), 1, 0)
        layout_hidrico.addWidget(self.label_deficit, 1, 1)
        layout_hidrico.addWidget(QLabel("Porcentaje de agua util:"), 2, 0)
        layout_hidrico.addWidget(self.label_porcentaje_util, 2, 1)

        grupo_hidrico.setLayout(layout_hidrico)

        # --- Seccion: cultivo ---
        grupo_cultivo = QGroupBox("Cultivo")
        layout_cultivo = QGridLayout()

        self.label_tipo_cultivo = QLabel("--")
        self.label_dias_siembra = QLabel("--")
        self.label_etapa = QLabel("--")
        self.label_kc = QLabel("--")

        layout_cultivo.addWidget(QLabel("Tipo de cultivo:"), 0, 0)
        layout_cultivo.addWidget(self.label_tipo_cultivo, 0, 1)
        layout_cultivo.addWidget(QLabel("Dias desde siembra:"), 1, 0)
        layout_cultivo.addWidget(self.label_dias_siembra, 1, 1)
        layout_cultivo.addWidget(QLabel("Etapa fenologica:"), 2, 0)
        layout_cultivo.addWidget(self.label_etapa, 2, 1)
        layout_cultivo.addWidget(QLabel("Kc actual:"), 3, 0)
        layout_cultivo.addWidget(self.label_kc, 3, 1)

        grupo_cultivo.setLayout(layout_cultivo)

        # --- Seccion: recomendacion ---
        grupo_recomendacion = QGroupBox("Recomendacion de riego")
        layout_recomendacion = QVBoxLayout()

        self.label_recomendacion = QLabel("Esperando datos de sensores y clima...")
        self.label_recomendacion.setWordWrap(True)
        self.label_recomendacion.setStyleSheet("font-size: 16px; padding: 10px;")
        self.label_recomendacion.setAlignment(Qt.AlignCenter)

        self.boton_ejecutar_riego = QPushButton("EJECUTAR RIEGO RECOMENDADO")
        self.boton_ejecutar_riego.clicked.connect(self._ejecutar_riego_recomendado)

        layout_recomendacion.addWidget(self.label_recomendacion)
        layout_recomendacion.addWidget(self.boton_ejecutar_riego)
        grupo_recomendacion.setLayout(layout_recomendacion)

        # --- Seccion superior: las tres secciones de arriba en fila ---
        layout_superior = QHBoxLayout()
        layout_superior.addWidget(grupo_hidrico)
        layout_superior.addWidget(grupo_cultivo)
        layout_superior.addWidget(grupo_recomendacion)

        # --- Grafica de balance hidrico ---
        self.grafica = GraficaWidget()

        # --- Layout general ---
        layout_principal = QVBoxLayout()
        layout_principal.addLayout(layout_superior)
        layout_principal.addWidget(self.grafica)

        self.setLayout(layout_principal)

    def actualizar_estado(self, estado):
        """
        Actualiza las secciones de "estado hidrico" y "cultivo" con un
        nuevo resultado del balance hidrico, y vuelve a calcular la
        recomendacion de riego.

        Parametros:
            estado (dict): resultado de balance_hidrico.calcular_estado_hidrico()
                mas las llaves "etapa_fenologica", "kc_actual",
                "dias_desde_siembra", "tipo_cultivo".

        Retorna:
            None
        """
        self.ultimo_estado = estado

        self.label_agua_disponible.setText(
            f"{estado['agua_disponible_mm']:.1f} mm de {estado['agua_total_util_mm']:.1f} mm"
        )
        self.label_deficit.setText(f"{estado['deficit_mm']:.1f} mm")
        self.label_porcentaje_util.setText(f"{estado['porcentaje_agua_util']:.1f} %")

        if estado["esta_en_estres"]:
            self.label_porcentaje_util.setStyleSheet("color: #c62828; font-weight: bold;")
        else:
            self.label_porcentaje_util.setStyleSheet("color: #2e7d32; font-weight: bold;")

        nombre_cultivo = NOMBRES_CULTIVOS.get(estado["tipo_cultivo"], estado["tipo_cultivo"])
        self.label_tipo_cultivo.setText(nombre_cultivo)
        self.label_dias_siembra.setText(str(estado["dias_desde_siembra"]))
        self.label_etapa.setText(estado["etapa_fenologica"].capitalize())
        self.label_kc.setText(f"{estado['kc_actual']:.2f}")

        self._recalcular_simulacion()

    def actualizar_pronostico(self, pronostico):
        """
        Guarda el ultimo pronostico recibido del clima y vuelve a
        calcular la recomendacion de riego.

        Parametros:
            pronostico (list[dict]): pronostico diario de Open-Meteo
                (ver clima/open_meteo.py).

        Retorna:
            None
        """
        self.ultimo_pronostico = pronostico
        self._recalcular_simulacion()

    def _recalcular_simulacion(self):
        """
        Si ya se tiene tanto el estado hidrico actual como el
        pronostico del clima, ejecuta el simulador de escenarios,
        actualiza el texto de recomendacion y redibuja la grafica.

        Retorna:
            None
        """
        if self.ultimo_estado is None or not self.ultimo_pronostico:
            return

        parametros_cultivo = {"kc": self.ultimo_estado["kc_actual"]}

        resultado = simulador.simular_escenarios(self.ultimo_estado, self.ultimo_pronostico, parametros_cultivo)

        texto = simulador.generar_texto_recomendacion(resultado, self.ultimo_estado["deficit_mm"])
        self.label_recomendacion.setText(texto)

        self._dibujar_grafica(resultado)

    def _dibujar_grafica(self, resultado_simulacion):
        """
        Dibuja la grafica de balance hidrico: agua disponible en los
        ultimos 7 dias (datos historicos) y la proyeccion de los
        proximos 7 dias segun el escenario optimo encontrado.

        Parametros:
            resultado_simulacion (dict): resultado de
                simulador.simular_escenarios().

        Retorna:
            None
        """
        historico = gestor_db.obtener_estados_gemelo_ultimos_dias(dias=7)

        ejes = self.grafica.obtener_ejes()
        self.grafica.limpiar()

        # --- Datos historicos ---
        if historico:
            fechas_historicas = [registro["timestamp"] for registro in historico]
            agua_historica = [registro["agua_disponible_mm"] for registro in historico]
            ejes.plot(fechas_historicas, agua_historica, label="Historico (7 dias)", color="#2e7d32", marker="o")

        # --- Proyeccion futura segun el escenario optimo ---
        escenario_optimo = resultado_simulacion["escenario_optimo"]
        evolucion = resultado_simulacion["escenarios"][escenario_optimo]["evolucion_diaria"]

        hoy = datetime.now()
        fechas_futuras = [hoy + timedelta(days=indice + 1) for indice in range(len(evolucion))]

        # Conectamos el ultimo punto historico con el primer punto futuro, si hay historico
        if historico:
            fechas_futuras = [historico[-1]["timestamp"]] + fechas_futuras
            evolucion = [historico[-1]["agua_disponible_mm"]] + evolucion

        ejes.plot(
            fechas_futuras, evolucion,
            label=f"Proyeccion ({escenario_optimo})", color="#1565c0", marker="o", linestyle="--"
        )

        # --- Linea de capacidad util total ---
        agua_total_util = self.ultimo_estado["agua_total_util_mm"]
        ejes.axhline(y=agua_total_util, color="#9e9e9e", linestyle=":", label="Capacidad util")
        ejes.axhline(y=agua_total_util * 0.5, color="#c62828", linestyle=":", label="Umbral de estres (50%)")

        ejes.set_title("Balance hidrico: historico y proyeccion")
        ejes.set_ylabel("Agua disponible (mm)")
        ejes.legend(fontsize="small")
        ejes.tick_params(axis="x", rotation=30)

        self.grafica.redibujar()

    def _ejecutar_riego_recomendado(self):
        """
        Pide confirmacion al usuario y, si confirma, registra el evento
        de riego recomendado en la base de datos.

        IMPORTANTE: en el alcance actual del proyecto NO se envia
        ninguna orden real al PLC. Solo se simula la accion y se deja
        constancia en la tabla "eventos_riego" (ejecutado_en_plc=False).

        Retorna:
            None

        Efectos secundarios:
            Escribe una fila en la tabla "eventos_riego" si el usuario
            confirma.
        """
        if self.ultimo_estado is None:
            QMessageBox.information(
                self, "Sin datos",
                "Todavia no hay suficiente informacion para generar una recomendacion de riego.",
            )
            return

        deficit_mm = self.ultimo_estado["deficit_mm"]

        confirmado = mostrar_confirmacion(
            self,
            "Confirmar riego",
            f"¿Desea ejecutar el riego recomendado de aproximadamente {deficit_mm:.1f} mm?",
            texto_detallado=(
                "En el sistema real, esta accion enviaria una orden de apertura de "
                "valvula y encendido de bomba al PLC. En esta version del proyecto "
                "(alcance B), la accion solo se registra en la base de datos y NO "
                "se envia ninguna orden al LOGO!."
            ),
        )

        if not confirmado:
            return

        gestor_db.guardar_evento_riego(
            tipo="recomendado",
            zona="zona_1",
            volumen_mm=deficit_mm,
            duracion_minutos=None,
            confirmado_por_usuario=True,
            motivo=self.label_recomendacion.text(),
            ejecutado_en_plc=False,
        )

        QMessageBox.information(
            self,
            "Riego ejecutado (simulacion)",
            "Riego ejecutado en simulacion. En sistema real se enviaria orden al PLC.",
        )

        logger.info(f"Riego recomendado registrado en simulacion: {deficit_mm:.1f} mm")
