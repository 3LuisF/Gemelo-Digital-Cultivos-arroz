"""
Simulador de escenarios de riego.

A partir del estado hidrico actual del suelo y el pronostico del clima
para los proximos dias, se simulan 3 escenarios posibles:

  1. "no_regar": no se aplica riego, solo se usa la lluvia pronosticada.
  2. "regar_ahora": se aplica el deficit actual como riego inmediato (dia 1).
  3. "regar_diferido": se aplica el mismo riego, pero en el dia 2.

Para cada escenario se calcula cuantos dias el cultivo quedaria en
estres hidrico y cuanta agua total se uso. Al final se elige el
escenario "optimo": el que tenga 0 dias de estres usando la menor
cantidad de agua. Si ningun escenario logra 0 dias de estres, se elige
el que tenga menos dias de estres (y, en caso de empate, el que use
menos agua).
"""

from src.gemelo.balance_hidrico import actualizar_balance_diario

# Nombres de los escenarios, en el orden en que se simulan
ESCENARIO_NO_REGAR = "no_regar"
ESCENARIO_REGAR_AHORA = "regar_ahora"
ESCENARIO_REGAR_DIFERIDO = "regar_diferido"


def _simular_un_escenario(agua_inicial_mm, agua_total_util_mm, kc, pronostico_7dias, plan_riego_mm):
    """
    Simula la evolucion del agua del suelo dia a dia durante el
    pronostico, aplicando el plan de riego indicado.

    Parametros:
        agua_inicial_mm (float): agua disponible en el suelo al
            iniciar la simulacion (dia 0).
        agua_total_util_mm (float): capacidad maxima de agua util del
            suelo, en mm.
        kc (float): coeficiente de cultivo (se asume constante durante
            los dias simulados, ya que es una ventana corta de 7 dias).
        pronostico_7dias (list[dict]): cada elemento debe tener las
            llaves "lluvia_mm" y "et0_estimada".
        plan_riego_mm (list[float]): lista con el riego (en mm) a
            aplicar cada dia. Debe tener la misma longitud que
            pronostico_7dias.

    Retorna:
        dict con las llaves:
            - "dias_estres": cantidad de dias en que el agua disponible
              quedo por debajo del 50% del agua util total.
            - "agua_total_usada_mm": suma del riego aplicado en todos
              los dias.
            - "balance_final_mm": agua disponible al final del periodo
              simulado.
            - "evolucion_diaria": lista con el agua disponible (mm) al
              final de cada dia, util para graficar.
    """
    agua_actual_mm = agua_inicial_mm
    dias_estres = 0
    agua_total_usada_mm = 0.0
    evolucion_diaria = []

    for indice, dia_pronostico in enumerate(pronostico_7dias):
        lluvia_mm = dia_pronostico.get("lluvia_mm") or 0.0
        et0_dia = dia_pronostico.get("et0_estimada") or 0.0
        riego_mm = plan_riego_mm[indice] if indice < len(plan_riego_mm) else 0.0

        etc_mm = et0_dia * kc

        agua_actual_mm, _drenaje_mm = actualizar_balance_diario(
            agua_actual_mm=agua_actual_mm,
            lluvia_mm=lluvia_mm,
            riego_mm=riego_mm,
            etc_mm=etc_mm,
            agua_total_util_mm=agua_total_util_mm,
        )

        if agua_actual_mm < (0.5 * agua_total_util_mm):
            dias_estres += 1

        agua_total_usada_mm += riego_mm
        evolucion_diaria.append(round(agua_actual_mm, 2))

    return {
        "dias_estres": dias_estres,
        "agua_total_usada_mm": round(agua_total_usada_mm, 2),
        "balance_final_mm": round(agua_actual_mm, 2),
        "evolucion_diaria": evolucion_diaria,
    }


