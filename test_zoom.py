import k2raster_engine

print("Cargando motor k2-raster...")
raster = k2raster_engine.K2Raster()

print("Cargando matriz k2-raster en memoria...")
raster.load("mapa_comprimido.k2r") 
print("¡Archivo cargado con éxito!")

#Apuntamos a la coordenada X=600, Y=600 (Abajo a la derecha, puro mar oscuro)
x_ini, x_fin = 600, 609
y_ini, y_fin = 600, 609

#Nivel 10 es la profundidad máxima (hojas del árbol) para ver el dato crudo
nivel_zoom = 10 

print(f"Consultando ventana X[{x_ini}:{x_fin}] Y[{y_ini}:{y_fin}] al nivel de zoom {nivel_zoom}...")

#Ejecutamos la consulta directa a la memoria de C++
resultado = raster.get_values_window_zoom(x_ini, x_fin, y_ini, y_fin, nivel_zoom)

print("¡Consulta terminada!")
print(f"Cantidad de valores recuperados: {len(resultado)}")
print("Valores de la matriz:", resultado)