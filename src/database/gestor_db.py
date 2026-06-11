"""
Funciones para conectarse a la base de datos SQLite y hacer
operaciones basicas (CRUD: Crear, Leer, Actualizar, Borrar).

Este modulo usa SQLAlchemy de forma sencilla: se crea un "engine" que
apunta al archivo .db y una fabrica de sesiones (SessionLocal). Cada
funcion abre su propia sesion, hace su trabajo y la cierra.
"""

from datetime import datetime

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from src.database.modelos import (
    Base,
    LecturaSensor,
    EstadoGemelo,
    EventoRiego,
    AccionManual,
    ClimaPronostico,
    ConfiguracionCultivo,
)
from src.utilidades.logger import obtener_logger

logger = obtener_logger("database")

# Estas dos variables se llenan cuando se llama a inicializar_base_datos()
_engine = None
SessionLocal = None


def inicializar_base_datos(ruta_db):
    """
    Crea el "engine" de SQLAlchemy apuntando al archivo SQLite indicado
    y crea todas las tablas si todavia no existen.

    Parametros:
        ruta_db (str): ruta del archivo .db (ejemplo: "gemelo.db")

    Retorna:
        None

    Efectos secundarios:
        - Crea el archivo .db si no existe.
        - Crea las tablas definidas en modelos.py si no existen.
    """
    global _engine, SessionLocal

    # echo=False para no llenar la consola con el SQL generado
    _engine = create_engine(f"sqlite:///{ruta_db}", echo=False)
    SessionLocal = sessionmaker(bind=_engine)

    Base.metadata.create_all(_engine)
    logger.info(f"Base de datos inicializada en: {ruta_db}")


# ---------------------------------------------------------------------
# LECTURAS DE SENSORES
# ---------------------------------------------------------------------

def guardar_lectura_sensor(fuente, temperatura=None, humedad_suelo=None,
                            caudal=None, lluvia_acumulada=None):
    """
    Inserta una nueva fila en la tabla "lecturas_sensores".

    Parametros:
        fuente (str): "plc" o "manual".
        temperatura, humedad_suelo, caudal, lluvia_acumulada (float):
            valores de los sensores. Pueden quedar en None si no se
            tiene el dato.

    Retorna:
        int: el id de la fila insertada.

    Efectos secundarios:
        Escribe una fila nueva en la base de datos.
    """
    sesion = SessionLocal()
    try:
        nueva_lectura = LecturaSensor(
            fuente=fuente,
            temperatura=temperatura,
            humedad_suelo=humedad_suelo,
            caudal=caudal,
            lluvia_acumulada=lluvia_acumulada,
        )
        sesion.add(nueva_lectura)
        sesion.commit()
        return nueva_lectura.id
    except Exception as error:
        sesion.rollback()
        logger.error(f"Error guardando lectura de sensor: {error}")
        return None
    finally:
        sesion.close()


def obtener_ultima_lectura():
    """
    Obtiene la lectura de sensores mas reciente.

    Retorna:
        dict con los valores de la lectura, o None si no hay ninguna
        lectura guardada todavia.
    """
    sesion = SessionLocal()
    try:
        lectura = (
            sesion.query(LecturaSensor)
            .order_by(desc(LecturaSensor.timestamp))
            .first()
        )
        if lectura is None:
            return None

        return {
            "id": lectura.id,
            "timestamp": lectura.timestamp,
            "fuente": lectura.fuente,
            "temperatura": lectura.temperatura,
            "humedad_suelo": lectura.humedad_suelo,
            "caudal": lectura.caudal,
            "lluvia_acumulada": lectura.lluvia_acumulada,
        }
    finally:
        sesion.close()


def obtener_lecturas_rango(fecha_inicio, fecha_fin):
    """
    Obtiene todas las lecturas de sensores entre dos fechas.

    Parametros:
        fecha_inicio (datetime): fecha/hora desde donde buscar.
        fecha_fin (datetime): fecha/hora hasta donde buscar.

    Retorna:
        list[dict]: lista de lecturas ordenadas por fecha (mas antigua
        primero).
    """
    sesion = SessionLocal()
    try:
        lecturas = (
            sesion.query(LecturaSensor)
            .filter(LecturaSensor.timestamp >= fecha_inicio)
            .filter(LecturaSensor.timestamp <= fecha_fin)
            .order_by(LecturaSensor.timestamp)
            .all()
        )

        resultado = []
        for lectura in lecturas:
            resultado.append({
                "id": lectura.id,
                "timestamp": lectura.timestamp,
                "fuente": lectura.fuente,
                "temperatura": lectura.temperatura,
                "humedad_suelo": lectura.humedad_suelo,
                "caudal": lectura.caudal,
                "lluvia_acumulada": lectura.lluvia_acumulada,
            })
        return resultado
    finally:
        sesion.close()


