"""
Modulo de comunicacion con el PLC Siemens LOGO! 8 (0BA8) usando la
libreria python-snap7.

Este modulo expone la clase ConexionPLC que:
  - Se conecta al LOGO! por Ethernet (IP, rack, slot configurables).
  - Lee las entradas analogicas (AI1-AI4) y el estado de las salidas
    (Q1-Q4) desde la zona de memoria VM.
  - Escribe el estado de las salidas Q1, Q2, Q3 (para riego/bomba).
  - Si no logra conectarse, queda en "modo simulado": el resto del
    programa puede seguir funcionando, solo que las lecturas del PLC
    no estaran disponibles (se deben usar datos manuales/BD).

NOTA IMPORTANTE (alcance B del proyecto):
    Aunque este modulo SI permite escribir las salidas Q1/Q2/Q3, en la
    interfaz NO se usa esta funcion para ejecutar riegos automaticos
    reales. El boton "Ejecutar riego recomendado" solo simula la accion
    y la registra en la base de datos. Ver pestana_gemelo.py.
"""

import struct

from src.utilidades.logger import obtener_logger
from src.plc import mapeo_memoria as mapa

logger = obtener_logger("plc")

# Intentamos importar snap7. Si la libreria no esta instalada o no es
# compatible con esta version de Python/Windows, el programa NO debe
# caerse: simplemente queda en modo simulado.
try:
    import snap7
    SNAP7_DISPONIBLE = True
except Exception as error:
    logger.warning(f"No se pudo importar python-snap7 ({error}). El sistema funcionara en modo simulado.")
    SNAP7_DISPONIBLE = False


# Numero de "DB" que usa python-snap7 para acceder a la zona VM del LOGO!
DB_VM_LOGO = 1


