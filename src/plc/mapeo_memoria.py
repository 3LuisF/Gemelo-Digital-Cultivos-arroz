"""
Mapeo de memoria del PLC Siemens LOGO! 8 (0BA8) y funciones de
conversion de las señales analogicas (0-10V) a valores fisicos reales.

MAPEO DE ENTRADAS/SALIDAS USADO EN ESTE PROYECTO
-------------------------------------------------
  I1 (AI1 en LOGO!Soft Comfort) -> Caudalimetro       (simulado, manual)
  I2 (AI2 en LOGO!Soft Comfort) -> Pluviometro        (simulado, manual)
  I3 (AI3 en LOGO!Soft Comfort) -> Sensor PT100 (temperatura, REAL)
  I4 (AI4 en LOGO!Soft Comfort) -> Humedad del suelo  (simulado, manual)

  Q1 -> Valvula de riego zona 1
  Q2 -> Valvula de riego zona 2
  Q3 -> Bomba principal
  Q4 -> Reserva (no usado)

DIRECCIONES DE MEMORIA (VM)
-------------------------------------------------
El LOGO! 8 expone sus entradas analogicas (AI) en la memoria VM como
palabras (2 bytes) sin signo, con un rango de 0 a 1000 que representa
la señal de 0V a 10V. Estas direcciones se configuran desde
LOGO!Soft Comfort (bloques "VM mapping"). Los valores de abajo son los
que se usaron al programar el LOGO! para este proyecto; si se cambia
la configuracion del LOGO!, hay que actualizar estos numeros.
"""

# Direcciones VM (en bytes) donde el LOGO! deja cada entrada analogica.
# Cada entrada ocupa 2 bytes (un "word").
DIRECCION_VM_AI1_CAUDAL = 0
DIRECCION_VM_AI2_LLUVIA = 2
DIRECCION_VM_AI3_TEMPERATURA = 4
DIRECCION_VM_AI4_HUMEDAD_SUELO = 6

# Direcciones de bit (en la zona VM) donde el LOGO! deja el estado de
# cada salida digital (Q1-Q4).
DIRECCION_VM_SALIDAS = 8  # byte donde estan los bits de Q1..Q4
BIT_Q1 = 0
BIT_Q2 = 1
BIT_Q3 = 2
BIT_Q4 = 3

# Rango crudo que entrega el LOGO! para una entrada analogica de 0-10V
VALOR_CRUDO_MINIMO = 0
VALOR_CRUDO_MAXIMO = 1000


def convertir_valor_crudo_a_real(valor_crudo, valor_real_min, valor_real_max):
    """
    Convierte un valor crudo del LOGO! (0 a 1000, que representa 0-10V)
    a un valor fisico real usando una escala lineal.

    Parametros:
        valor_crudo (int): valor leido del LOGO! (esperado entre 0 y 1000).
        valor_real_min (float): valor fisico que corresponde a 0V.
        valor_real_max (float): valor fisico que corresponde a 10V.

    Retorna:
        float: valor convertido a unidades reales (ej: grados Celsius,
        porcentaje, L/min, mm/h segun el sensor).
    """
    # Nos aseguramos de no salirnos del rango esperado (0-1000)
    valor_crudo = max(VALOR_CRUDO_MINIMO, min(VALOR_CRUDO_MAXIMO, valor_crudo))

    proporcion = (valor_crudo - VALOR_CRUDO_MINIMO) / (VALOR_CRUDO_MAXIMO - VALOR_CRUDO_MINIMO)
    valor_real = valor_real_min + proporcion * (valor_real_max - valor_real_min)

    return round(valor_real, 2)


def convertir_temperatura_pt100(valor_crudo, temperatura_min, temperatura_max):
    """
    Convierte la lectura cruda de la entrada AI3 (sensor PT100 conectado
    via transmisor 0-10V) a grados Celsius.

    Parametros:
        valor_crudo (int): valor leido del LOGO! en AI3.
        temperatura_min (float): temperatura correspondiente a 0V
            (configurable en settings.yaml, por defecto -20°C).
        temperatura_max (float): temperatura correspondiente a 10V
            (configurable en settings.yaml, por defecto 80°C).

    Retorna:
        float: temperatura en grados Celsius.
    """
    return convertir_valor_crudo_a_real(valor_crudo, temperatura_min, temperatura_max)


def convertir_humedad_suelo(valor_crudo, humedad_min=0.0, humedad_max=100.0):
    """
    Convierte la lectura cruda de la entrada AI4 (humedad de suelo,
    sensor simulado) a porcentaje de humedad (0-100%).

    Parametros:
        valor_crudo (int): valor leido del LOGO! en AI4.
        humedad_min (float): humedad correspondiente a 0V (default 0%).
        humedad_max (float): humedad correspondiente a 10V (default 100%).

    Retorna:
        float: porcentaje de humedad del suelo.
    """
    return convertir_valor_crudo_a_real(valor_crudo, humedad_min, humedad_max)


def convertir_caudal(valor_crudo, caudal_min=0.0, caudal_max=100.0):
    """
    Convierte la lectura cruda de la entrada AI1 (caudalimetro, sensor
    simulado) a litros por minuto.

    Parametros:
        valor_crudo (int): valor leido del LOGO! en AI1.
        caudal_min (float): caudal correspondiente a 0V (default 0 L/min).
        caudal_max (float): caudal correspondiente a 10V (default 100 L/min).

    Retorna:
        float: caudal en L/min.
    """
    return convertir_valor_crudo_a_real(valor_crudo, caudal_min, caudal_max)


def convertir_lluvia(valor_crudo, lluvia_min=0.0, lluvia_max=50.0):
    """
    Convierte la lectura cruda de la entrada AI2 (pluviometro, sensor
    simulado) a milimetros por hora.

    Parametros:
        valor_crudo (int): valor leido del LOGO! en AI2.
        lluvia_min (float): lluvia correspondiente a 0V (default 0 mm/h).
        lluvia_max (float): lluvia correspondiente a 10V (default 50 mm/h).

    Retorna:
        float: lluvia en mm/h.
    """
    return convertir_valor_crudo_a_real(valor_crudo, lluvia_min, lluvia_max)
