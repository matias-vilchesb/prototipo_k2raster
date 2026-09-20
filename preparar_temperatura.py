import os
import urllib.request
import zipfile
import io
import rasterio
import numpy as np
import subprocess

OFFSET = 90.0  # Para que -90°C sea 0
SCALE = 10.0   # 1 decimal de precisión (0.1 °C)

def descargar_worldclim():
    os.makedirs("climate_data", exist_ok=True)
    target_tif = "climate_data/wc2.1_10m_tavg_01.tif"
    if not os.path.exists(target_tif):
        url = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_tavg.zip"
        print(f"Descargando dataset de temperatura WorldClim (~37MB)...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                z.extractall("climate_data")
        print("Dataset descargado y extraído en climate_data/")
    else:
        print("Archivos de WorldClim ya presentes en climate_data/")

def encode_temp_matrix(temp_matrix, nodata_mask, out_k2r_path):
    rows, cols = temp_matrix.shape
    out_mat = np.zeros((rows, cols), dtype=np.int32)
    
    # Solo pixeles válidos
    valid = ~nodata_mask & ~np.isnan(temp_matrix)
    scaled = np.round((temp_matrix[valid] + OFFSET) * SCALE) + 1  # 0 reservado para nodata/océano
    out_mat[valid] = scaled.astype(np.int32)
    
    bin_path = out_k2r_path.replace(".k2r", ".bin")
    out_mat.tofile(bin_path)
    
    cmd = ["./build/bin/encode_k2r", bin_path, str(rows), str(cols), out_k2r_path]
    subprocess.run(cmd, check=True)
    print(f"-> Generado: {out_k2r_path} ({os.path.getsize(out_k2r_path):,} bytes) | Min: {temp_matrix[valid].min():.1f}°C, Max: {temp_matrix[valid].max():.1f}°C")

def main():
    descargar_worldclim()
    
    # 1. Enero (Invierno hemisferio norte, verano hemisferio sur)
    with rasterio.open("climate_data/wc2.1_10m_tavg_01.tif") as src:
        data_01 = src.read(1)
        nodata_01 = (data_01 == src.nodata)
        print("Comprimiendo Temperatura Global Enero...")
        encode_temp_matrix(data_01, nodata_01, "mapa_temperatura_enero.k2r")

    # 2. Julio (Verano hemisferio norte, invierno hemisferio sur)
    with rasterio.open("climate_data/wc2.1_10m_tavg_07.tif") as src:
        data_07 = src.read(1)
        nodata_07 = (data_07 == src.nodata)
        print("Comprimiendo Temperatura Global Julio...")
        encode_temp_matrix(data_07, nodata_07, "mapa_temperatura_julio.k2r")

    # 3. Promedio Anual (12 meses)
    print("Calculando promedio anual de 12 meses...")
    all_months = []
    for m in range(1, 13):
        with rasterio.open(f"climate_data/wc2.1_10m_tavg_{m:02d}.tif") as src:
            d = src.read(1)
            d[d == src.nodata] = np.nan
            all_months.append(d)
    annual_mean = np.nanmean(np.stack(all_months, axis=0), axis=0)
    annual_nodata = np.isnan(annual_mean)
    print("Comprimiendo Temperatura Global Promedio Anual...")
    encode_temp_matrix(annual_mean, annual_nodata, "mapa_temperatura_anual.k2r")
    print("\n¡Todo listo! Los mapas .k2r están generados y disponibles.")

if __name__ == "__main__":
    main()
