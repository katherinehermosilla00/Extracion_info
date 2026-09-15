package com.example.toursearch.service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.example.toursearch.entity.Actividad;
import com.example.toursearch.entity.OperadorTuristico;
import com.example.toursearch.repository.ActividadRepository;

@Service
public class ActividadService {

    @Autowired
    private ActividadRepository actividadRepository;

    // =========================================================
    // OBTENER ACTIVIDAD POR ID
    // =========================================================
    public Optional<Actividad> obtenerPorId(Long id) {
        return actividadRepository.findById(id);
    }

    // =========================================================
    // OBTENER TODAS LAS ACTIVIDADES ACTIVAS
    // =========================================================
    public List<Actividad> obtenerTodas() {
        return actividadRepository.findAll()
                .stream()
                .filter(Actividad::isActivo)
                .toList();
    }

    // =========================================================
    // OBTENER ACTIVIDADES POR OPERADOR
    // =========================================================
    public List<Actividad> obtenerPorOperador(Long operadorTuristicoId) {
        return actividadRepository
                .findByOperadorTuristicoIdAndActivoTrue(
                        operadorTuristicoId
                );
    }

    // =========================================================
    // REVISAR SI EXISTE POR OPERADOR + NOMBRE
    // =========================================================
    public Optional<Actividad> existeParaOperador(
            Long operadorTuristicoId,
            String nombre) {

        return actividadRepository
                .findByOperadorTuristicoIdAndNombreIgnoreCaseAndActivoTrue(
                        operadorTuristicoId,
                        nombre
                );
    }

    // =========================================================
    // REVISAR SI EXISTE POR URL DE ORIGEN
    // =========================================================
    public Optional<Actividad> existePorUrlOrigen(String urlOrigen) {
        return actividadRepository.findByUrlOrigenAndActivoTrue(urlOrigen);
    }

    // =========================================================
    // BUSCAR ACTIVIDADES POR TEXTO
    // =========================================================
    public List<Actividad> buscarPorTexto(String texto) {
        return actividadRepository.buscarPorTextoEnNombre(texto);
    }

    // =========================================================
    // GUARDAR ACTIVIDAD
    // =========================================================
    public Actividad guardar(Actividad actividad) {
        return actividadRepository.save(actividad);
    }

    // =========================================================
    // GUARDAR ACTIVIDAD DESDE EL SCRAPER
    // =========================================================
    public Actividad guardarDesdeExtraccion(
            Actividad datosExtraidos,
            OperadorTuristico operador) {

        datosExtraidos.setOperadorTuristico(operador);
        datosExtraidos.setActivo(true);

        return actividadRepository.save(datosExtraidos);
    }

    // =========================================================
    // ACTUALIZAR ACTIVIDAD
    // =========================================================
    public Actividad actualizar(Long id, Actividad datos) {

        Actividad existente = actividadRepository
                .findById(id)
                .orElseThrow(
                        () -> new RuntimeException(
                                "Actividad no encontrada con id: " + id
                        )
                );

        // =====================================================
        // DATOS GENERALES
        // =====================================================

        existente.setNombre(
                datos.getNombre()
        );

        existente.setDescripcion(
                datos.getDescripcion()
        );

        existente.setUbicacion(
                datos.getUbicacion()
        );

        existente.setDestino(
                datos.getDestino()
        );

        existente.setDuracion(
                datos.getDuracion()
        );

        // =====================================================
        // EDADES
        // =====================================================

        existente.setEdadMinima(
                datos.getEdadMinima()
        );

        existente.setEdadMaxima(
                datos.getEdadMaxima()
        );

        // =====================================================
        // IDIOMAS
        // =====================================================

        existente.setIdiomas(
                datos.getIdiomas() != null
                        ? new ArrayList<>(datos.getIdiomas())
                        : new ArrayList<>()
        );

        // =====================================================
        // IMÁGENES
        // Se mantienen por compatibilidad.
        // =====================================================

        existente.setImagenes(
                datos.getImagenes() != null
                        ? new ArrayList<>(datos.getImagenes())
                        : new ArrayList<>()
        );

        // =====================================================
        // HIGHLIGHTS
        // =====================================================

        existente.setHighlights(
                datos.getHighlights() != null
                        ? new ArrayList<>(datos.getHighlights())
                        : new ArrayList<>()
        );

        // =====================================================
        // ITINERARIO
        // =====================================================

        existente.setItinerario(
                datos.getItinerario() != null
                        ? new ArrayList<>(datos.getItinerario())
                        : new ArrayList<>()
        );

        // =====================================================
        // HORARIOS
        // =====================================================

        existente.setHorarios(
                datos.getHorarios() != null
                        ? new ArrayList<>(datos.getHorarios())
                        : new ArrayList<>()
        );

        // =====================================================
        // RESTRICCIONES
        // =====================================================

        existente.setRestricciones(
                datos.getRestricciones() != null
                        ? new ArrayList<>(datos.getRestricciones())
                        : new ArrayList<>()
        );

        // =====================================================
        // URL
        // =====================================================

        existente.setUrlOrigen(
                datos.getUrlOrigen()
        );

        // =====================================================
        // OPERADOR
        // Normalmente se mantiene el existente.
        // Si llega uno válido, se actualiza.
        // =====================================================

        if (datos.getOperadorTuristico() != null) {
            existente.setOperadorTuristico(
                    datos.getOperadorTuristico()
            );
        }

        // =====================================================
        // ESTADO
        // =====================================================

        existente.setActivo(
                datos.isActivo()
        );

        return actividadRepository.save(existente);
    }

    // =========================================================
    // DESACTIVAR ACTIVIDAD
    // =========================================================
    public void desactivar(Long id) {

        Actividad existente = actividadRepository
                .findById(id)
                .orElseThrow(
                        () -> new RuntimeException(
                                "Actividad no encontrada con id: " + id
                        )
                );

        existente.setActivo(false);

        actividadRepository.save(existente);
    }

    // =========================================================
    // ELIMINAR ACTIVIDAD DEFINITIVAMENTE
    // =========================================================
    public void eliminar(Long id) {

        Actividad existente = actividadRepository
                .findById(id)
                .orElseThrow(
                        () -> new RuntimeException(
                                "Actividad no encontrada con id: " + id
                        )
                );

        actividadRepository.delete(existente);
    }
}