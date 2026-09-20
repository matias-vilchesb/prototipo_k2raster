import k2raster_engine
import time
import numpy as np

print("==================================================")
print("  PROBANDO MOTOR K2-RASTER CON MUESTREO AL VUELO")
print("==================================================")

raster = k2raster_engine.K2Raster()
raster.load("mapa_comprimido.k2r")

rows = raster.get_rows()
cols = raster.get_cols()
min_val = raster.get_min_value()
max_val = raster.get_max_value()

print(f"Mapa cargado con éxito:")
print(f" - Dimensiones: {rows} filas x {cols} columnas ({rows * cols:,} celdas)")
print(f" - Rango global de valores: [{min_val}, {max_val}]")
print("--------------------------------------------------\n")

# Pruebas a diferentes escalas de visualización (LOD)

# Función auxiliar para renderizado visual en terminal
def render_ascii_map(matrix):
    chars = " .:-=+*#%@"
    max_v = max(1, matrix.max())
    lines = []
    for row in matrix:
        lines.append(" ".join(chars[min(len(chars)-1, int(v / max_v * (len(chars)-1)))] for v in row))
    return "\n".join(lines)

# CASO 1: Vista Global (Zoom 1) - Ver todo el mapa adaptado a pantalla de 20x15
print("1. [ZOOM 1 - VISTA GLOBAL COMPLETA]")
t0 = time.perf_counter()
vp_global = raster.get_viewport(0, rows - 1, 0, cols - 1, target_width=20, target_height=14)
t1 = time.perf_counter()

data_global = np.array(vp_global["data"]).reshape((vp_global["rows"], vp_global["cols"]))
print(f" - Ventana consultada: todo el mapa (0:{rows-1}, 0:{cols-1})")
print(f" - Resolución de salida: {vp_global['rows']}x{vp_global['cols']} (Paso: X={vp_global['step_x']}, Y={vp_global['step_y']})")
print(f" - Tiempo de respuesta: {(t1 - t0)*1000:.3f} ms")
print(f" - Estadísticas reales:")
print(f"     * Promedio: {data_global.mean():.2f} | Mediana: {np.median(data_global):.2f}")
print(f"     * Mínimo:   {data_global.min()} | Máximo: {data_global.max()}")
print(" - Matriz de valores (Zoom 1):")
print(data_global)
print(" - Vista previa visual (Silueta del mapa):")
print(render_ascii_map(data_global))
print("--------------------------------------------------\n")

# CASO 2: Vista Regional (Zoom 5) - Enfocar un cuadrante medio (ej. 200:500, 200:500)
print("2. [ZOOM 5 - VISTA REGIONAL]")
x1, x2 = 200, 500
y1, y2 = 200, 500
t0 = time.perf_counter()
vp_regional = raster.get_viewport(x1, x2, y1, y2, target_width=16, target_height=12)
t1 = time.perf_counter()

data_regional = np.array(vp_regional["data"]).reshape((vp_regional["rows"], vp_regional["cols"]))
print(f" - Ventana consultada: X[{x1}:{x2}], Y[{y1}:{y2}] ({x2-x1+1}x{y2-y1+1} celdas)")
print(f" - Resolución de salida: {vp_regional['rows']}x{vp_regional['cols']} (Paso: X={vp_regional['step_x']}, Y={vp_regional['step_y']})")
print(f" - Tiempo de respuesta: {(t1 - t0)*1000:.3f} ms")
print(f" - Estadísticas de la región:")
print(f"     * Promedio: {data_regional.mean():.2f} | Mediana: {np.median(data_regional):.2f}")
print(f"     * Mínimo:   {data_regional.min()} | Máximo: {data_regional.max()}")
print(" - Matriz de valores (Zoom 5):")
print(data_regional)
print(" - Vista previa visual:")
print(render_ascii_map(data_regional))
print("--------------------------------------------------\n")

# CASO 3: Vista Detallada (Zoom 10) - Ventana pequeña a resolución píxel a píxel (paso 1)
print("3. [ZOOM 10 - VISTA LOCAL DETALLADA (PÍXEL A PÍXEL)]")
x1, x2 = 100, 115
y1, y2 = 302, 317
t0 = time.perf_counter()
vp_local = raster.get_values_sampled(x1, x2, y1, y2, step_x=1, step_y=1)
t1 = time.perf_counter()

data_local = np.array(vp_local).reshape((x2 - x1 + 1, y2 - y1 + 1))
print(f" - Ventana consultada: X[{x1}:{x2}], Y[{y1}:{y2}] ({x2-x1+1}x{y2-y1+1} celdas)")
print(f" - Paso aplicado: 1x1 (resolución nativa)")
print(f" - Tiempo de respuesta: {(t1 - t0)*1000:.3f} ms")
print(f" - Matriz de valores (Zoom 10):")
print(data_local)
print(" - Vista previa visual:")
print(render_ascii_map(data_local))
print("==================================================")

