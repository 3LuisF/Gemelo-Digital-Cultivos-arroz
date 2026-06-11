"""
Pruebas basicas del modelo de balance hidrico (Thornthwaite-Mather).

Estas pruebas usan los parametros del suelo "franco-arcilloso del
Sinu" (config/suelo.yaml) y de los cultivos definidos para el proyecto,
para comprobar que el "tanque" de agua del suelo se llena, se vacia y
respeta sus limites como se espera.
"""

from src.gemelo import balance_hidrico as bh

# Parametros del suelo franco-arcilloso del Sinu (ver config/suelo.yaml)
CAPACIDAD_CAMPO = 0.32
PUNTO_MARCHITEZ = 0.18

# Profundidad de raiz del arroz secano (ver config/cultivos.yaml)
PROFUNDIDAD_RAIZ_ARROZ_M = 0.4


def test_agua_total_util_arroz_secano():
    # (0.32 - 0.18) * 0.4 m * 1000 = 56 mm
    agua_total_util = bh.calcular_agua_total_util_mm(PROFUNDIDAD_RAIZ_ARROZ_M, CAPACIDAD_CAMPO, PUNTO_MARCHITEZ)
    assert round(agua_total_util, 2) == 56.0


def test_agua_actual_en_punto_de_marchitez_es_cero():
    # Si la humedad del suelo es igual al punto de marchitez (18%),
    # no queda agua disponible para la planta.
    agua_disponible = bh.calcular_agua_actual_desde_humedad(
        humedad_suelo_porcentaje=18.0,
        profundidad_raiz_m=PROFUNDIDAD_RAIZ_ARROZ_M,
        punto_marchitez=PUNTO_MARCHITEZ,
    )
    assert agua_disponible == 0.0


def test_agua_actual_en_capacidad_de_campo_es_igual_al_total_util():
    # Si la humedad del suelo es igual a la capacidad de campo (32%),
    # el agua disponible debe ser igual al agua total util.
    agua_disponible = bh.calcular_agua_actual_desde_humedad(
        humedad_suelo_porcentaje=32.0,
        profundidad_raiz_m=PROFUNDIDAD_RAIZ_ARROZ_M,
        punto_marchitez=PUNTO_MARCHITEZ,
    )
    agua_total_util = bh.calcular_agua_total_util_mm(PROFUNDIDAD_RAIZ_ARROZ_M, CAPACIDAD_CAMPO, PUNTO_MARCHITEZ)

    assert round(agua_disponible, 2) == round(agua_total_util, 2)


def test_agua_actual_nunca_es_negativa_por_debajo_del_punto_de_marchitez():
    # Si el sensor reporta una humedad por debajo del punto de
    # marchitez, el agua disponible no puede ser negativa.
    agua_disponible = bh.calcular_agua_actual_desde_humedad(
        humedad_suelo_porcentaje=10.0,
        profundidad_raiz_m=PROFUNDIDAD_RAIZ_ARROZ_M,
        punto_marchitez=PUNTO_MARCHITEZ,
    )
    assert agua_disponible == 0.0


def test_balance_diario_sin_lluvia_ni_riego_disminuye_el_agua():
    agua_total_util = 56.0
    agua_actual = 40.0
    etc = 4.0  # evapotranspiracion del cultivo del dia, en mm

    agua_nueva, drenaje = bh.actualizar_balance_diario(
        agua_actual_mm=agua_actual, lluvia_mm=0.0, riego_mm=0.0,
        etc_mm=etc, agua_total_util_mm=agua_total_util,
    )

    assert agua_nueva == agua_actual - etc
    assert drenaje == 0.0


def test_balance_diario_con_lluvia_excesiva_genera_drenaje():
    agua_total_util = 56.0
    agua_actual = 50.0
    lluvia = 30.0  # mas de lo que cabe en el suelo
    etc = 4.0

    agua_nueva, drenaje = bh.actualizar_balance_diario(
        agua_actual_mm=agua_actual, lluvia_mm=lluvia, riego_mm=0.0,
        etc_mm=etc, agua_total_util_mm=agua_total_util,
    )

    # El agua nueva no puede superar la capacidad del "tanque"
    assert agua_nueva == agua_total_util
    # El excedente se va por drenaje
    assert drenaje == (agua_actual + lluvia - etc) - agua_total_util
    assert drenaje > 0


def test_balance_diario_no_baja_de_cero():
    agua_total_util = 56.0
    agua_actual = 2.0
    etc = 10.0  # mas de lo que queda disponible

    agua_nueva, drenaje = bh.actualizar_balance_diario(
        agua_actual_mm=agua_actual, lluvia_mm=0.0, riego_mm=0.0,
        etc_mm=etc, agua_total_util_mm=agua_total_util,
    )

    assert agua_nueva == 0.0
    assert drenaje == 0.0


def test_estado_hidrico_detecta_estres_con_suelo_seco():
    lecturas = {"humedad_suelo": 18.0, "et0": 4.5}  # humedad = punto de marchitez
    parametros_cultivo = {"kc": 1.1, "profundidad_raiz_m": PROFUNDIDAD_RAIZ_ARROZ_M}
    parametros_suelo = {"capacidad_campo": CAPACIDAD_CAMPO, "punto_marchitez": PUNTO_MARCHITEZ}

    estado = bh.calcular_estado_hidrico(lecturas, parametros_cultivo, parametros_suelo)

    assert estado["agua_disponible_mm"] == 0.0
    assert estado["porcentaje_agua_util"] == 0.0
    assert estado["esta_en_estres"] is True
    # ETc = ET0 * Kc = 4.5 * 1.1 = 4.95
    assert estado["evapotranspiracion_mm"] == 4.95


def test_estado_hidrico_sin_estres_con_suelo_humedo():
    lecturas = {"humedad_suelo": 32.0, "et0": 4.0}  # humedad = capacidad de campo
    parametros_cultivo = {"kc": 1.0, "profundidad_raiz_m": PROFUNDIDAD_RAIZ_ARROZ_M}
    parametros_suelo = {"capacidad_campo": CAPACIDAD_CAMPO, "punto_marchitez": PUNTO_MARCHITEZ}

    estado = bh.calcular_estado_hidrico(lecturas, parametros_cultivo, parametros_suelo)

    assert estado["porcentaje_agua_util"] == 100.0
    assert estado["deficit_mm"] == 0.0
    assert estado["esta_en_estres"] is False
