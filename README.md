# Gemelo Digital de Riego — Arroz Secano y Maíz (Córdoba)

Prototipo académico de un **gemelo digital** para apoyar decisiones de
riego en cultivos de arroz secano y maíz en la región del Sinú,
Córdoba. El sistema combina:

- Lectura de sensores (reales y simulados) conectados a un PLC Siemens
  **LOGO! 8 (0BA8)**.
- Modelos hídricos científicos: **Penman-Monteith FAO-56** (ET0) y
  **balance hídrico Thornthwaite-Mather** (humedad del suelo).
- Pronóstico de clima de 7 días vía la API gratuita **Open-Meteo**.
- Una interfaz de escritorio en **PyQt5** con 6 pestañas.
- Persistencia en **SQLite** mediante **SQLAlchemy**.

> **Alcance del proyecto (alcance B):** el botón "Ejecutar riego
> recomendado" de la pestaña *Gemelo Digital* **NO envía ninguna orden
> real al PLC**. El riego se simula y se registra en la base de datos
> con `ejecutado_en_plc=False`. La pestaña *Control Manual* sí permite
> forzar las salidas Q1/Q2/Q3 directamente sobre el PLC, pero solo con
> fines de prueba/diagnóstico y siempre con confirmación del usuario.

---

## 1. Estructura del proyecto

```
gemelo_digital/
├── config/                  # Archivos de configuración (YAML)
│   ├── settings.yaml        # PLC, escalas de sensores, BD, ubicación, intervalos
│   ├── cultivos.yaml        # Etapas fenológicas y Kc de arroz secano y maíz
│   └── suelo.yaml           # Parámetros del suelo franco-arcilloso del Sinú
├── src/
│   ├── plc/                 # Conexión y mapeo de memoria del LOGO! 8
│   ├── database/            # Modelos SQLAlchemy y funciones CRUD
│   ├── gemelo/               # Modelos hídricos: ET0, cultivo, balance hídrico, simulador
│   ├── clima/                # Cliente de la API Open-Meteo
│   ├── gui/                  # Ventana principal, pestañas, hilos y widgets
│   └── utilidades/           # Logger y utilidades de configuración
├── tests/                    # Pruebas unitarias del modelo hídrico
├── docs/                      # Documentación adicional (manual de usuario)
├── logs/                      # Archivos de log generados en tiempo de ejecución
├── main.py                    # Punto de entrada de la aplicación
└── requirements.txt
```

---

## 2. Instalación

### 2.1 Requisitos previos

- Python 3.10 o superior (probado con Python 3.14 en Windows).
- (Opcional) Un PLC Siemens LOGO! 8 (0BA8) en la misma red, programado
  según el mapeo de memoria descrito en
  [`src/plc/mapeo_memoria.py`](src/plc/mapeo_memoria.py). Si no se
  cuenta con el PLC, la aplicación funciona en **modo simulado**.

### 2.2 Crear entorno virtual e instalar dependencias

Desde la carpeta `gemelo_digital/`:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Esto instala: PyQt5, python-snap7, SQLAlchemy, pandas, numpy,
matplotlib, requests, PyYAML y pytest (para las pruebas).

> **Nota (Windows):** las versiones del `requirements.txt` están
> definidas como mínimos (`>=`) porque algunas versiones antiguas no
> tienen instaladores precompilados ("wheels") para versiones
> recientes de Python en Windows. `pip` instalará automáticamente las
> versiones más nuevas compatibles.

---

## 3. Configuración

Toda la configuración se encuentra en la carpeta `config/` y también
puede editarse desde la pestaña **Configuración** de la interfaz
gráfica.

### 3.1 `config/settings.yaml`

| Sección | Descripción |
|---|---|
| `plc.ip / rack / slot / timeout_ms` | Datos de conexión al LOGO! 8. Por defecto `192.168.0.29`, rack 0, slot 1. |
| `escalas_entradas` | Rangos de conversión (valor real mínimo/máximo) para cada entrada analógica. |
| `database.ruta` | Ruta del archivo SQLite (relativa a la raíz del proyecto). |
| `ubicacion` | Latitud/longitud del cultivo (por defecto Montería, Córdoba: 8.7479, -75.8814) y zona horaria. |
| `intervalos` | Cada cuánto se ejecutan los hilos de fondo (lectura PLC, clima, recálculo del gemelo). |

### 3.2 `config/cultivos.yaml`