def simular_escenarios(estado_actual, pronostico_7dias, parametros_cultivo):
    """
    Simula los 3 escenarios de riego (no regar, regar ahora, regar
    diferido) usando el pronostico de los proximos dias, y determina
    cual es el escenario optimo.

    Parametros:
        estado_actual (dict): resultado de
            balance_hidrico.calcular_estado_hidrico(), debe tener las
            llaves "agua_disponible_mm", "agua_total_util_mm" y
            "deficit_mm".
        pronostico_7dias (list[dict]): pronostico diario, cada elemento
            con las llaves "lluvia_mm" y "et0_estimada".
        parametros_cultivo (dict): debe tener la llave "kc" (coeficiente
            de cultivo actual).

    Retorna:
        dict con las llaves:
            - "escenarios": dict con los resultados de cada escenario
              (claves "no_regar", "regar_ahora", "regar_diferido").
            - "escenario_optimo": nombre del escenario elegido como
              mejor opcion.
    """
    agua_inicial_mm = estado_actual["agua_disponible_mm"]
    agua_total_util_mm = estado_actual["agua_total_util_mm"]
    deficit_mm = estado_actual["deficit_mm"]
    kc = parametros_cultivo["kc"]

    cantidad_dias = len(pronostico_7dias)

    # Escenario 1: no regar
    plan_no_regar = [0.0] * cantidad_dias

    # Escenario 2: regar ahora (dia 1, indice 0) con el deficit actual
    plan_regar_ahora = [0.0] * cantidad_dias
    if cantidad_dias > 0:
        plan_regar_ahora[0] = deficit_mm

    # Escenario 3: regar diferido (dia 2, indice 1) con el mismo volumen
    plan_regar_diferido = [0.0] * cantidad_dias
    if cantidad_dias > 1:
        plan_regar_diferido[1] = deficit_mm
    elif cantidad_dias == 1:
        # Si solo hay un dia de pronostico, no se puede diferir: se riega ese dia
        plan_regar_diferido[0] = deficit_mm

    resultados = {
        ESCENARIO_NO_REGAR: _simular_un_escenario(
            agua_inicial_mm, agua_total_util_mm, kc, pronostico_7dias, plan_no_regar
        ),
        ESCENARIO_REGAR_AHORA: _simular_un_escenario(
            agua_inicial_mm, agua_total_util_mm, kc, pronostico_7dias, plan_regar_ahora
        ),
        ESCENARIO_REGAR_DIFERIDO: _simular_un_escenario(
            agua_inicial_mm, agua_total_util_mm, kc, pronostico_7dias, plan_regar_diferido
        ),
    }

    escenario_optimo = _elegir_escenario_optimo(resultados)

    return {
        "escenarios": resultados,
        "escenario_optimo": escenario_optimo,
    }


def _elegir_escenario_optimo(resultados):
    """
    Elige el mejor escenario de entre los simulados.

    Criterio: primero se prefieren los escenarios con 0 dias de estres
    hidrico; entre esos, se elige el que use menos agua de riego. Si
    ningun escenario tiene 0 dias de estres, se elige el que tenga
    menos dias de estres (y, en caso de empate, el que use menos agua).

    Parametros:
        resultados (dict): diccionario {nombre_escenario: resultado},
            donde cada resultado tiene "dias_estres" y
            "agua_total_usada_mm".

    Retorna:
        str: nombre del escenario elegido.
    """
    escenarios_sin_estres = {
        nombre: datos for nombre, datos in resultados.items() if datos["dias_estres"] == 0
    }

    if escenarios_sin_estres:
        candidatos = escenarios_sin_estres
    else:
        # Ningun escenario evita el estres: buscamos el menor numero de dias de estres
        minimo_estres = min(datos["dias_estres"] for datos in resultados.values())
        candidatos = {
            nombre: datos for nombre, datos in resultados.items() if datos["dias_estres"] == minimo_estres
        }

    # Entre los candidatos, elegimos el que use menos agua de riego
    mejor_nombre = min(candidatos, key=lambda nombre: candidatos[nombre]["agua_total_usada_mm"])

    return mejor_nombre


def generar_texto_recomendacion(resultado_simulacion, deficit_mm):
    """
    Genera un texto en español, legible para el usuario, explicando la
    recomendacion de riego segun el escenario optimo encontrado.

    Parametros:
        resultado_simulacion (dict): resultado de simular_escenarios(),
            con las llaves "escenarios" y "escenario_optimo".
        deficit_mm (float): deficit hidrico actual, en mm.

    Retorna:
        str: texto con la recomendacion para mostrar en la pestaña
        "Gemelo Digital".
    """
    escenario_optimo = resultado_simulacion["escenario_optimo"]
    datos_optimo = resultado_simulacion["escenarios"][escenario_optimo]

    if escenario_optimo == ESCENARIO_NO_REGAR:
        return (
            "No es necesario regar en este momento. La lluvia pronosticada "
            "para los proximos dias deberia mantener el cultivo sin estres hidrico."
        )

    if escenario_optimo == ESCENARIO_REGAR_AHORA:
        return (
            f"Se recomienda regar AHORA aproximadamente {deficit_mm:.1f} mm "
            "para cubrir el deficit hidrico actual y evitar dias de estres en el cultivo."
        )

    if escenario_optimo == ESCENARIO_REGAR_DIFERIDO:
        return (
            "Se recomienda esperar y regar en el dia 2 del pronostico "
            f"(aprox. {deficit_mm:.1f} mm). Esto permite aprovechar mejor la lluvia "
            "esperada antes de aplicar el riego."
        )

    # Caso de respaldo (no deberia ocurrir)
    return (
        f"Escenario recomendado: {escenario_optimo}. "
        f"Dias de estres esperados: {datos_optimo['dias_estres']}."
    )
