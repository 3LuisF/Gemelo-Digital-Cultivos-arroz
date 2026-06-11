"""
Pruebas basicas del modulo de evapotranspiracion (ET0, Penman-Monteith
FAO-56).

La idea de estas pruebas no es validar el metodo cientifico en si
(eso ya lo valido la FAO), sino comprobar que la implementacion en
Python da resultados razonables y se comporta como se espera ante
casos limite.
"""

from datetime import datetime

from src.gemelo import evapotranspiracion as et


def test_dia_juliano_primero_de_enero():
    # El 1 de enero siempre es el dia juliano 1
    fecha = datetime(2024, 1, 1)
    assert et.calcular_dia_juliano(fecha) == 1


def test_presion_saturacion_vapor_aumenta_con_la_temperatura():
    # A mayor temperatura, mayor presion de saturacion de vapor
    es_20 = et.calcular_presion_saturacion_vapor(20)
    es_30 = et.calcular_presion_saturacion_vapor(30)

    assert es_30 > es_20
    # Para 20°C, la FAO-56 reporta es ~ 2.34 kPa
    assert round(es_20, 2) == 2.34


def test_constante_psicrometrica_a_nivel_del_mar():
    # A nivel del mar (elevacion 0, presion atmosferica = 101.3 kPa),
    # gamma = 0.665e-3 * 101.3 ~ 0.0674 kPa/°C segun FAO-56
    gamma = et.calcular_constante_psicrometrica(elevacion_m=0.0)
    assert round(gamma, 4) == 0.0674


def test_radiacion_extraterrestre_es_mayor_en_verano_que_en_invierno_monteria():
    # Monteria (latitud ~ 8.7° N): la radiacion extraterrestre varia
    # poco durante el año por estar cerca al ecuador, pero debe ser
    # positiva en cualquier epoca.
    latitud = 8.7479

    ra_enero = et.calcular_radiacion_extraterrestre(latitud, dia_juliano=15)
    ra_junio = et.calcular_radiacion_extraterrestre(latitud, dia_juliano=170)

    assert ra_enero > 0
    assert ra_junio > 0


def test_et0_penman_monteith_da_un_valor_positivo_y_razonable():
    # Dia tipico calido en Monteria, Cordoba
    et0 = et.calcular_et0_penman_monteith(
        temp_max=33.0,
        temp_min=24.0,
        humedad_rel_media=80.0,
        fecha=datetime(2026, 6, 10),
        latitud=8.7479,
    )

    # ET0 en zonas tropicales suele estar entre 3 y 6 mm/dia
    assert 2.0 < et0 < 7.0


def test_et0_nunca_es_negativa():
    # Caso extremo: temperaturas muy bajas y humedad muy alta, donde el
    # resultado del balance de radiacion podria volverse negativo. La
    # funcion debe limitar el resultado a 0 como minimo.
    et0 = et.calcular_et0_penman_monteith(
        temp_max=5.0,
        temp_min=2.0,
        humedad_rel_media=99.0,
        fecha=datetime(2026, 1, 1),
        latitud=8.7479,
    )

    assert et0 >= 0.0


def test_estimar_radiacion_solar_con_mayor_amplitud_termica_da_mas_radiacion():
    ra = 35.0  # valor de ejemplo de radiacion extraterrestre

    rs_amplitud_baja = et.estimar_radiacion_solar(temp_max=28, temp_min=26, radiacion_extraterrestre=ra)
    rs_amplitud_alta = et.estimar_radiacion_solar(temp_max=34, temp_min=20, radiacion_extraterrestre=ra)

    assert rs_amplitud_alta > rs_amplitud_baja
