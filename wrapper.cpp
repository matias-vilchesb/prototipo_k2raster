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
        // Tu nueva función de zoom corregida
        .def("get_values_window_zoom", [](k2raster::k2_raster<int> &self, int x_ini, int x_fin, int y_ini, int y_fin, int zoom) {
            std::vector<int> resultado;
            self.get_values_window_zoom(x_ini, x_fin, y_ini, y_fin, zoom, resultado);
            return resultado;
        })
        .def("get_blocks_window_zoom", &k2raster::k2_raster<int>::get_blocks_window_zoom, "Obtiene bloques con LOD");
}
