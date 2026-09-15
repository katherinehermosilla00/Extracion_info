package com.example.toursearch.controller;
import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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

import com.example.toursearch.entity.Pais;
import com.example.toursearch.service.PaisService;

@RestController
@RequestMapping("/api/paises")
@CrossOrigin(origins = "*")
public class PaisController {

    private final PaisService paisService;

    public PaisController(PaisService paisService) {
        this.paisService = paisService;
    }

    @GetMapping
    public List<Pais> listar() {
        return paisService.listar();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Pais> buscarPorId(
            @PathVariable Long id
    ) {
        return paisService.buscarPorId(id)
            .map(ResponseEntity::ok)
            .orElseGet(() ->
                ResponseEntity.notFound().build()
            );
    }

    @GetMapping("/buscar")
    public ResponseEntity<Pais> buscarPorNombre(
            @RequestParam String nombre
    ) {
        return paisService.buscarPorNombre(nombre)
            .map(ResponseEntity::ok)
            .orElseGet(() ->
                ResponseEntity.notFound().build()
            );
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Pais crear(
            @RequestBody Pais pais
    ) {
        return paisService.crear(pais);
    }

    @PutMapping("/{id}")
    public Pais actualizar(
            @PathVariable Long id,
            @RequestBody Pais pais
    ) {
        return paisService.actualizar(
            id,
            pais
        );
    }

    @PatchMapping("/{id}/estado")
    public Pais cambiarEstado(
            @PathVariable Long id,
            @RequestParam String estado
    ) {
        return paisService.cambiarEstado(
            id,
            estado
        );
    }
}