def obtener_ultimas_n_lecturas(n=50):
    """
    Obtiene las ultimas "n" lecturas de sensores, de la mas reciente
    a la mas antigua.

    Parametros:
        n (int): cantidad de lecturas a traer (por defecto 50).

    Retorna:
        list[dict]: lista de lecturas, la primera es la mas reciente.
    """
    sesion = SessionLocal()
    try:
        lecturas = (
            sesion.query(LecturaSensor)
            .order_by(desc(LecturaSensor.timestamp))
            .limit(n)
            .all()
        )

        resultado = []
        for lectura in lecturas:
            resultado.append({
                "id": lectura.id,
                "timestamp": lectura.timestamp,
                "fuente": lectura.fuente,
                "temperatura": lectura.temperatura,
                "humedad_suelo": lectura.humedad_suelo,
                "caudal": lectura.caudal,
                "lluvia_acumulada": lectura.lluvia_acumulada,
            })
        return resultado
    finally:
        sesion.close()


# ---------------------------------------------------------------------
# ESTADO DEL GEMELO (BALANCE HIDRICO)
# ---------------------------------------------------------------------

def guardar_estado_gemelo(agua_disponible_mm, evapotranspiracion_mm,
                           deficit_hidrico_mm, etapa_fenologica,
                           kc_actual, dias_desde_siembra):
    """
    Inserta una nueva fila en la tabla "estado_gemelo" con el resultado
    del calculo del balance hidrico.

    Parametros: ver columnas de la tabla EstadoGemelo en modelos.py.

    Retorna:
        int: id de la fila insertada.

    Efectos secundarios:
        Escribe una fila nueva en la base de datos.
    """
    sesion = SessionLocal()
    try:
        nuevo_estado = EstadoGemelo(
            agua_disponible_mm=agua_disponible_mm,
            evapotranspiracion_mm=evapotranspiracion_mm,
            deficit_hidrico_mm=deficit_hidrico_mm,
            etapa_fenologica=etapa_fenologica,
            kc_actual=kc_actual,
            dias_desde_siembra=dias_desde_siembra,
        )
        sesion.add(nuevo_estado)
        sesion.commit()
        return nuevo_estado.id
    except Exception as error:
        sesion.rollback()
        logger.error(f"Error guardando estado del gemelo: {error}")
        return None
    finally:
        sesion.close()


def obtener_ultimo_estado_gemelo():
    """
    Obtiene el ultimo calculo guardado del balance hidrico.

    Retorna:
        dict con los valores del estado, o None si todavia no se ha
        calculado nada.
    """
    sesion = SessionLocal()
    try:
        estado = (
            sesion.query(EstadoGemelo)
            .order_by(desc(EstadoGemelo.timestamp))
            .first()
        )
        if estado is None:
            return None

        return {
            "id": estado.id,
            "timestamp": estado.timestamp,
            "agua_disponible_mm": estado.agua_disponible_mm,
            "evapotranspiracion_mm": estado.evapotranspiracion_mm,
            "deficit_hidrico_mm": estado.deficit_hidrico_mm,
            "etapa_fenologica": estado.etapa_fenologica,
            "kc_actual": estado.kc_actual,
            "dias_desde_siembra": estado.dias_desde_siembra,
        }
    finally:
        sesion.close()


def obtener_estados_gemelo_ultimos_dias(dias=7):
    """
    Obtiene los estados del gemelo de los ultimos N dias, ordenados del
    mas antiguo al mas reciente. Se usa para graficar el balance
    hidrico historico.

    Parametros:
        dias (int): cantidad de dias hacia atras a consultar.

    Retorna:
        list[dict]: lista de estados ordenados por fecha ascendente.
    """
    from datetime import datetime, timedelta

    sesion = SessionLocal()
    try:
        fecha_limite = datetime.now() - timedelta(days=dias)
        estados = (
            sesion.query(EstadoGemelo)
            .filter(EstadoGemelo.timestamp >= fecha_limite)
            .order_by(EstadoGemelo.timestamp)
            .all()
        )

        resultado = []
        for estado in estados:
            resultado.append({
                "timestamp": estado.timestamp,
                "agua_disponible_mm": estado.agua_disponible_mm,
                "evapotranspiracion_mm": estado.evapotranspiracion_mm,
                "deficit_hidrico_mm": estado.deficit_hidrico_mm,
            })
        return resultado
    finally:
        sesion.close()


