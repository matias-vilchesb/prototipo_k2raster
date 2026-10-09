import http.server
import socketserver
from socketserver import ThreadingMixIn
import json
import urllib.parse
import time
import os
import numpy as np
import k2raster_engine
from collections import OrderedDict

import sys

PORT = 8081

if len(sys.argv) > 1:
    RASTER_FILE = sys.argv[1]
elif os.path.exists("mapa_relieve_1152M.k2r"):
    RASTER_FILE = "mapa_relieve_1152M.k2r"
elif os.path.exists("mapa_comprimido.k2r"):
    RASTER_FILE = "mapa_comprimido.k2r"
else:
    k2r_files = [f for f in os.listdir(".") if f.endswith(".k2r")]
    if k2r_files:
        RASTER_FILE = k2r_files[0]
    else:
        print("No se encontró ningún archivo .k2r")
        print("para usar: python3 visor_web.py <archivo.k2r>")
        sys.exit(1)

class ThreadingHTTPServer(ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

print(f"Cargando dataset K2-Raster: {RASTER_FILE}...")
t0 = time.perf_counter()
raster = k2raster_engine.K2Raster()
raster.load(RASTER_FILE)
dt_load = (time.perf_counter() - t0) * 1000

rows = raster.get_rows()
cols = raster.get_cols()
total_cells = rows * cols
height = raster.get_height()
min_val = raster.get_min_value()
max_val = raster.get_max_value()

raster_info = {
    "rows": rows,
    "cols": cols,
    "total_cells": total_cells,
    "height": height,
    "min_val": min_val,
    "max_val": max_val,
    "archivo": os.path.basename(RASTER_FILE),
    "nombre": f"🗺️ {os.path.basename(RASTER_FILE)} ({total_cells:,} celdas)",
    "load_time_ms": dt_load
}
print(f" Mapa cargado en {dt_load:.2f} ms: {rows}x{cols} ({total_cells:,} celdas) [Árbol K2-Raster: {height} niveles]")

viewport_cache = OrderedDict()
MAX_CACHE_SIZE = 120

HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visor K2-Raster GIS</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body, html {
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #020617;
            font-family: 'Outfit', sans-serif;
        }
        #map-canvas {
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            display: block;
            cursor: grab;
            image-rendering: pixelated;
            user-select: none;
        }
        #map-canvas:active {
            cursor: grabbing;
        }
        /* HUD Flotante Minimalista: Tiempo de Respuesta + Cantidad de Celdas */
        .floating-hud {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 9999px;
            padding: 9px 18px;
            color: #f8fafc;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.55);
            z-index: 100;
            pointer-events: none;
            user-select: none;
            letter-spacing: 0.2px;
        }
        .hud-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 10px #22c55e;
        }
        .hud-time-val {
            color: #38bdf8;
            font-weight: 700;
        }
        .hud-cells-badge {
            color: #94a3b8;
            font-size: 11px;
            border-left: 1px solid rgba(255,255,255,0.15);
            padding-left: 10px;
        }
        .hud-divider {
            width: 1px;
            height: 14px;
            background: rgba(255, 255, 255, 0.15);
            margin: 0 2px;
            flex-shrink: 0;
        }
        .hud-cell-info {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            white-space: nowrap;
        }
        .hud-cell-coord {
            color: #e2e8f0;
            font-weight: 600;
        }
        .hud-cell-val {
            color: #f59e0b;
            font-weight: 700;
        }
        .hud-sublabel {
            color: #94a3b8;
        }

        /* Botones Flotantes de Zoom */
        .zoom-controls {
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 100;
        }
        .zoom-btn {
            width: 44px;
            height: 44px;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #f8fafc;
            font-family: 'JetBrains Mono', monospace;
            font-size: 20px;
            font-weight: 700;
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.18s ease;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
            user-select: none;
        }
        .zoom-btn:hover {
            background: #38bdf8;
            color: #0f172a;
            border-color: #38bdf8;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(56, 189, 248, 0.35);
        }
        .zoom-btn:active {
            transform: scale(0.95);
        }
    </style>
