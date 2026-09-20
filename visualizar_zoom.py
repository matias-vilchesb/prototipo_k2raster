import k2raster_engine
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import rasterio
import time
import os

print("==================================================")
print("  GENERANDO REPORTE VISUAL: K2-RASTER Y ZOOMS")
print("==================================================")

# 1. Cargar el motor y el mapa comprimido
raster = k2raster_engine.K2Raster()
raster.load("mapa_comprimido.k2r")

rows = raster.get_rows()
cols = raster.get_cols()
print(f"Dimensiones del mapa K2-Raster: {rows} filas x {cols} columnas")

# 2. Cargar el TIF original como referencia de verdad
tif_disponible = os.path.exists("RGB.byte.tif")
tif_data = None
if tif_disponible:
    with rasterio.open("RGB.byte.tif") as src:
        tif_data = src.read(1)
    print("Archivo TIF original cargado para comparación.")

# 3. Definir regiones de prueba para Zoom
# CASO A: Vista Global con get_viewport (adaptado a resolución de pantalla 200x200)
t0 = time.perf_counter()
vp_global = raster.get_viewport(0, rows - 1, 0, cols - 1, target_width=200, target_height=200)
t_global = (time.perf_counter() - t0) * 1000
data_global = np.array(vp_global["data"]).reshape((vp_global["rows"], vp_global["cols"]))

# CASO B: Vista Regional (Zoom 5)
x1_reg, x2_reg = 200, 500
y1_reg, y2_reg = 200, 500
t0 = time.perf_counter()
vp_regional = raster.get_viewport(x1_reg, x2_reg, y1_reg, y2_reg, target_width=300, target_height=300)
t_regional = (time.perf_counter() - t0) * 1000
data_regional = np.array(vp_regional["data"]).reshape((vp_regional["rows"], vp_regional["cols"]))

# CASO C: Vista Detallada Píxel a Píxel (Zoom 10)
x1_loc, x2_loc = 100, 180
y1_loc, y2_loc = 300, 380
t0 = time.perf_counter()
raw_local = raster.get_values_sampled(x1_loc, x2_loc, y1_loc, y2_loc, step_x=1, step_y=1)
t_local = (time.perf_counter() - t0) * 1000
data_local = np.array(raw_local).reshape((x2_loc - x1_loc + 1, y2_loc - y1_loc + 1))

# 4. Crear la figura comparativa con Matplotlib
fig, axes = plt.subplots(2, 2, figsize=(14, 12))
plt.subplots_adjust(wspace=0.3, hspace=0.35)

cmap_selected = "viridis"  # Paleta de colores GIS de alto contraste

# --- Panel 1: Vista Global Completa (Submuestreada al vuelo) ---
ax1 = axes[0, 0]
im1 = ax1.imshow(data_global, cmap=cmap_selected, origin="upper", aspect="auto", extent=[0, cols, rows, 0])
ax1.set_title(f"1. Vista Global (get_viewport)\nResolución: {vp_global['rows']}x{vp_global['cols']} | Tiempo: {t_global:.2f} ms", fontsize=11, fontweight="bold")
ax1.set_xlabel("Columnas (Y)")
ax1.set_ylabel("Filas (X)")
fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04, label="Valor (0 - 255)")

# Dibujamos recuadros sobre la vista global indicando dónde están los zooms
rect_reg = patches.Rectangle((y1_reg, x1_reg), y2_reg - y1_reg, x2_reg - x1_reg, linewidth=2, edgecolor='cyan', facecolor='none', linestyle='--', label='Región Zoom 5')
rect_loc = patches.Rectangle((y1_loc, x1_loc), y2_loc - y1_loc, x2_loc - x1_loc, linewidth=2, edgecolor='red', facecolor='none', label='Detalle Zoom 10')
ax1.add_patch(rect_reg)
ax1.add_patch(rect_loc)
ax1.legend(loc="upper right", fontsize=9, framealpha=0.8)

# --- Panel 2: Vista Regional (Zoom 5) ---
ax2 = axes[0, 1]
im2 = ax2.imshow(data_regional, cmap=cmap_selected, origin="upper", aspect="auto", extent=[y1_reg, y2_reg, x2_reg, x1_reg])
ax2.set_title(f"2. Vista Regional (Zoom 5)\nVentana: X[{x1_reg}:{x2_reg}], Y[{y1_reg}:{y2_reg}] | Tiempo: {t_regional:.2f} ms", fontsize=11, fontweight="bold")
ax2.set_xlabel("Columnas (Y)")
ax2.set_ylabel("Filas (X)")
fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04, label="Valor (0 - 255)")

# --- Panel 3: Vista Detallada Píxel a Píxel (Zoom 10) ---
ax3 = axes[1, 0]
im3 = ax3.imshow(data_local, cmap=cmap_selected, origin="upper", aspect="auto", extent=[y1_loc, y2_loc, x2_loc, x1_loc])
ax3.set_title(f"3. Vista Detallada Nativa (Zoom 10 - Píxel a Píxel)\nVentana: X[{x1_loc}:{x2_loc}], Y[{y1_loc}:{y2_loc}] | Tiempo: {t_local:.2f} ms", fontsize=11, fontweight="bold")
ax3.set_xlabel("Columnas (Y)")
ax3.set_ylabel("Filas (X)")
fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04, label="Valor (0 - 255)")

# --- Panel 4: Comparación con TIF original (Verificación de fidelidad) ---
ax4 = axes[1, 1]
if tif_disponible:
    # Mostramos exactamente la misma región de detalle del TIF original
    tif_crop = tif_data[x1_loc:x2_loc+1, y1_loc:y2_loc+1]
    im4 = ax4.imshow(tif_crop, cmap=cmap_selected, origin="upper", aspect="auto", extent=[y1_loc, y2_loc, x2_loc, x1_loc])
    # Verificamos si son 100% idénticos
    coincidencia_exacta = np.array_equal(data_local, tif_crop)
    estado = "100% Idéntico (Sin pérdida)" if coincidencia_exacta else "Diferencias detectadas"
    ax4.set_title(f"4. Original GeoTIFF (Misma ventana Zoom 10)\nFidelidad con K2-Raster: {estado}", fontsize=11, fontweight="bold", color="darkgreen" if coincidencia_exacta else "red")
    ax4.set_xlabel("Columnas (Y)")
    ax4.set_ylabel("Filas (X)")
    fig.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04, label="Valor TIF (0 - 255)")
else:
    ax4.text(0.5, 0.5, "Archivo TIF no disponible para comparación", ha='center', va='center')

output_img = "comparacion_visual_zoom.png"
plt.suptitle("Validación Visual y Rendimiento del Motor K2-Raster", fontsize=15, fontweight="bold", y=0.98)
plt.savefig(output_img, dpi=180, bbox_inches='tight')
print(f"\n¡Gráfico generado con éxito! Guardado en: {output_img}")