# ---------------------------------------------------------------------
# EVENTOS DE RIEGO
# ---------------------------------------------------------------------

def guardar_evento_riego(tipo, zona, volumen_mm, duracion_minutos,
                          confirmado_por_usuario, motivo,
                          ejecutado_en_plc=False):
    """
    Inserta un nuevo evento de riego en la tabla "eventos_riego".

    Parametros:
        tipo (str): "recomendado" o "manual".
        zona (str): nombre/identificador de la zona regada.
        volumen_mm (float): volumen de riego en milimetros.
        duracion_minutos (float): duracion estimada del riego.
        confirmado_por_usuario (bool): si el usuario confirmo la accion.
        motivo (str): texto explicando por que se hizo el riego.
        ejecutado_en_plc (bool): SIEMPRE debe quedar en False en el
            alcance actual del proyecto, ya que no se controla el PLC
            real para riego (ver modelos.py).

    Retorna:
        int: id de la fila insertada.

    Efectos secundarios:
        Escribe una fila nueva en la base de datos.
    """
    sesion = SessionLocal()
    try:
        nuevo_evento = EventoRiego(
            tipo=tipo,
            zona=zona,
            volumen_mm=volumen_mm,
            duracion_minutos=duracion_minutos,
            confirmado_por_usuario=confirmado_por_usuario,
            ejecutado_en_plc=False,  # No se envian ordenes reales al PLC (alcance B)
            motivo=motivo,
        )
        sesion.add(nuevo_evento)
        sesion.commit()
        logger.info(f"Evento de riego registrado: zona={zona}, volumen={volumen_mm}mm, motivo={motivo}")
        return nuevo_evento.id
    except Exception as error:
        sesion.rollback()
        logger.error(f"Error guardando evento de riego: {error}")
        return None
    finally:
        sesion.close()


# ---------------------------------------------------------------------
# ACCIONES MANUALES
# ---------------------------------------------------------------------

def guardar_accion_manual(componente, valor_anterior, valor_nuevo, usuario="usuario"):
    """
    Registra en la tabla "acciones_manuales" un cambio hecho a mano por
    el usuario desde la pestaña de Control Manual.

    Parametros:
        componente (str): "I1", "I2", ..., "Q1", "Q2", etc.
        valor_anterior: valor que tenia antes del cambio.
        valor_nuevo: valor nuevo que se aplico.
        usuario (str): nombre de quien hizo el cambio (por defecto "usuario").

    Retorna:
        int: id de la fila insertada.

    Efectos secundarios:
        Escribe una fila nueva en la base de datos.
    """
    sesion = SessionLocal()
    try:
        nueva_accion = AccionManual(
            componente=componente,
            valor_anterior=str(valor_anterior),
            valor_nuevo=str(valor_nuevo),
            usuario=usuario,
        )
        sesion.add(nueva_accion)
        sesion.commit()
        logger.info(f"Accion manual registrada: {componente} de {valor_anterior} a {valor_nuevo}")
        return nueva_accion.id
    except Exception as error:
        sesion.rollback()
        logger.error(f"Error guardando accion manual: {error}")
        return None
    finally:
        sesion.close()


# ---------------------------------------------------------------------
# PRONOSTICO DEL CLIMA
# ---------------------------------------------------------------------

def guardar_pronostico_clima(lista_dias):
    """
    Guarda en la tabla "clima_pronostico" una lista de pronosticos
    diarios obtenidos de Open-Meteo.

    Parametros:
        lista_dias (list[dict]): cada dict debe tener las llaves
            "fecha_pronostico", "temp_max", "temp_min", "lluvia_mm",
            "humedad_rel", "et0_estimada".

    Retorna:
        None

    Efectos secundarios:
        Escribe una fila nueva por cada elemento de la lista.
    """
    # Usamos la misma fecha_consulta para todas las filas de esta
    # consulta, asi obtener_ultimo_pronostico() puede recuperarlas
    # juntas como "el pronostico mas reciente". Si cada fila tomara
    # su propio datetime.now(), las marcas de tiempo quedarian
    # ligeramente distintas y solo se recuperaria una fila.
    fecha_consulta = datetime.now()

    sesion = SessionLocal()
    try:
        for dia in lista_dias:
            fila = ClimaPronostico(
                fecha_consulta=fecha_consulta,
                fecha_pronostico=dia["fecha_pronostico"],
                temp_max=dia.get("temp_max"),
                temp_min=dia.get("temp_min"),
                lluvia_mm=dia.get("lluvia_mm"),
                humedad_rel=dia.get("humedad_rel"),
                et0_estimada=dia.get("et0_estimada"),
            )
            sesion.add(fila)
        sesion.commit()
    except Exception as error:
        sesion.rollback()
        logger.error(f"Error guardando pronostico de clima: {error}")
    finally:
        sesion.close()