</head>
<body>
    <div class="floating-hud">
        <span class="hud-dot"></span>
        <span>Tiempo de respuesta: <strong class="hud-time-val" id="hud-time">0.0 ms</strong></span>
        <span class="hud-divider"></span>
        <span class="hud-cell-info">
            <span><span class="hud-sublabel">Celda:</span> <strong class="hud-cell-coord" id="cell-coords">—</strong></span>
            <span><span class="hud-sublabel">Valor:</span> <strong class="hud-cell-val" id="cell-val">—</strong></span>
        </span>
        <span class="hud-cells-badge" id="hud-cells"></span>
    </div>

    <div class="zoom-controls">
        <button class="zoom-btn" onclick="applyZoom(1.4)" title="Acercar (+)">+</button>
        <button class="zoom-btn" onclick="applyZoom(0.714)" title="Alejar (−)">−</button>
        <button class="zoom-btn" onclick="resetView()" title="Restablecer Vista (1x)" style="font-size: 15px;">⟲</button>
    </div>

    <canvas id="map-canvas"></canvas>

    <script>
        const canvas = document.getElementById('map-canvas');
        const ctx = canvas.getContext('2d', { alpha: false });
        const offCanvas = document.createElement('canvas');
        const offCtx = offCanvas.getContext('2d', { alpha: false });

        let rasterInfo = { rows: 0, cols: 0, min_val: 0, max_val: 255 };
        let centerX = 0;
        let centerY = 0;
        let zoomLevel = 1.0;
        let isDragging = false;
        let dragStart = { x: 0, y: 0 };
        let isFetching = false;
        let nextFetchRequested = false;

        let lastRawBuffer = null;
        let lastRows = 0;
        let lastCols = 0;

        // Paleta Google Maps Físico / Terreno Topográfico (256 niveles de sombreado y elevación)
        const TERRAIN_LUT_R = new Uint8Array(256);
        const TERRAIN_LUT_G = new Uint8Array(256);
        const TERRAIN_LUT_B = new Uint8Array(256);

        for (let i = 0; i < 256; i++) {
            if (i <= 106) {
                // Océanos azul marino profundo estilo Google Maps
                TERRAIN_LUT_R[i] = 26;
                TERRAIN_LUT_G[i] = 52;
                TERRAIN_LUT_B[i] = 92;
            } else {
                const norm = Math.max(0.0, Math.min(1.0, (i - 107) / 140.0));
                if (norm < 0.25) {
                    const k = norm / 0.25;
                    TERRAIN_LUT_R[i] = Math.round(48 + k * 82);
                    TERRAIN_LUT_G[i] = Math.round(128 + k * 42);
                    TERRAIN_LUT_B[i] = Math.round(78 - k * 28);
                } else if (norm < 0.55) {
                    const k = (norm - 0.25) / 0.30;
                    TERRAIN_LUT_R[i] = Math.round(130 + k * 70);
                    TERRAIN_LUT_G[i] = Math.round(170);
                    TERRAIN_LUT_B[i] = Math.round(50 + k * 60);
                } else if (norm < 0.80) {
                    const k = (norm - 0.55) / 0.25;
                    TERRAIN_LUT_R[i] = Math.round(200 - k * 55);
                    TERRAIN_LUT_G[i] = Math.round(170 - k * 75);
                    TERRAIN_LUT_B[i] = Math.round(110 - k * 50);
                } else {
                    const k = (norm - 0.80) / 0.20;
                    TERRAIN_LUT_R[i] = Math.round(145 + k * 105);
                    TERRAIN_LUT_G[i] = Math.round(95 + k * 155);
                    TERRAIN_LUT_B[i] = Math.round(60 + k * 190);
                }
            }
        }

        async function init() {
            const res = await fetch('/api/info');
            rasterInfo = await res.json();
            
            centerX = rasterInfo.rows / 2;
            centerY = rasterInfo.cols / 2;
            zoomLevel = 1.0;

            document.getElementById('hud-cells').textContent = `${(rasterInfo.rows * rasterInfo.cols).toLocaleString()} celdas`;

            resizeCanvas();
            renderViewport();
            setupInteractions();
            window.addEventListener('resize', () => {
                resizeCanvas();
                renderViewport();
            });
        }

        function resizeCanvas() {
            const w = window.innerWidth;
            const h = window.innerHeight;
            if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w;
                canvas.height = h;
            }
        }

        function applyZoom(factor) {
            zoomLevel = Math.max(1.0, Math.min(300.0, zoomLevel * factor));
            renderViewport();
        }

        function resetView() {
            centerX = rasterInfo.rows / 2;
            centerY = rasterInfo.cols / 2;
            zoomLevel = 1.0;
            renderViewport();
        }

        function redrawCanvas() {
            if (!lastRawBuffer || lastRows === 0 || lastCols === 0) return;

            offCanvas.width = lastCols;
            offCanvas.height = lastRows;
            const imgData = offCtx.createImageData(lastCols, lastRows);
            const dst = imgData.data;
            const src = lastRawBuffer;
            const numPixels = lastRows * lastCols;

            for (let i = 0; i < numPixels; i++) {
                const val = src[i];
                const dstIdx = i * 4;
                dst[dstIdx] = TERRAIN_LUT_R[val];
                dst[dstIdx + 1] = TERRAIN_LUT_G[val];
                dst[dstIdx + 2] = TERRAIN_LUT_B[val];
                dst[dstIdx + 3] = 255;
            }

            offCtx.putImageData(imgData, 0, 0);
            ctx.imageSmoothingEnabled = false;
            ctx.drawImage(offCanvas, 0, 0, canvas.width, canvas.height);
        }

        async function renderViewport() {
            if (isFetching) {
                nextFetchRequested = true;
                return;
            }
            isFetching = true;

            // Resolución uniforme sin reajustes ni parpadeos
            const targetW = 800;
            const targetH = 450;

            const spanX = rasterInfo.rows / zoomLevel;
            const spanY = rasterInfo.cols / zoomLevel;

            centerX = Math.max(spanX / 2, Math.min(rasterInfo.rows - spanX / 2, centerX));
            centerY = Math.max(spanY / 2, Math.min(rasterInfo.cols - spanY / 2, centerY));

            let x_ini = Math.round(centerX - spanX / 2);
            let x_fin = Math.round(centerX + spanX / 2);
            let y_ini = Math.round(centerY - spanY / 2);
            let y_fin = Math.round(centerY + spanY / 2);

            x_ini = Math.max(0, Math.min(rasterInfo.rows - 1, x_ini));
            x_fin = Math.max(0, Math.min(rasterInfo.rows - 1, x_fin));
            y_ini = Math.max(0, Math.min(rasterInfo.cols - 1, y_ini));
            y_fin = Math.max(0, Math.min(rasterInfo.cols - 1, y_fin));

            if (x_fin <= x_ini) x_fin = Math.min(rasterInfo.rows - 1, x_ini + 1);
            if (y_fin <= y_ini) y_fin = Math.min(rasterInfo.cols - 1, y_ini + 1);

            // Evita descender a las hojas y usa el promedio K2-Raster en el zoom
            const url = `/api/viewport_raw?x_ini=${x_ini}&x_fin=${x_fin}&y_ini=${y_ini}&y_fin=${y_fin}&w=${targetW}&h=${targetH}&avoid_leaves=1`;

            try {
                const response = await fetch(url);
                const queryTime = response.headers.get('X-Query-Time') || '0';
                const outRows = parseInt(response.headers.get('X-Rows') || '0');
                const outCols = parseInt(response.headers.get('X-Cols') || '0');

                const arrayBuffer = await response.arrayBuffer();
                lastRawBuffer = new Uint8Array(arrayBuffer);
                lastRows = outRows;
                lastCols = outCols;

                redrawCanvas();
                if (lastMousePos && !isDragging) {
                    updateHoverCell(lastMousePos.x, lastMousePos.y, false);
                }

                document.getElementById('hud-time').textContent = `${parseFloat(queryTime).toFixed(2)} ms`;
            } catch (err) {
                console.error(err);
            } finally {
                isFetching = false;
                if (nextFetchRequested) {
                    nextFetchRequested = false;
                    renderViewport();
                }
            }
        }

        let lastMousePos = null;
        let cellHoverTimeout = null;
        let lastRequestedCell = { row: -1, col: -1 };

        function updateHoverCell(clientX, clientY, allowFetch = true) {
            if (!rasterInfo.rows || !rasterInfo.cols) return;

            const rect = canvas.getBoundingClientRect();
            const mouseNormX = (clientY - rect.top) / rect.height;
            const mouseNormY = (clientX - rect.left) / rect.width;

            const spanX = rasterInfo.rows / zoomLevel;
            const spanY = rasterInfo.cols / zoomLevel;

            const curRow = Math.floor((centerX - spanX / 2) + mouseNormX * spanX);
            const curCol = Math.floor((centerY - spanY / 2) + mouseNormY * spanY);

            const coordsElem = document.getElementById('cell-coords');
            const valElem = document.getElementById('cell-val');

            if (curRow >= 0 && curRow < rasterInfo.rows && curCol >= 0 && curCol < rasterInfo.cols) {
                coordsElem.textContent = `[${curRow.toLocaleString()}, ${curCol.toLocaleString()}]`;

                // Valor preliminar instantáneo desde el búfer renderizado en pantalla (0 ms de latencia)
                if (lastRawBuffer && lastRows > 0 && lastCols > 0) {
                    const bufRow = Math.floor(mouseNormX * lastRows);
                    const bufCol = Math.floor(mouseNormY * lastCols);
                    if (bufRow >= 0 && bufRow < lastRows && bufCol >= 0 && bufCol < lastCols) {
                        valElem.textContent = lastRawBuffer[bufRow * lastCols + bufCol];
                    }
                }

                // Consulta precisa al árbol K2-Raster en C++
                if (allowFetch) {
                    clearTimeout(cellHoverTimeout);
                    lastRequestedCell = { row: curRow, col: curCol };
                    cellHoverTimeout = setTimeout(async () => {
                        const targetR = curRow;
                        const targetC = curCol;
                        try {
                            const res = await fetch(`/api/cell?row=${targetR}&col=${targetC}`);
                            const data = await res.json();
                            if (lastRequestedCell.row === data.row && lastRequestedCell.col === data.col && data.val !== null) {
                                valElem.textContent = data.val;
                            }
                        } catch (err) {}
                    }, 25);
                }
            } else {
                coordsElem.textContent = '—';
                valElem.textContent = '—';
            }
        }

        function setupInteractions() {
            window.addEventListener('wheel', (e) => {
                e.preventDefault();
                const rect = canvas.getBoundingClientRect();
                const mouseNormX = (e.clientY - rect.top) / rect.height;
                const mouseNormY = (e.clientX - rect.left) / rect.width;

                const spanX = rasterInfo.rows / zoomLevel;
                const spanY = rasterInfo.cols / zoomLevel;

                const targetRow = (centerX - spanX / 2) + mouseNormX * spanX;
                const targetCol = (centerY - spanY / 2) + mouseNormY * spanY;

                const zoomFactor = e.deltaY < 0 ? 1.3 : 0.77;
                const newZoom = Math.max(1.0, Math.min(300.0, zoomLevel * zoomFactor));

                if (newZoom !== zoomLevel) {
                    zoomLevel = newZoom;
                    const newSpanX = rasterInfo.rows / zoomLevel;
                    const newSpanY = rasterInfo.cols / zoomLevel;

                    centerX = targetRow + (0.5 - mouseNormX) * newSpanX;
                    centerY = targetCol + (0.5 - mouseNormY) * newSpanY;

                    renderViewport();
                    updateHoverCell(e.clientX, e.clientY, true);
                }
            }, { passive: false });

            window.addEventListener('mousedown', (e) => {
                if (e.button !== 0) return;
                isDragging = true;
                dragStart = { x: e.clientX, y: e.clientY };
            });

            window.addEventListener('mousemove', (e) => {
                lastMousePos = { x: e.clientX, y: e.clientY };
                if (isDragging) {
                    const dx = e.clientX - dragStart.x;
                    const dy = e.clientY - dragStart.y;
                    dragStart = { x: e.clientX, y: e.clientY };

                    const spanX = rasterInfo.rows / zoomLevel;
                    const spanY = rasterInfo.cols / zoomLevel;

                    centerX -= (dy / canvas.height) * spanX;
                    centerY -= (dx / canvas.width) * spanY;

                    renderViewport();
                    updateHoverCell(e.clientX, e.clientY, false);
                } else {
                    updateHoverCell(e.clientX, e.clientY, true);
                }
            });

            window.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    renderViewport();
                    if (lastMousePos) {
                        updateHoverCell(lastMousePos.x, lastMousePos.y, true);
                    }
                }
            });

            canvas.addEventListener('mouseleave', () => {
                lastMousePos = null;
                document.getElementById('cell-coords').textContent = '—';
                document.getElementById('cell-val').textContent = '—';
            });

            window.addEventListener('dblclick', () => {
                resetView();
            });
        }

        init();
    </script>
