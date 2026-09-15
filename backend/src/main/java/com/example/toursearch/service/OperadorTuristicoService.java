package com.example.toursearch.service;

import java.util.List;

import org.springframework.stereotype.Service;

import com.example.toursearch.entity.OperadorTuristico;
import com.example.toursearch.entity.Pais;
import com.example.toursearch.repository.OperadorTuristicoRepository;
import com.example.toursearch.repository.PaisRepository;

@Service
public class OperadorTuristicoService {

    private final OperadorTuristicoRepository operadorRepository;
    private final PaisRepository paisRepository;

    public OperadorTuristicoService(
            OperadorTuristicoRepository operadorRepository,
            PaisRepository paisRepository
    ) {
        this.operadorRepository = operadorRepository;
        this.paisRepository = paisRepository;
    }

    public List<OperadorTuristico> listarTodos() {
        return operadorRepository.findAllByOrderByNombreAsc();
    }

    public List<OperadorTuristico> listarPorPais(Long paisId) {
        verificarPais(paisId);

        return operadorRepository
                .findByPaisIdOrderByNombreAsc(paisId);
    }

    public OperadorTuristico obtenerPorId(Long id) {
        return operadorRepository.findById(id)
                .orElseThrow(() ->
                        new IllegalArgumentException(
                                "No existe el operador turístico con ID " + id
                        )
                );
    }

    public OperadorTuristico crear(
            Long paisId,
            OperadorTuristico operador
    ) {
        Pais pais = verificarPais(paisId);

        validarNombre(operador.getNombre());

        String nombre = operador.getNombre().trim();

        boolean yaExiste = operadorRepository
                .existsByPaisIdAndNombreIgnoreCase(
                        paisId,
                        nombre
                );

        if (yaExiste) {
            throw new IllegalArgumentException(
                    "Ya existe un operador con ese nombre en el país seleccionado"
            );
        }

        operador.setId(null);
        operador.setNombre(nombre);
        operador.setPais(pais);

        if (operador.getEstado() == null
                || operador.getEstado().isBlank()) {
            operador.setEstado("ACTIVO");
        } else {
            operador.setEstado(
                    validarEstado(operador.getEstado())
            );
        }

        return operadorRepository.save(operador);
    }

    public OperadorTuristico actualizar(
            Long id,
            Long paisId,
            OperadorTuristico datos
    ) {
        OperadorTuristico operador = obtenerPorId(id);
        Pais pais = verificarPais(paisId);

        validarNombre(datos.getNombre());

        String nombre = datos.getNombre().trim();

        operadorRepository
                .findByPaisIdAndNombreIgnoreCase(
                        paisId,
                        nombre
                )
                .filter(encontrado ->
                        !encontrado.getId().equals(id)
                )
                .ifPresent(encontrado -> {
                    throw new IllegalArgumentException(
                            "Ya existe otro operador con ese nombre en el país seleccionado"
                    );
                });

        operador.setPais(pais);
        operador.setNombre(nombre);
        operador.setSitioWeb(datos.getSitioWeb());
        operador.setCorreo(datos.getCorreo());
        operador.setTelefono(datos.getTelefono());

        if (datos.getEstado() != null
                && !datos.getEstado().isBlank()) {
            operador.setEstado(
                    validarEstado(datos.getEstado())
            );
        }

        return operadorRepository.save(operador);
    }

    public OperadorTuristico cambiarEstado(
            Long id,
            String estado
    ) {
        OperadorTuristico operador = obtenerPorId(id);

        operador.setEstado(
                validarEstado(estado)
        );

        return operadorRepository.save(operador);
    }

    private Pais verificarPais(Long paisId) {
        if (paisId == null) {
            throw new IllegalArgumentException(
                    "El ID del país es obligatorio"
            );
        }

        return paisRepository.findById(paisId)
                .orElseThrow(() ->
                        new IllegalArgumentException(
                                "No existe el país con ID " + paisId
                        )
                );
    }

    private void validarNombre(String nombre) {
        if (nombre == null || nombre.isBlank()) {
            throw new IllegalArgumentException(
                    "El nombre del operador es obligatorio"
            );
        }
    }

    private String validarEstado(String estado) {
        if (estado == null
                || (!estado.equalsIgnoreCase("ACTIVO")
                && !estado.equalsIgnoreCase("INACTIVO"))) {
            throw new IllegalArgumentException(
                    "El estado debe ser ACTIVO o INACTIVO"
            );
        }

        return estado.trim().toUpperCase();
    }
}