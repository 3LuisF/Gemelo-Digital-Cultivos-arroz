# Manual de Usuario — Gemelo Digital de Riego (Arroz Secano y Maíz)

Este manual describe el funcionamiento del prototipo desde el punto de
vista del usuario final, pensado como apoyo para la sustentación del
proyecto.

## 1. Propósito del sistema

El sistema apoya la toma de decisiones de riego para cultivos de
**arroz secano** y **maíz** en la zona del Sinú (Córdoba), combinando:

- Datos de campo (temperatura real vía sensor PT100, y humedad de
  suelo, caudal y lluvia simulados a través del PLC LOGO! 8).
- Pronóstico meteorológico de 7 días (Open-Meteo).
- Modelos científicos de evapotranspiración (Penman-Monteith FAO-56) y
  balance hídrico del suelo (Thornthwaite-Mather).

El resultado es una **recomendación de riego** (regar ahora, esperar,
o no regar) y una proyección visual de cómo evolucionaría el agua
disponible en el suelo en los próximos días.

## 2. Modo simulado vs. modo conectado

La barra de estado (parte inferior de la ventana) muestra en todo
momento si el PLC está **ONLINE** u **OFFLINE (modo simulado)**:

- **ONLINE**: la aplicación lee directamente del LOGO! 8 cada 5
  segundos (temperatura real del PT100, y las demás señales según lo
  que esté conectado/simulado en el PLC).
- **OFFLINE (modo simulado)**: la aplicación no puede comunicarse con
  el PLC (por ejemplo, porque no hay hardware disponible). En este
  caso, usa la última lectura guardada manualmente desde la pestaña
  *Control Manual*. Esto permite probar todo el sistema (modelos
  hídricos, recomendaciones, gráficas, históricos) sin necesidad de
  hardware físico.

## 3. Pestaña "Estado actual"

Muestra en una grilla:

- **Temperatura ambiente (°C)**, **Humedad del suelo (%)**, **Caudal
  actual (L/min)** y **Lluvia hoy (mm)**: últimos valores leídos.
- **Estado de las válvulas (Q1, Q2)** y **estado de la bomba (Q3)**:
  indicadores de color (verde = encendido, rojo = apagado, gris = sin
  dato).
- Botón **"Actualizar ahora"**: fuerza una nueva lectura inmediata sin
  esperar el ciclo automático de 5 segundos.
- Etiqueta inferior con la fecha/hora de la última actualización y la
  fuente del dato (`plc` o `manual`).

## 4. Pestaña "Gemelo digital"

Es el panel central del proyecto. Se actualiza automáticamente cada 30
segundos (hilo de fondo) y muestra:

- **Estado hídrico actual**: agua disponible (mm) sobre el total útil,
  déficit hídrico (mm) y porcentaje de agua útil. El porcentaje se
  muestra en rojo si el cultivo está en **estrés hídrico** (agua
  disponible por debajo del 50% del agua útil total).
- **Cultivo**: tipo de cultivo configurado, días desde la siembra,
  etapa fenológica actual (inicial, desarrollo, media o final) y el
  coeficiente de cultivo (Kc) correspondiente a esa etapa.
- **Recomendación de riego**: texto generado por el simulador de
  escenarios (ver sección 4.1) y el botón **"EJECUTAR RIEGO
  RECOMENDADO"**.
- **Gráfica de balance hídrico**: combina el histórico de los últimos
  7 días (agua disponible registrada) con la proyección de los
  próximos 7 días según el escenario óptimo, además de líneas de
  referencia para la capacidad útil total y el umbral de estrés (50%).

### 4.1 Simulador de escenarios

Cada vez que hay un nuevo estado hídrico y un nuevo pronóstico de
clima, el sistema simula tres escenarios para los próximos días:

1. **No regar**: solo se considera la lluvia pronosticada.
2. **Regar ahora**: se aplica el déficit actual como riego en el
   primer día del pronóstico.
3. **Regar diferido**: se aplica el mismo riego, pero en el segundo
   día (para aprovechar lluvia esperada en el primer día).

Para cada escenario se calcula cuántos días el cultivo quedaría en
estrés hídrico y cuánta agua de riego se usaría en total. El sistema
elige como **óptimo** el escenario con 0 días de estrés que use menos
agua; si ningún escenario evita el estrés por completo, elige el que
menos días de estrés genere.

### 4.2 Botón "EJECUTAR RIEGO RECOMENDADO" — IMPORTANTE