class ConexionPLC:
    """
    Representa la conexion con el LOGO! 8. Guarda la configuracion de
    red y el estado actual de la conexion (conectado o no).
    """

    def __init__(self, ip, rack=0, slot=1, timeout_ms=2000):
        """
        Guarda los datos de conexion. NO se conecta todavia (eso lo
        hace el metodo conectar()).

        Parametros:
            ip (str): direccion IP del LOGO!.
            rack (int): numero de rack (siempre 0 en LOGO!).
            slot (int): numero de slot (1 para LOGO! 0BA8).
            timeout_ms (int): tiempo de espera para la conexion, en ms.
        """
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.timeout_ms = timeout_ms

        self.cliente = None
        self.conectado = False

    def conectar(self):
        """
        Intenta conectarse al LOGO! 8 por Ethernet.

        Retorna:
            bool: True si la conexion fue exitosa, False en caso
            contrario (incluyendo el caso en que snap7 no esta
            disponible).

        Efectos secundarios:
            Crea/guarda el objeto cliente de snap7 y actualiza
            self.conectado. Escribe en el log el resultado.
        """
        if not SNAP7_DISPONIBLE:
            self.conectado = False
            return False

        try:
            self.cliente = snap7.client.Client()
            self.cliente.set_connection_type(3)  # tipo de conexion PG/OP basico para LOGO!
            self.cliente.connect(self.ip, self.rack, self.slot)

            self.conectado = self.cliente.get_connected()

            if self.conectado:
                logger.info(f"Conectado al LOGO! 8 en {self.ip}")
            else:
                logger.warning(f"No se pudo conectar al LOGO! 8 en {self.ip}")

            return self.conectado

        except Exception as error:
            logger.warning(f"Error al conectar con el LOGO! 8 en {self.ip}: {error}")
            self.conectado = False
            return False

    def desconectar(self):
        """
        Cierra la conexion con el LOGO! si esta abierta.

        Retorna:
            None

        Efectos secundarios:
            Cierra el socket de comunicacion con el PLC.
        """
        if self.cliente is not None and self.conectado:
            try:
                self.cliente.disconnect()
                logger.info("Conexion con el LOGO! 8 cerrada.")
            except Exception as error:
                logger.warning(f"Error al desconectar del LOGO! 8: {error}")

        self.conectado = False

    def reconectar_si_es_necesario(self):
        """
        Si la conexion se perdio, intenta reconectarse automaticamente.

        Retorna:
            bool: True si esta (o quedo) conectado, False si sigue sin
            poder conectarse.

        Efectos secundarios:
            Puede crear una nueva conexion al PLC.
        """
        if self.conectado:
            return True

        logger.info("Intentando reconectar con el LOGO! 8...")
        return self.conectar()

    def leer_entradas_analogicas(self):
        """
        Lee las 4 entradas analogicas (AI1-AI4) del LOGO! desde la
        zona de memoria VM.

        Retorna:
            dict con las llaves "AI1", "AI2", "AI3", "AI4" y sus
            valores crudos (0-1000), o None si no se pudo leer
            (por ejemplo, si esta en modo simulado).

        Efectos secundarios:
            Lee datos del PLC por la red. Si la lectura falla, marca
            la conexion como perdida (self.conectado = False).
        """
        if not self.reconectar_si_es_necesario():
            return None

        try:
            # Leemos 8 bytes desde la direccion donde empiezan las AI
            # (4 entradas analogicas x 2 bytes cada una)
            datos = self.cliente.db_read(DB_VM_LOGO, mapa.DIRECCION_VM_AI1_CAUDAL, 8)

            ai1 = struct.unpack_from(">H", datos, 0)[0]
            ai2 = struct.unpack_from(">H", datos, 2)[0]
            ai3 = struct.unpack_from(">H", datos, 4)[0]
            ai4 = struct.unpack_from(">H", datos, 6)[0]

            return {"AI1": ai1, "AI2": ai2, "AI3": ai3, "AI4": ai4}

        except Exception as error:
            logger.warning(f"Error leyendo entradas analogicas del LOGO!: {error}")
            self.conectado = False
            return None

    def leer_salidas_digitales(self):
        """
        Lee el estado actual de las salidas Q1-Q4 del LOGO!.

        Retorna:
            dict con las llaves "Q1", "Q2", "Q3", "Q4" y valores
            booleanos, o None si no se pudo leer.

        Efectos secundarios:
            Lee datos del PLC por la red. Si la lectura falla, marca
            la conexion como perdida (self.conectado = False).
        """
        if not self.reconectar_si_es_necesario():
            return None

        try:
            datos = self.cliente.db_read(DB_VM_LOGO, mapa.DIRECCION_VM_SALIDAS, 1)
            byte_salidas = datos[0]

            return {
                "Q1": bool(byte_salidas & (1 << mapa.BIT_Q1)),
                "Q2": bool(byte_salidas & (1 << mapa.BIT_Q2)),
                "Q3": bool(byte_salidas & (1 << mapa.BIT_Q3)),
                "Q4": bool(byte_salidas & (1 << mapa.BIT_Q4)),
            }

        except Exception as error:
            logger.warning(f"Error leyendo salidas digitales del LOGO!: {error}")
            self.conectado = False
            return None

    def escribir_salida_digital(self, nombre_salida, encender):
        """
        Escribe (forza) el estado de una salida digital del LOGO!
        (Q1, Q2, Q3 o Q4).

        Parametros:
            nombre_salida (str): "Q1", "Q2", "Q3" o "Q4".
            encender (bool): True para activar la salida, False para
                apagarla.

        Retorna:
            bool: True si se escribio correctamente, False si hubo
            algun error o si esta en modo simulado.

        Efectos secundarios:
            Escribe en la memoria del PLC (cambia el estado fisico de
            la salida correspondiente).
        """
        if not self.reconectar_si_es_necesario():
            return False

        bits_salidas = {
            "Q1": mapa.BIT_Q1,
            "Q2": mapa.BIT_Q2,
            "Q3": mapa.BIT_Q3,
            "Q4": mapa.BIT_Q4,
        }

        if nombre_salida not in bits_salidas:
            logger.error(f"Nombre de salida invalido: {nombre_salida}")
            return False

        try:
            # Leemos el byte actual de salidas para no pisar las otras salidas
            datos = bytearray(self.cliente.db_read(DB_VM_LOGO, mapa.DIRECCION_VM_SALIDAS, 1))

            bit = bits_salidas[nombre_salida]
            if encender:
                datos[0] |= (1 << bit)
            else:
                datos[0] &= ~(1 << bit)

            self.cliente.db_write(DB_VM_LOGO, mapa.DIRECCION_VM_SALIDAS, datos)
            logger.info(f"Salida {nombre_salida} escrita como {'ON' if encender else 'OFF'}")
            return True

        except Exception as error:
            logger.warning(f"Error escribiendo salida {nombre_salida} en el LOGO!: {error}")
            self.conectado = False
            return False