def obtener_ultimo_pronostico(dias=7):
    """
    Obtiene el pronostico mas reciente guardado en la base de datos
    (segun la fecha de consulta mas alta).

    Parametros:
        dias (int): cantidad maxima de dias de pronostico a devolver.

    Retorna:
        list[dict]: lista de pronosticos diarios, o lista vacia si no
        hay nada guardado.
    """
    sesion = SessionLocal()
    try:
        # Buscamos la fecha de consulta mas reciente
        ultima_consulta = (
            sesion.query(ClimaPronostico.fecha_consulta)
            .order_by(desc(ClimaPronostico.fecha_consulta))
            .first()
        )
        if ultima_consulta is None:
            return []

        fecha_consulta = ultima_consulta[0]

        pronosticos = (
            sesion.query(ClimaPronostico)
            .filter(ClimaPronostico.fecha_consulta == fecha_consulta)
            .order_by(ClimaPronostico.fecha_pronostico)
            .limit(dias)
            .all()
        )

        resultado = []
        for dia in pronosticos:
            resultado.append({
                "fecha_pronostico": dia.fecha_pronostico,
                "temp_max": dia.temp_max,
                "temp_min": dia.temp_min,
                "lluvia_mm": dia.lluvia_mm,
                "humedad_rel": dia.humedad_rel,
                "et0_estimada": dia.et0_estimada,
            })
        return resultado
    finally:
        sesion.close()


# ---------------------------------------------------------------------
# CONFIGURACION DEL CULTIVO
# ---------------------------------------------------------------------

def guardar_configuracion_cultivo(tipo_cultivo, fecha_siembra, area_hectareas):
    """
    Guarda una nueva configuracion de cultivo y la marca como activa.
    Cualquier configuracion anterior se marca como inactiva (activo=False).

    Parametros:
        tipo_cultivo (str): "arroz_secano" o "maiz".
        fecha_siembra (datetime): fecha en que se sembro.
        area_hectareas (float): area sembrada en hectareas.

    Retorna:
        int: id de la fila insertada.

    Efectos secundarios:
        Escribe una fila nueva y actualiza las anteriores.
    """
    sesion = SessionLocal()
    try:
        # Desactivamos cualquier configuracion anterior
        sesion.query(ConfiguracionCultivo).filter(
            ConfiguracionCultivo.activo == True  # noqa: E712
        ).update({"activo": False})

        nueva_config = ConfiguracionCultivo(
            tipo_cultivo=tipo_cultivo,
            fecha_siembra=fecha_siembra,
            area_hectareas=area_hectareas,
            activo=True,
        )
        sesion.add(nueva_config)
        sesion.commit()
        logger.info(f"Nueva configuracion de cultivo guardada: {tipo_cultivo}, siembra={fecha_siembra}")
        return nueva_config.id
    except Exception as error:
        sesion.rollback()
        logger.error(f"Error guardando configuracion de cultivo: {error}")
        return None
    finally:
        sesion.close()


def obtener_configuracion_cultivo_activa():
    """
    Obtiene la configuracion de cultivo que esta marcada como activa.

    Retorna:
        dict con los datos del cultivo activo, o None si no hay
        ninguna configuracion guardada todavia.
    """
    sesion = SessionLocal()
    try:
        config = (
            sesion.query(ConfiguracionCultivo)
            .filter(ConfiguracionCultivo.activo == True)  # noqa: E712
            .order_by(desc(ConfiguracionCultivo.id))
            .first()
        )
        if config is None:
            return None

        return {
            "id": config.id,
            "tipo_cultivo": config.tipo_cultivo,
            "fecha_siembra": config.fecha_siembra,
            "area_hectareas": config.area_hectareas,
            "activo": config.activo,
        }
    finally:
        sesion.close()
