import k2raster_engine

print("Cargando motor k2-raster...")
raster = k2raster_engine.K2Raster()

print("Cargando matriz k2-raster en memoria...")
raster.load("mapa_comprimido.k2r") 
print("¡Archivo cargado con éxito!")

# Apuntamos a una ventana representativa
x_ini, x_fin = 600, 609
y_ini, y_fin = 600, 609

# 1. Consulta directa a máxima resolución (píxel a píxel)
print(f"\n1. Consultando ventana X[{x_ini}:{x_fin}] Y[{y_ini}:{y_fin}] a resolución nativa...")
resultado_nativo = raster.get_values_sampled(x_ini, x_fin, y_ini, y_fin, step_x=1, step_y=1)
print(f"Valores recuperados ({len(resultado_nativo)} celdas):", resultado_nativo)

# 2. Consulta con muestreo para Viewport (ej. ver todo el mapa adaptado a pantalla de 50x50)
print(f"\n2. Consultando vista global completa adaptada a pantalla (50x50)...")
viewport = raster.get_viewport(0, raster.get_rows()-1, 0, raster.get_cols()-1, target_width=50, target_height=50)
print(f"Dimensiones devueltas: {viewport['rows']}x{viewport['cols']} (Paso: X={viewport['step_x']}, Y={viewport['step_y']})")
print(f"Muestra de los primeros 10 valores de la vista global:", viewport['data'][:10])