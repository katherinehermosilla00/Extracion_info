package com.example.toursearch.controller;

import com.example.toursearch.dto.RegistroTuristicoRequest;
import com.example.toursearch.entity.RegistroTuristico;
import com.example.toursearch.service.RegistroTuristicoService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/registros")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class RegistroTuristicoController {

    private final RegistroTuristicoService service;

    @PostMapping
    public ResponseEntity<RegistroTuristico> guardar(
        @Valid @RequestBody RegistroTuristicoRequest request
    ) {
        RegistroTuristico registro = service.guardar(request);

        return ResponseEntity
            .created(
                URI.create(
                    "/api/registros/"
                    + registro.getCodigoInterno()
                )
            )
            .body(registro);
    }

    @GetMapping
    public List<RegistroTuristico> listarActivos() {
        return service.listarActivos();
    }

    @GetMapping("/{codigo}")
    public RegistroTuristico buscarPorCodigo(
        @PathVariable String codigo
    ) {
        return service.buscarPorCodigo(codigo);
    }

    @GetMapping("/por-url")
    public RegistroTuristico buscarPorUrl(
        @RequestParam String sourceUrl
    ) {
        return service.buscarPorUrl(sourceUrl);
    }

    @GetMapping("/buscar")
    public List<RegistroTuristico> buscar(
        @RequestParam(defaultValue = "actividad") String tipo,
        @RequestParam(defaultValue = "") String termino
    ) {
        return service.buscar(tipo, termino);
    }

    @PutMapping("/{codigo}")
    public RegistroTuristico actualizar(
        @PathVariable String codigo,
        @Valid @RequestBody RegistroTuristicoRequest request
    ) {
        return service.actualizar(codigo, request);
    }

    @PatchMapping("/{codigo}/estado")
    public RegistroTuristico cambiarEstado(
        @PathVariable String codigo,
        @RequestParam RegistroTuristico.EstadoRegistro estado
    ) {
        return service.cambiarEstado(codigo, estado);
    }

    @DeleteMapping("/{codigo}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void eliminar(
        @PathVariable String codigo
    ) {
        service.eliminar(codigo);
    }
}
