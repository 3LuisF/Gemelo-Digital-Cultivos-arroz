"""
Hilos de fondo (QThread) usados por la interfaz para no congelar la
ventana mientras se lee el PLC, se consulta el clima o se recalcula el
estado del gemelo digital.

Cada hilo corre un ciclo "while" que se repite cada cierto tiempo y
emite una señal (pyqtSignal) con los datos nuevos. La ventana
principal conecta esas señales con los metodos que actualizan la
interfaz.
"""

import time
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal

from src.database import gestor_db
from src.plc import mapeo_memoria as mapa
from src.clima import open_meteo
from src.gemelo import cultivo, balance_hidrico, evapotranspiracion
from src.utilidades.logger import obtener_logger

logger = obtener_logger("hilos")


class HiloLecturaPLC(QThread):
    """
    Hilo que lee periodicamente las entradas analogicas y las salidas
    digitales del LOGO! 8. Si el PLC no esta disponible, usa la ultima
    lectura manual guardada en la base de datos (modo simulado).
    """

    # Señal que se emite cada vez que hay una lectura nueva
    nueva_lectura = pyqtSignal(dict)

    def __init__(self, conexion_plc, settings, intervalo_segundos=5):
        """
        Parametros:
            conexion_plc (ConexionPLC): objeto de conexion al LOGO!.
            settings (dict): configuracion general (incluye las
                escalas de conversion de las entradas analogicas).
            intervalo_segundos (int): cada cuanto se hace una lectura.
        """
        super().__init__()
        self.conexion_plc = conexion_plc
        self.settings = settings
        self.intervalo_segundos = intervalo_segundos
        self._activo = True

    def detener(self):
        """
        Marca el hilo para que termine su ciclo en la proxima vuelta.

        Retorna:
            None
        """
        self._activo = False

    def run(self):
        """
        Ciclo principal del hilo. Se ejecuta automaticamente cuando se
        llama a .start(). Lee el PLC (o la BD si esta offline), guarda
        la lectura y emite la señal "nueva_lectura".

        Retorna:
            None

        Efectos secundarios:
            Lee del PLC, escribe en la base de datos (tabla
            lecturas_sensores).
        """
        escalas = self.settings.get("escalas_entradas", {})

        while self._activo:
            lectura = self._leer_una_vez(escalas)
            self.nueva_lectura.emit(lectura)
            time.sleep(self.intervalo_segundos)

    def leer_y_emitir_una_vez(self):
        """
        Hace una lectura inmediata (sin esperar el intervalo normal) y
        emite la señal "nueva_lectura". Se usa cuando el usuario
        presiona el boton "Actualizar ahora" en la pestaña de Estado.

        Retorna:
            None

        Efectos secundarios:
            Igual que _leer_una_vez(): lee el PLC y guarda en la BD.
        """
        escalas = self.settings.get("escalas_entradas", {})
        lectura = self._leer_una_vez(escalas)
        self.nueva_lectura.emit(lectura)

    def _leer_una_vez(self, escalas):
        """
        Hace una lectura completa: intenta leer del PLC, y si no se
        puede, usa la ultima lectura manual de la base de datos.

        Parametros:
            escalas (dict): rangos de conversion de las entradas
                analogicas (de settings.yaml).

        Retorna:
            dict con las llaves "timestamp", "fuente", "conectado",
            "temperatura", "humedad_suelo", "caudal",
            "lluvia_acumulada" y "salidas" (dict Q1-Q4 o None).
        """
        entradas = self.conexion_plc.leer_entradas_analogicas()

        if entradas is not None:
            # El PLC esta conectado: convertimos las señales crudas a unidades reales
            temperatura = mapa.convertir_temperatura_pt100(
                entradas["AI3"],
                escalas.get("temperatura_min", -20.0),
                escalas.get("temperatura_max", 80.0),
            )
            humedad_suelo = mapa.convertir_humedad_suelo(
                entradas["AI4"],
                escalas.get("humedad_suelo_min", 0.0),
                escalas.get("humedad_suelo_max", 100.0),
            )
            caudal = mapa.convertir_caudal(
                entradas["AI1"],
                escalas.get("caudal_min", 0.0),
                escalas.get("caudal_max", 100.0),
            )
            lluvia = mapa.convertir_lluvia(
                entradas["AI2"],
                escalas.get("lluvia_min", 0.0),
                escalas.get("lluvia_max", 50.0),
            )
            fuente = "plc"
            salidas = self.conexion_plc.leer_salidas_digitales()

        else:
            # Modo simulado: usamos la ultima lectura manual guardada en la BD
            ultima = gestor_db.obtener_ultima_lectura()

            if ultima is not None:
                temperatura = ultima["temperatura"]
                humedad_suelo = ultima["humedad_suelo"]
                caudal = ultima["caudal"]
                lluvia = ultima["lluvia_acumulada"]
            else:
                temperatura = None
                humedad_suelo = None
                caudal = None
                lluvia = None

            fuente = "manual"
            salidas = None

        gestor_db.guardar_lectura_sensor(
            fuente=fuente,
            temperatura=temperatura,
            humedad_suelo=humedad_suelo,
            caudal=caudal,
            lluvia_acumulada=lluvia,
        )

        return {
            "timestamp": datetime.now(),
            "fuente": fuente,
            "conectado": self.conexion_plc.conectado,
            "temperatura": temperatura,
            "humedad_suelo": humedad_suelo,
            "caudal": caudal,
            "lluvia_acumulada": lluvia,
            "salidas": salidas,
        }


