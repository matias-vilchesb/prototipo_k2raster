#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <fstream>
#include "include/k2_raster.hpp"
namespace py = pybind11;

// Exponemos la clase k2_raster
PYBIND11_MODULE(k2raster_engine, m) {
     // Enseñar a Python la estructura BloqueLOD
    py::class_<k2raster::BloqueLOD>(m, "BloqueLOD")
        .def_readonly("fila", &k2raster::BloqueLOD::fila)
        .def_readonly("columna", &k2raster::BloqueLOD::columna)
        .def_readonly("alto", &k2raster::BloqueLOD::alto)
        .def_readonly("ancho", &k2raster::BloqueLOD::ancho)
        .def_readonly("valor", &k2raster::BloqueLOD::valor);

    py::class_<k2raster::k2_raster<int>>(m, "K2Raster")
        .def(py::init<>())
        // Función para cargar el archivo .k2r desde Python
        .def("load", [](k2raster::k2_raster<int>& self, const std::string& filename) {
            std::ifstream in(filename, std::ios::binary);
            if (!in.is_open()) throw std::runtime_error("No se pudo abrir el archivo");
            self.load(in);
            in.close();
        })
        .def("decompress_to_bin", [](k2raster::k2_raster<int>& self, const std::string& out_path) {
            std::vector<int> values;
            size_t rows, cols;
            self.decompress(values, rows, cols);
            std::ofstream out(out_path, std::ios::binary);
            out.write(reinterpret_cast<const char*>(values.data()), values.size() * sizeof(int));
            out.close();
            return true;
        })
        // Consultar una celda individual
        .def("get_cell", [](const k2raster::k2_raster<int>& self, size_t row, size_t col) {
            return self.get_cell(row, col);
        })
        // Consultar una celda evitando descender a las hojas (usando promedio del nodo intermedio)
        .def("get_cell_promedio", [](const k2raster::k2_raster<int>& self, size_t row, size_t col, ushort target_level) {
            return self.get_cell_promedio(row, col, target_level);
        }, py::arg("row"), py::arg("col"), py::arg("target_level") = 0)
        // Metadatos de la matriz
        .def("get_rows", [](const k2raster::k2_raster<int>& self) {
            return (size_t)self.m_real_size_x;
        })
        .def("get_cols", [](const k2raster::k2_raster<int>& self) {
            return (size_t)self.m_real_size_y;
        })
        .def("get_height", [](const k2raster::k2_raster<int>& self) {
            return (ushort)self.height;
        })
        .def("get_min_value", [](const k2raster::k2_raster<int>& self) {
            return self.min_value;
        })
        .def("get_max_value", [](const k2raster::k2_raster<int>& self) {
            return self.max_value;
        })
        // Muestreo con paso regular (stride)
        .def("get_values_sampled", [](const k2raster::k2_raster<int>& self,
                                      size_t x_ini, size_t x_fin,
                                      size_t y_ini, size_t y_fin,
                                      size_t step_x, size_t step_y,
                                      bool avoid_leaves) {
            std::vector<int> resultado;
            if (self.m_real_size_x == 0 || self.m_real_size_y == 0) return resultado;
            if (x_ini >= self.m_real_size_x || y_ini >= self.m_real_size_y) return resultado;
            
            x_fin = std::min(x_fin, (size_t)(self.m_real_size_x - 1));
            y_fin = std::min(y_fin, (size_t)(self.m_real_size_y - 1));
            if (step_x == 0) step_x = 1;
            if (step_y == 0) step_y = 1;

            size_t n_rows = (x_fin >= x_ini) ? ((x_fin - x_ini) / step_x + 1) : 0;
            size_t n_cols = (y_fin >= y_ini) ? ((y_fin - y_ini) / step_y + 1) : 0;
            resultado.reserve(n_rows * n_cols);

            for (size_t x = x_ini; x <= x_fin; x += step_x) {
                for (size_t y = y_ini; y <= y_fin; y += step_y) {
                    if (avoid_leaves) {
                        resultado.push_back(self.get_cell_promedio(x, y));
                    } else {
                        resultado.push_back(self.get_cell(x, y));
                    }
                }
            }
            return resultado;
        }, py::arg("x_ini"), py::arg("x_fin"), py::arg("y_ini"), py::arg("y_fin"), py::arg("step_x") = 1, py::arg("step_y") = 1, py::arg("avoid_leaves") = false)
        // Muestreo adaptativo para Viewport / Pantalla de visualización
        .def("get_viewport", [](const k2raster::k2_raster<int>& self,
                                size_t x_ini, size_t x_fin,
                                size_t y_ini, size_t y_fin,
                                size_t target_width, size_t target_height,
                                bool avoid_leaves, ushort target_level) {
            py::dict res;
            std::vector<int> resultado;
            if (self.m_real_size_x == 0 || self.m_real_size_y == 0 || target_width == 0 || target_height == 0) {
                res["data"] = resultado;
                res["rows"] = 0;
                res["cols"] = 0;
                res["step_x"] = 1;
                res["step_y"] = 1;
                return res;
            }

            if (x_ini >= self.m_real_size_x) x_ini = self.m_real_size_x - 1;
            if (y_ini >= self.m_real_size_y) y_ini = self.m_real_size_y - 1;
            x_fin = std::min(x_fin, (size_t)(self.m_real_size_x - 1));
            y_fin = std::min(y_fin, (size_t)(self.m_real_size_y - 1));

            size_t win_h = (x_fin >= x_ini) ? (x_fin - x_ini + 1) : 1;
            size_t win_w = (y_fin >= y_ini) ? (y_fin - y_ini + 1) : 1;

            size_t step_x = std::max((size_t)1, win_h / target_height);
            size_t step_y = std::max((size_t)1, win_w / target_width);

            size_t out_rows = 0;
            size_t out_cols = 0;

            size_t block_s = self.k2 > 0 ? (size_t)self.k2 : 2;
            size_t last_bx = (size_t)-1;
            size_t last_by = (size_t)-1;
            int last_val = 0;

            for (size_t x = x_ini; x <= x_fin; x += step_x) {
                out_rows++;
                size_t current_cols = 0;
                for (size_t y = y_ini; y <= y_fin; y += step_y) {
                    current_cols++;
                    if (avoid_leaves) {
                        size_t bx = x / block_s;
                        size_t by = y / block_s;
                        if (bx == last_bx && by == last_by) {
                            resultado.push_back(last_val);
                        } else {
                            last_val = self.get_cell_promedio(x, y, target_level);
                            last_bx = bx;
                            last_by = by;
                            resultado.push_back(last_val);
                        }
                    } else {
                        resultado.push_back(self.get_cell(x, y));
                    }
                }
                if (out_cols == 0) out_cols = current_cols;
            }

            res["data"] = resultado;
            res["rows"] = out_rows;
            res["cols"] = out_cols;
            res["step_x"] = step_x;
            res["step_y"] = step_y;
            return res;
        }, py::arg("x_ini"), py::arg("x_fin"), py::arg("y_ini"), py::arg("y_fin"), py::arg("target_width") = 100, py::arg("target_height") = 100, py::arg("avoid_leaves") = true, py::arg("target_level") = 0)
        // Función de zoom corregida existente
        .def("get_values_window_zoom", [](k2raster::k2_raster<int> &self, int x_ini, int x_fin, int y_ini, int y_fin, int zoom) {
            std::vector<int> resultado;
            self.get_values_window_zoom(x_ini, x_fin, y_ini, y_fin, zoom, resultado);
            return resultado;
        })
        .def("get_blocks_window_zoom", &k2raster::k2_raster<int>::get_blocks_window_zoom, "Obtiene bloques con LOD");
}

