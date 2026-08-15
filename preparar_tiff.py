import rasterio
import numpy as np

filename = "RGB.byte.tif"

try:
    with rasterio.open(filename) as src:
        # Leemos la primera capa del mapa
        banda = src.read(1)
        filas, columnas = banda.shape

        print("--- ¡Extracción exitosa! ---")
        print(f"Filas detectadas: {filas}")
        print(f"Columnas detectadas: {columnas}")

        output_bin = "matriz_cruda.bin"
        # Convertimos a enteros de 32 bits para que C++ lo entienda a la perfección
        banda.astype(np.int32).tofile(output_bin)
        print(f"Datos crudos guardados en: {output_bin}")

        print("\n--- PASO FINAL ---")
        print("Copia y pega este comando en tu terminal para comprimirlo en C++:")
        print(f"./bin/encode_k2r {output_bin} {filas} {columnas} mapa_comprimido.k2r")

except FileNotFoundError:
    print(f"Error: No se encontró el archivo {filename}. Asegúrate de haberlo descargado con wget.")