class HiloClima(QThread):
    """
    Hilo que consulta periodicamente el pronostico del clima en
    Open-Meteo y guarda los resultados en la base de datos.
    """

    # Señal que se emite cuando hay un pronostico nuevo
    nuevo_pronostico = pyqtSignal(list)

    def __init__(self, settings, intervalo_minutos=60):
        """
        Parametros:
            settings (dict): configuracion general (incluye latitud y
                longitud de la ubicacion del cultivo).
            intervalo_minutos (int): cada cuanto se consulta la API.
        """
        super().__init__()
        self.settings = settings
        self.intervalo_minutos = intervalo_minutos
        self._activo = True

    def detener(self):
        """
        Marca el hilo para que termine su ciclo en la proxima vuelta.

        Retorna:
            None
        """
        self._activo = False

    def run(self):
        """
        Ciclo principal del hilo. Consulta Open-Meteo, emite la señal
        "nuevo_pronostico" y espera el intervalo configurado.

        Retorna:
            None

        Efectos secundarios:
            Hace peticiones HTTP y escribe en la base de datos (tabla
            clima_pronostico).
        """
        ubicacion = self.settings.get("ubicacion", {})
        latitud = ubicacion.get("latitud", 8.7479)
        longitud = ubicacion.get("longitud", -75.8814)

        segundos_totales_espera = self.intervalo_minutos * 60

        while self._activo:
            pronostico = open_meteo.obtener_pronostico(latitud, longitud, dias=7)
            self.nuevo_pronostico.emit(pronostico)

            # Esperamos el intervalo, pero revisando cada segundo si nos pidieron parar
            segundos_esperados = 0
            while self._activo and segundos_esperados < segundos_totales_espera:
                time.sleep(1)
                segundos_esperados += 1


