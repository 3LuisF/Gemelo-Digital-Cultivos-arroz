"""
Definicion de las tablas de la base de datos del Gemelo Digital.

Se usa SQLAlchemy con el estilo declarativo basico (cada tabla es una
clase de Python que hereda de "Base"). SQLAlchemy se encarga de crear
las tablas en SQLite a partir de estas clases.
"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from datetime import datetime

# Clase base de la cual heredan todas las tablas
Base = declarative_base()


class LecturaSensor(Base):
    """
    Guarda cada lectura de los sensores (ya sea que venga del PLC real
    o que haya sido ingresada manualmente desde la pestaña de Control
    Manual).
    """
    __tablename__ = "lecturas_sensores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    # Origen del dato: "plc" si vino del LOGO!, "manual" si lo escribio el usuario
    fuente = Column(String, nullable=False)

    temperatura = Column(Float)
    humedad_suelo = Column(Float)
    caudal = Column(Float)
    lluvia_acumulada = Column(Float)


class EstadoGemelo(Base):
    """
    Guarda el resultado del calculo del balance hidrico en un momento
    dado. Esta tabla se llena periodicamente por el HiloGemelo.
    """
    __tablename__ = "estado_gemelo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    agua_disponible_mm = Column(Float)
    evapotranspiracion_mm = Column(Float)
    deficit_hidrico_mm = Column(Float)
    etapa_fenologica = Column(String)
    kc_actual = Column(Float)
    dias_desde_siembra = Column(Integer)


class EventoRiego(Base):
    """
    Registra cada evento de riego, ya sea uno recomendado por el
    simulador y confirmado por el usuario, o uno realizado manualmente.

    IMPORTANTE: en el alcance B de este proyecto, "ejecutado_en_plc"
    siempre queda en False porque NO se envian ordenes reales de riego
    al PLC. Solo se simula y se deja constancia en esta tabla.
    """
    __tablename__ = "eventos_riego"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    # "recomendado" (sugerido por el gemelo) o "manual" (decidido por el usuario)
    tipo = Column(String, nullable=False)

    zona = Column(String)
    volumen_mm = Column(Float)
    duracion_minutos = Column(Float)
    confirmado_por_usuario = Column(Boolean, default=False)

    # Siempre False en el alcance actual del proyecto (no se controla el PLC real)
    ejecutado_en_plc = Column(Boolean, default=False)

    motivo = Column(String)


class AccionManual(Base):
    """
    Registra cada accion que el usuario realiza desde la pestaña de
    Control Manual (forzar una entrada o una salida del LOGO!).
    Sirve como bitacora/auditoria de lo que se hizo manualmente.
    """
    __tablename__ = "acciones_manuales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    # Componente afectado: "I1", "I2", ..., "Q1", "Q2", etc.
    componente = Column(String, nullable=False)

    valor_anterior = Column(String)
    valor_nuevo = Column(String)
    usuario = Column(String)


class ClimaPronostico(Base):
    """
    Guarda los pronosticos diarios obtenidos de la API de Open-Meteo.
    Cada fila es un dia de pronostico para una fecha futura, con la
    fecha en que se hizo la consulta.
    """
    __tablename__ = "clima_pronostico"

    id = Column(Integer, primary_key=True, autoincrement=True)

    fecha_consulta = Column(DateTime, default=datetime.now, nullable=False)
    fecha_pronostico = Column(DateTime, nullable=False)

    temp_max = Column(Float)
    temp_min = Column(Float)
    lluvia_mm = Column(Float)
    humedad_rel = Column(Float)
    et0_estimada = Column(Float)


class ConfiguracionCultivo(Base):
    """
    Guarda la configuracion del cultivo activo (tipo de cultivo, fecha
    de siembra, area sembrada). Normalmente solo deberia haber una fila
    con "activo=True" a la vez.
    """
    __tablename__ = "configuracion_cultivo"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # "arroz_secano" o "maiz" (debe coincidir con las claves de cultivos.yaml)
    tipo_cultivo = Column(String, nullable=False)
    fecha_siembra = Column(DateTime, nullable=False)
    area_hectareas = Column(Float)
    activo = Column(Boolean, default=True)
