package com.example.toursearch.controller;

import java.util.List;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.example.toursearch.entity.Actividad;
import com.example.toursearch.service.ActividadService;

@CrossOrigin(origins = "*")
@RestController
@RequestMapping("/api/actividades")
public class ActividadController {

    @Autowired
    private ActividadService actividadService;

    // =========================================================
    // LISTAR TODAS LAS ACTIVIDADES ACTIVAS
    // GET /api/actividades
    // =========================================================
    @GetMapping
    public ResponseEntity<List<Actividad>> obtenerTodas() {
        return ResponseEntity.ok(actividadService.obtenerTodas());
    }

    // =========================================================
    // OBTENER ACTIVIDAD POR ID
    // GET /api/actividades/{id}
    // =========================================================
    @GetMapping("/{id}")
    public ResponseEntity<Actividad> obtenerPorId(@PathVariable Long id) {

        Optional<Actividad> actividad = actividadService.obtenerPorId(id);

        return actividad
                .map(ResponseEntity::ok)
                .orElseGet(() ->
                        ResponseEntity
                                .status(HttpStatus.NOT_FOUND)
                                .build()
                );
    }

    // =========================================================
    // OBTENER ACTIVIDADES POR OPERADOR
    // GET /api/actividades/operador/{operadorTuristicoId}
    // =========================================================
    @GetMapping("/operador/{operadorTuristicoId}")
    public ResponseEntity<List<Actividad>> obtenerPorOperador(
            @PathVariable Long operadorTuristicoId) {

        return ResponseEntity.ok(
                actividadService.obtenerPorOperador(operadorTuristicoId)
        );
    }

    // =========================================================
    // REVISAR SI YA EXISTE UNA ACTIVIDAD
    // GET /api/actividades/existe
    // =========================================================
    @GetMapping("/existe")
    public ResponseEntity<Actividad> existe(
            @RequestParam(required = false) Long operadorTuristicoId,
            @RequestParam(required = false) String nombre,
            @RequestParam(required = false) String urlOrigen) {

        Optional<Actividad> resultado;

        if (urlOrigen != null && !urlOrigen.isBlank()) {
            resultado = actividadService.existePorUrlOrigen(urlOrigen);

        } else if (
                operadorTuristicoId != null &&
                nombre != null &&
                !nombre.isBlank()
        ) {
            resultado = actividadService.existeParaOperador(
                    operadorTuristicoId,
                    nombre
            );

        } else {
            return ResponseEntity.badRequest().build();
        }

        return resultado
                .map(ResponseEntity::ok)
                .orElseGet(() ->
                        ResponseEntity
                                .status(HttpStatus.NOT_FOUND)
                                .build()
                );
    }

    // =========================================================
    // BUSCAR ACTIVIDADES POR TEXTO
    // GET /api/actividades/buscar?texto=...
    // =========================================================
    @GetMapping("/buscar")
    public ResponseEntity<List<Actividad>> buscarPorTexto(
            @RequestParam String texto) {

        return ResponseEntity.ok(
                actividadService.buscarPorTexto(texto)
        );
    }

    // =========================================================
    // CREAR ACTIVIDAD
    // POST /api/actividades
    // =========================================================
    @PostMapping
    public ResponseEntity<Actividad> crear(
            @RequestBody Actividad actividad) {

        Actividad creada = actividadService.guardar(actividad);

        return ResponseEntity
                .status(HttpStatus.CREATED)
                .body(creada);
    }

    // =========================================================
    // ACTUALIZAR ACTIVIDAD
    // PUT /api/actividades/{id}
    // =========================================================
    @PutMapping("/{id}")
    public ResponseEntity<Actividad> actualizar(
            @PathVariable Long id,
            @RequestBody Actividad actividad) {

        try {
            Actividad actualizada =
                    actividadService.actualizar(id, actividad);

            return ResponseEntity.ok(actualizada);

        } catch (RuntimeException e) {
            return ResponseEntity
                    .status(HttpStatus.NOT_FOUND)
                    .build();
        }
    }

    // =========================================================
    // DESACTIVAR ACTIVIDAD
    // PATCH /api/actividades/{id}/desactivar
    // =========================================================
    @PatchMapping("/{id}/desactivar")
    public ResponseEntity<Void> desactivar(@PathVariable Long id) {

        try {
            actividadService.desactivar(id);
            return ResponseEntity.noContent().build();

        } catch (RuntimeException e) {
            return ResponseEntity
                    .status(HttpStatus.NOT_FOUND)
                    .build();
        }
    }

    // =========================================================
    // ELIMINAR ACTIVIDAD DEFINITIVAMENTE
    // DELETE /api/actividades/{id}
    // =========================================================
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> eliminar(@PathVariable Long id) {

        try {
            actividadService.eliminar(id);
            return ResponseEntity.noContent().build();

        } catch (RuntimeException e) {
            return ResponseEntity
                    .status(HttpStatus.NOT_FOUND)
                    .build();
        }
    }
}