Define, para `arroz_secano` y `maiz`, la duración del ciclo, la
profundidad efectiva de raíz y las etapas fenológicas con su
coeficiente de cultivo (Kc), usados por el modelo Penman-Monteith y el
balance hídrico.

### 3.3 `config/suelo.yaml`

Parámetros del suelo franco-arcilloso típico del valle del Sinú:
capacidad de campo, punto de marchitez y densidad aparente.

### 3.4 Mapeo del PLC (LOGO! 8)

| Entrada LOGO! | Sensor | Tipo |
|---|---|---|
| I1 (AI1) | Caudalímetro | Simulado |
| I2 (AI2) | Pluviómetro | Simulado |
| I3 (AI3) | Sensor PT100 (temperatura) | **Real** |
| I4 (AI4) | Humedad del suelo | Simulado |

| Salida | Función |
|---|---|
| Q1 | Válvula de riego zona 1 |
| Q2 | Válvula de riego zona 2 |
| Q3 | Bomba principal |
| Q4 | Reserva (no usada) |

Las direcciones de memoria VM usadas por la aplicación están
documentadas en [`src/plc/mapeo_memoria.py`](src/plc/mapeo_memoria.py)
y deben coincidir con el bloque "VM mapping" configurado en
LOGO!Soft Comfort.

---

## 4. Uso

### 4.1 Ejecutar la aplicación

```powershell
venv\Scripts\activate
python main.py
```

Al iniciar, la aplicación:

1. Carga `config/settings.yaml`.
2. Crea (si no existe) la base de datos SQLite (`gemelo.db`) con las 6
   tablas del esquema.
3. Intenta conectarse al PLC. Si no lo logra (por ejemplo, si no hay
   hardware disponible), continúa en **modo simulado**: la barra de
   estado mostrará "PLC: OFFLINE (modo simulado)" y las lecturas se
   tomarán de la última fila guardada manualmente en la base de datos.
4. Inicia tres hilos de fondo:
   - **Lectura del PLC** cada 5 segundos.
   - **Consulta de clima** (Open-Meteo) cada 60 minutos.
   - **Recálculo del gemelo digital** cada 30 segundos.

### 4.2 Primer uso: configurar el cultivo

La pestaña *Gemelo Digital* necesita que exista una configuración de
cultivo activa (tipo de cultivo y fecha de siembra). Vaya a la pestaña
**Configuración**, seleccione el cultivo (arroz secano o maíz), la
fecha de siembra y guarde. A partir de ese momento, el hilo del gemelo
digital empezará a calcular el balance hídrico y la recomendación de
riego.

### 4.3 Pestañas

1. **Estado actual**: valores en vivo de temperatura, humedad de
   suelo, caudal y lluvia, y estado de las válvulas/bomba. Botón
   "Actualizar ahora" para forzar una lectura inmediata.
2. **Gemelo digital**: estado hídrico actual (agua disponible, déficit,
   % de agua útil), datos fenológicos del cultivo (etapa, Kc, días
   desde siembra), recomendación de riego generada por el simulador de
   escenarios, y una gráfica con el histórico de 7 días más la
   proyección de los próximos 7 días.
3. **Control manual**: permite forzar manualmente los valores de los
   sensores simulados (AI1-AI4) y el estado de las salidas Q1-Q3, con
   confirmación previa. Toda acción queda registrada en la tabla
   `acciones_manuales`.
4. **Histórico**: consulta de lecturas de sensores por rango de fechas,
   gráfica de la variable seleccionada y exportación a CSV.
5. **Clima**: pronóstico de 7 días de Open-Meteo (temperatura, lluvia,
   humedad relativa, ET0), gráfica de lluvia esperada y alertas simples
   de lluvia fuerte o sequía proyectada.
6. **Configuración**: edición de la configuración del PLC (con botón
   "Probar conexión"), del cultivo activo, del suelo y de la ubicación.

---

## 5. Pruebas

El proyecto incluye pruebas unitarias del modelo hídrico (ET0,
balance de agua del suelo, etapas de cultivo y cliente de Open-Meteo
con respaldo offline). Para ejecutarlas:

```powershell
venv\Scripts\activate
pytest tests/ -v
```

---

## 6. Documentación adicional

Ver [`docs/manual_usuario.md`](docs/manual_usuario.md) para un manual
de usuario orientado a la sustentación del proyecto (descripción
detallada de cada pestaña, flujo de datos y limitaciones del alcance
actual).