</body>
</html>
"""

class RasterViewerHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/api/info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(raster_info).encode("utf-8"))

        elif path == "/api/viewport_raw":
            r_rows = raster_info["rows"]
            r_cols = raster_info["cols"]
            x_ini = int(query.get("x_ini", [0])[0])
            x_fin = int(query.get("x_fin", [r_rows - 1])[0])
            y_ini = int(query.get("y_ini", [0])[0])
            y_fin = int(query.get("y_fin", [r_cols - 1])[0])
            target_w = int(query.get("w", [800])[0])
            target_h = int(query.get("h", [450])[0])
            avoid_leaves = query.get("avoid_leaves", ["1"])[0] in ("1", "true", "True")

            cache_key = (x_ini, x_fin, y_ini, y_fin, target_w, target_h, avoid_leaves)

            if cache_key in viewport_cache:
                raw_bytes, out_rows, out_cols = viewport_cache[cache_key]
                viewport_cache.move_to_end(cache_key)
                dt_ms = 0.0
            else:
                t0 = time.perf_counter()
                vp = raster.get_viewport(x_ini, x_fin, y_ini, y_fin, target_width=target_w, target_height=target_h, avoid_leaves=avoid_leaves)
                dt_ms = (time.perf_counter() - t0) * 1000

                out_rows = vp["rows"]
                out_cols = vp["cols"]

                if out_rows > 0 and out_cols > 0:
                    raw_bytes = np.array(vp["data"], dtype=np.uint8).tobytes()
                else:
                    raw_bytes = b""

                if len(viewport_cache) >= MAX_CACHE_SIZE:
                    viewport_cache.popitem(last=False)
                viewport_cache[cache_key] = (raw_bytes, out_rows, out_cols)

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("X-Query-Time", f"{dt_ms:.2f}")
            self.send_header("X-Rows", str(out_rows))
            self.send_header("X-Cols", str(out_cols))
            self.end_headers()
            self.wfile.write(raw_bytes)

        elif path == "/api/cell":
            r_rows = raster_info["rows"]
            r_cols = raster_info["cols"]
            row = int(query.get("row", [-1])[0])
            col = int(query.get("col", [-1])[0])

            if 0 <= row < r_rows and 0 <= col < r_cols:
                t0 = time.perf_counter()
                val = int(raster.get_cell(row, col))
                dt_us = (time.perf_counter() - t0) * 1e6
            else:
                val = None
                dt_us = 0.0

            res_obj = {
                "row": row,
                "col": col,
                "val": val,
                "time_us": round(dt_us, 1)
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(res_obj).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    with ThreadingHTTPServer(("", PORT), RasterViewerHandler) as httpd:
        print("================================================================")
        print(f" Funcionando correctamente")
        print(f"   http://localhost:{PORT}")
        print("================================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
