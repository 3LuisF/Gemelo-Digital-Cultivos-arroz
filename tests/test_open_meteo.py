"""
Pruebas basicas del modulo de clima (Open-Meteo).

No hacemos peticiones reales a internet en las pruebas: usamos un JSON
de ejemplo (con la misma forma que devuelve Open-Meteo) para probar la
funcion que lo convierte a una lista de diccionarios, y simulamos el
caso en que la API falla para comprobar que se usa la base de datos
como respaldo.
"""

import os

from src.clima import open_meteo
from src.database import gestor_db

# JSON de ejemplo con la misma forma que devuelve la API de Open-Meteo
JSON_EJEMPLO_OPEN_METEO = {
    "daily": {
        "time": ["2026-06-10", "2026-06-11"],
        "temperature_2m_max": [33.0, 33.6],
        "temperature_2m_min": [24.5, 25.2],
        "precipitation_sum": [1.0, 1.4],
        "relative_humidity_2m_mean": [83.0, 83.0],
        "et0_fao_evapotranspiration": [4.65, 4.61],
    }
}


def test_convertir_json_a_lista():
    pronostico = open_meteo._convertir_json_a_lista(JSON_EJEMPLO_OPEN_METEO)

    assert len(pronostico) == 2

    primer_dia = pronostico[0]
    assert primer_dia["fecha_pronostico"].strftime("%Y-%m-%d") == "2026-06-10"
    assert primer_dia["temp_max"] == 33.0
    assert primer_dia["temp_min"] == 24.5
    assert primer_dia["lluvia_mm"] == 1.0
    assert primer_dia["humedad_rel"] == 83.0
    assert primer_dia["et0_estimada"] == 4.65


def test_convertir_json_vacio_da_lista_vacia():
    pronostico = open_meteo._convertir_json_a_lista({"daily": {"time": []}})
    assert pronostico == []


def test_obtener_pronostico_usa_respaldo_de_la_base_de_datos_si_falla_la_api(tmp_path, monkeypatch):
    # Inicializamos una base de datos temporal solo para esta prueba
    ruta_db = os.path.join(tmp_path, "gemelo_test.db")
    gestor_db.inicializar_base_datos(ruta_db)

    # Guardamos un pronostico "viejo" como si ya se hubiera consultado antes
    pronostico_guardado = open_meteo._convertir_json_a_lista(JSON_EJEMPLO_OPEN_METEO)
    gestor_db.guardar_pronostico_clima(pronostico_guardado)

    # Simulamos que la peticion a Open-Meteo siempre falla
    def get_que_falla(*args, **kwargs):
        raise ConnectionError("Sin conexion a internet (simulado para la prueba)")

    monkeypatch.setattr(open_meteo.requests, "get", get_que_falla)

    pronostico = open_meteo.obtener_pronostico(latitud=8.7479, longitud=-75.8814, dias=2)

    # Como la API "fallo", debe devolver el pronostico guardado en la BD
    assert len(pronostico) == 2
    assert pronostico[0]["temp_max"] == 33.0
