package com.example.toursearch.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.example.toursearch.entity.OperadorTuristico;
import com.example.toursearch.service.OperadorTuristicoService;

@RestController
@RequestMapping("/api/operadores")
@CrossOrigin(origins = "*")
public class OperadorTuristicoController {

    private final OperadorTuristicoService operadorService;

    public OperadorTuristicoController(
            OperadorTuristicoService operadorService
    ) {
        this.operadorService = operadorService;
    }

    @GetMapping
    public List<OperadorTuristico> listarTodos() {
        return operadorService.listarTodos();
    }

    @GetMapping("/pais/{paisId}")
    public List<OperadorTuristico> listarPorPais(
            @PathVariable Long paisId
    ) {
        return operadorService.listarPorPais(paisId);
    }

    @GetMapping("/{id}")
    public OperadorTuristico obtenerPorId(
            @PathVariable Long id
    ) {
        return operadorService.obtenerPorId(id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public OperadorTuristico crear(
            @RequestParam Long paisId,
            @RequestBody OperadorTuristico operador
    ) {
        return operadorService.crear(
                paisId,
                operador
        );
    }

    @PutMapping("/{id}")
    public OperadorTuristico actualizar(
            @PathVariable Long id,
            @RequestParam Long paisId,
            @RequestBody OperadorTuristico operador
    ) {
        return operadorService.actualizar(
                id,
                paisId,
                operador
        );
    }

    @PatchMapping("/{id}/estado")
    public OperadorTuristico cambiarEstado(
            @PathVariable Long id,
            @RequestParam String estado
    ) {
        return operadorService.cambiarEstado(
                id,
                estado
        );
    }
}