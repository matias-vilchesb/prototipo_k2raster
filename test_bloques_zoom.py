import k2raster_engine
import time
print("Cargando motor...")
raster = k2raster_engine.K2Raster()
raster.load("mapa_comprimido.k2r")
x_ini, x_fin = 500, 599
y_ini, y_fin = 500, 599
nivel_zoom = 3
print(f"Consultando X[{x_ini}:{x_fin}] Y[{y_ini}:{y_fin}] con Zoom Nivel {nivel_zoom}...")
inicio = time.time()
bloques = raster.get_blocks_window_zoom(x_ini, x_fin, y_ini, y_fin, nivel_zoom)
fin = time.time()
print(f"\n¡Consulta terminada en {fin - inicio:.5f} segundos!")
print(f"El motor K2-Raster (C++) devolvió {len(bloques)} bloques de geometría.")
print("\nMuestra de los bloques recibidos:")
for i, bloque in enumerate(bloques[:5]):
	print(f"Bloque {i+1} -> Fila: {bloque.fila}, Col: {bloque.columna}, Dimensión: {bloque.ancho}x{bloque.alto}, VALOR: {bloque.valor}")
