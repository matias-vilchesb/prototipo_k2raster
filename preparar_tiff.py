import sys
import rasterio
import numpy as np
import time

filename = sys.argv[1] if len(sys.argv) > 1 else "/home/ubb/Descargas/ETOPO_2022_v1_30s_N90W180_surface.tif"
output_bin = sys.argv[2] if len(sys.argv) > 2 else "etopo2022.bin"

try:
    print(f"Abriendo raster: {filename}...")
    t0 = time.time()
    with rasterio.open(filename) as src:
        filas = src.height
        columnas = src.width
        total_celdas = filas * columnas

        print(f"--- ¡Metadatos detectados en {filename}! ---")
        print(f"Filas: {filas:,}")
        print(f"Columnas: {columnas:,}")
        print(f"Total de celdas: {total_celdas:,}")

        chunk_rows = 2048
        min_val = float("inf")
        max_val = float("-inf")

        with open(output_bin, "wb") as f_out:
            for row_start in range(0, filas, chunk_rows):
                h = min(chunk_rows, filas - row_start)
                window = rasterio.windows.Window(0, row_start, columnas, h)
                data = src.read(1, window=window)

                # Si es flotante, redondear a entero más cercano manteniendo cotas en metros
                if np.issubdtype(data.dtype, np.floating):
                    # Reemplazar NaN si existiera
                    data = np.nan_to_num(data, nan=0.0)
                    chunk_int = np.rint(data).astype(np.int32)
                else:
                    chunk_int = data.astype(np.int32)

                c_min = int(chunk_int.min())
                c_max = int(chunk_int.max())
                if c_min < min_val: min_val = c_min
                if c_max > max_val: max_val = c_max

                f_out.write(chunk_int.tobytes())

                prog = (row_start + h) / filas * 100
                print(f"  Procesando... {prog:5.1f}% ({row_start + h:,}/{filas:,} filas)", end="\r")

        print(f"\nDatos crudos int32 guardados en: {output_bin} ({time.time() - t0:.1f}s)")
        print(f"Cota mínima: {min_val} m, Cota máxima: {max_val} m")

        print("\n--- PASO FINAL ---")
        print("Comando de compresión K2-Raster:")
        print(f"./build/bin/encode_k2r {output_bin} {filas} {columnas} etopo2022.k2r")

except FileNotFoundError:
    print(f"Error: No se encontró el archivo '{filename}'.")