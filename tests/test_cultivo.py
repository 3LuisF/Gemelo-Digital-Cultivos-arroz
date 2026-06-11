"""
Pruebas basicas del modulo de cultivos: que las etapas fenologicas y
los coeficientes Kc se lean correctamente desde "config/cultivos.yaml"
para el arroz secano y el maiz.
"""

from datetime import datetime

from src.gemelo import cultivo


def test_etapa_inicial_arroz_secano():
    # Segun config/cultivos.yaml, la etapa inicial del arroz secano va
    # del dia 0 al 25 con Kc = 0.50
    etapa = cultivo.obtener_etapa_actual("arroz_secano", dias_desde_siembra=10)

    assert etapa["nombre"] == "inicial"
    assert etapa["kc"] == 0.50


def test_etapa_media_maiz():
    # Segun config/cultivos.yaml, la etapa media del maiz va del dia 51
    # al 90 con Kc = 1.15
    etapa = cultivo.obtener_etapa_actual("maiz", dias_desde_siembra=70)

    assert etapa["nombre"] == "media"
    assert etapa["kc"] == 1.15


def test_etapa_mas_alla_del_ciclo_devuelve_la_ultima_etapa():
    # El arroz secano tiene un ciclo de 120 dias. Si ya pasaron 200
    # dias, debe devolver la etapa "final" (la ultima definida).
    etapa = cultivo.obtener_etapa_actual("arroz_secano", dias_desde_siembra=200)

    assert etapa["nombre"] == "final"


def test_profundidad_raiz_arroz_y_maiz():
    assert cultivo.obtener_profundidad_raiz("arroz_secano") == 0.4
    assert cultivo.obtener_profundidad_raiz("maiz") == 0.6


def test_dias_desde_siembra():
    fecha_siembra = datetime(2026, 1, 1)
    fecha_actual = datetime(2026, 1, 31)

    assert cultivo.calcular_dias_desde_siembra(fecha_siembra, fecha_actual) == 30


def test_dias_desde_siembra_en_el_futuro_no_es_negativo():
    # Si por error la fecha de siembra quedo en el futuro, no debe
    # devolver un numero de dias negativo.
    fecha_siembra = datetime(2026, 12, 1)
    fecha_actual = datetime(2026, 6, 10)

    assert cultivo.calcular_dias_desde_siembra(fecha_siembra, fecha_actual) == 0