> **Este botón NO envía ninguna orden al PLC.** Al presionarlo, se
> muestra un mensaje de confirmación que explica que la acción es
> **solo una simulación**. Si el usuario confirma, se registra un
> evento en la tabla `eventos_riego` con `ejecutado_en_plc=False`,
> `tipo="recomendado"` y el volumen recomendado (déficit hídrico
> actual en mm). Esto permite demostrar el flujo completo de decisión
> sin operar maquinaria real (alcance B del proyecto).

## 5. Pestaña "Control manual"

Permite **forzar manualmente** los valores de los sensores simulados y
el estado de las salidas del PLC. Es la forma principal de generar
datos de prueba cuando no hay hardware real conectado (excepto el
sensor de temperatura PT100).

- **Forzar entradas (sensores simulados)**: para cada entrada (caudal,
  pluviómetro, temperatura PT100, humedad de suelo) se puede ingresar
  un valor con un spinbox y presionar "Aplicar valor". Tras confirmar,
  se guarda una nueva lectura con `fuente="manual"` en la tabla
  `lecturas_sensores` y se registra la acción en `acciones_manuales`.
- **Forzar salidas (válvulas/bomba)**: botones "Encender/Apagar" para
  Q1, Q2 y Q3. Si el PLC está conectado, esta acción **sí escribe
  directamente sobre la salida física del LOGO!** (a diferencia del
  botón de riego recomendado de la pestaña *Gemelo digital*). Si el
  PLC está offline, se actualiza un estado simulado interno. Toda
  acción se registra en `acciones_manuales`.
- **"Volver a modo automático"**: apaga todas las salidas forzadas
  (Q1, Q2, Q3) tras confirmación.

Todas las acciones de esta pestaña requieren confirmación explícita
del usuario mediante un cuadro de diálogo.

## 6. Pestaña "Histórico"

Permite consultar las lecturas de sensores guardadas en la base de
datos:

- Selección de rango de fechas (desde/hasta).
- Selección de la variable a graficar (temperatura, humedad de suelo,
  caudal o lluvia acumulada).
- Tabla con las últimas 50 lecturas del rango seleccionado.
- Botón **"Exportar a CSV"** para guardar los datos consultados.

## 7. Pestaña "Clima"

Muestra el pronóstico de 7 días obtenido de la API Open-Meteo para la
ubicación configurada (por defecto Montería, Córdoba):

- Tabla con temperatura máxima/mínima, lluvia, humedad relativa media
  y ET0 estimada por día.
- Gráfica de barras con la lluvia esperada por día.
- **Alertas automáticas**:
  - Lluvia fuerte: si algún día se pronostican más de 50 mm.
  - Sequía proyectada: si se esperan más de 5 días seguidos sin lluvia
    significativa (≤ 0.1 mm).
- Botón **"Actualizar pronóstico"** para consultar la API de
  inmediato (además de la consulta automática cada hora).

Si no hay conexión a internet, se muestra el último pronóstico
guardado en la base de datos.

## 8. Pestaña "Configuración"

Permite ajustar y guardar:

- **PLC**: dirección IP, rack y slot, con botón "Probar conexión PLC".
- **Cultivo**: tipo de cultivo (arroz secano / maíz), fecha de siembra
  y área sembrada (hectáreas). Al guardar, se crea un nuevo registro
  en la tabla `configuracion_cultivo`, que el hilo del gemelo digital
  usa para calcular días desde siembra, etapa fenológica y Kc.
- **Suelo**: capacidad de campo y punto de marchitez (fracciones de
  volumen).
- **Ubicación**: latitud y longitud usadas para el cálculo de ET0 y la
  consulta a Open-Meteo.

Algunos cambios (como la IP del PLC) requieren reiniciar la aplicación
para aplicarse por completo.

## 9. Resumen del flujo de datos

```
PLC LOGO! 8 / Control Manual
        │
        ▼
lecturas_sensores  ──────────────┐
        │                        │
        ▼                        ▼
balance_hidrico (Thornthwaite-Mather)   open_meteo (pronóstico 7 días)
        │                        │
        ▼                        ▼
  estado_gemelo  ◄──────  simulador (escenarios de riego)
        │
        ▼
  Pestaña "Gemelo digital"
  (estado hídrico + recomendación + gráfica)
        │
        ▼
  eventos_riego (ejecutado_en_plc = False, siempre simulado)
```

## 10. Limitaciones conocidas (alcance B)

- Solo el sensor de temperatura (PT100, AI3) corresponde a hardware
  real; los demás sensores (caudal, pluviómetro, humedad de suelo) son
  simulados a través de la pestaña *Control Manual*.
- El riego "recomendado" nunca se ejecuta físicamente: es un registro
  con fines de demostración y análisis.
- El simulador de escenarios usa un Kc constante durante la ventana de
  7 días (no recalcula la etapa fenológica día a día dentro de la
  proyección).