class HiloGemelo(QThread):
    """
    Hilo que recalcula periodicamente el estado hidrico del cultivo
    (balance hidrico) usando la ultima lectura de sensores y el
    pronostico del clima, y guarda el resultado en la base de datos.
    """

    # Señal que se emite cada vez que se recalcula el estado del gemelo
    nuevo_estado = pyqtSignal(dict)

    def __init__(self, settings, intervalo_segundos=30):
        """
        Parametros:
            settings (dict): configuracion general (incluye latitud y
                longitud, usadas como respaldo para calcular ET0).
            intervalo_segundos (int): cada cuanto se recalcula el estado.
        """
        super().__init__()
        self.settings = settings
        self.intervalo_segundos = intervalo_segundos
        self._activo = True

    def detener(self):
        """
        Marca el hilo para que termine su ciclo en la proxima vuelta.

        Retorna:
            None
        """
        self._activo = False

    def run(self):
        """
        Ciclo principal del hilo. Calcula el estado hidrico actual y
        emite la señal "nuevo_estado".

        Retorna:
            None

        Efectos secundarios:
            Lee de la base de datos (lecturas, pronostico, configuracion
            de cultivo) y escribe en la base de datos (tabla
            estado_gemelo).
        """
        from src.utilidades import configuracion as config_utils

        while self._activo:
            estado = self._calcular_estado()
            if estado is not None:
                self.nuevo_estado.emit(estado)

            time.sleep(self.intervalo_segundos)

    def _calcular_estado(self):
        """
        Hace un calculo completo del balance hidrico actual.

        Retorna:
            dict con el resultado del balance hidrico mas datos del
            cultivo (etapa, kc, dias desde siembra), o None si todavia
            no hay suficiente informacion (sin lectura de sensores o
            sin cultivo configurado).
        """
        from src.utilidades import configuracion as config_utils

        ultima_lectura = gestor_db.obtener_ultima_lectura()
        config_cultivo = gestor_db.obtener_configuracion_cultivo_activa()

        if ultima_lectura is None or config_cultivo is None:
            return None

        if ultima_lectura["humedad_suelo"] is None:
            return None

        # --- Datos del cultivo (etapa fenologica y Kc actuales) ---
        dias_desde_siembra = cultivo.calcular_dias_desde_siembra(
            config_cultivo["fecha_siembra"], datetime.now()
        )
        etapa = cultivo.obtener_etapa_actual(config_cultivo["tipo_cultivo"], dias_desde_siembra)
        profundidad_raiz_m = cultivo.obtener_profundidad_raiz(config_cultivo["tipo_cultivo"])

        # --- ET0 del dia: preferimos la del pronostico de Open-Meteo ---
        et0_hoy = self._obtener_et0_hoy()

        # --- Parametros del suelo ---
        parametros_suelo = config_utils.cargar_suelo()

        lecturas = {
            "humedad_suelo": ultima_lectura["humedad_suelo"],
            "et0": et0_hoy,
        }
        parametros_cultivo = {
            "kc": etapa["kc"],
            "profundidad_raiz_m": profundidad_raiz_m,
        }

        estado_hidrico = balance_hidrico.calcular_estado_hidrico(lecturas, parametros_cultivo, parametros_suelo)

        gestor_db.guardar_estado_gemelo(
            agua_disponible_mm=estado_hidrico["agua_disponible_mm"],
            evapotranspiracion_mm=estado_hidrico["evapotranspiracion_mm"],
            deficit_hidrico_mm=estado_hidrico["deficit_mm"],
            etapa_fenologica=etapa["nombre"],
            kc_actual=etapa["kc"],
            dias_desde_siembra=dias_desde_siembra,
        )

        resultado = dict(estado_hidrico)
        resultado["etapa_fenologica"] = etapa["nombre"]
        resultado["kc_actual"] = etapa["kc"]
        resultado["dias_desde_siembra"] = dias_desde_siembra
        resultado["tipo_cultivo"] = config_cultivo["tipo_cultivo"]

        return resultado

    def _obtener_et0_hoy(self):
        """
        Obtiene la evapotranspiracion de referencia (ET0) de hoy.
        Primero intenta usar el dato del pronostico de Open-Meteo
        guardado en la base de datos. Si no hay pronostico disponible,
        calcula una ET0 aproximada con el metodo Penman-Monteith usando
        valores de respaldo (temperatura del ultimo registro y humedad
        relativa tipica de la zona).

        Retorna:
            float: ET0 estimada en mm/dia.
        """
        pronostico = gestor_db.obtener_ultimo_pronostico(dias=1)

        if pronostico and pronostico[0].get("et0_estimada") is not None:
            return pronostico[0]["et0_estimada"]

        # --- Calculo de respaldo (sin pronostico disponible) ---
        ultima_lectura = gestor_db.obtener_ultima_lectura()
        ubicacion = self.settings.get("ubicacion", {})
        latitud = ubicacion.get("latitud", 8.7479)

        temperatura = ultima_lectura["temperatura"] if ultima_lectura and ultima_lectura["temperatura"] is not None else 28.0

        # Sin datos de tmax/tmin reales, usamos +-3°C alrededor de la lectura actual
        temp_max = temperatura + 3
        temp_min = temperatura - 3
        humedad_rel = 75.0  # humedad relativa tipica de la zona del Sinu

        et0 = evapotranspiracion.calcular_et0_penman_monteith(
            temp_max=temp_max,
            temp_min=temp_min,
            humedad_rel_media=humedad_rel,
            fecha=datetime.now(),
            latitud=latitud,
        )

        return et0
