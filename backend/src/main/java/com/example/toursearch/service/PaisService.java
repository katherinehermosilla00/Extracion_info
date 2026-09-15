package com.example.toursearch.service;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Service;

import com.example.toursearch.entity.Pais;
import com.example.toursearch.repository.PaisRepository;

@Service
public class PaisService {

    private final PaisRepository paisRepository;

    public PaisService(PaisRepository paisRepository) {
        this.paisRepository = paisRepository;
    }

    public List<Pais> listar() {
        return paisRepository.findAllByOrderByNombreAsc();
    }

    public Optional<Pais> buscarPorId(Long id) {
        return paisRepository.findById(id);
    }

    public Optional<Pais> buscarPorNombre(String nombre) {
        return paisRepository.findByNombreIgnoreCase(nombre);
    }

    public Pais obtenerPorId(Long id) {
        return paisRepository.findById(id)
            .orElseThrow(() ->
                new IllegalArgumentException(
                    "No existe el país con ID " + id
                )
            );
    }

    public Pais crear(Pais pais) {
        validarNombre(pais.getNombre());

        String nombre = pais.getNombre().trim();
        String codigoIso = normalizarCodigoIso(
            pais.getCodigoIso()
        );

        if (paisRepository.existsByNombreIgnoreCase(nombre)) {
            throw new IllegalArgumentException(
                "Ya existe un país con ese nombre"
            );
        }

        if (codigoIso != null
                && paisRepository.existsByCodigoIsoIgnoreCase(codigoIso)) {
            throw new IllegalArgumentException(
                "Ya existe un país con ese código ISO"
            );
        }

        pais.setId(null);
        pais.setNombre(nombre);
        pais.setCodigoIso(codigoIso);

        if (pais.getEstado() == null
                || pais.getEstado().isBlank()) {
            pais.setEstado("ACTIVO");
        } else {
            pais.setEstado(
                validarEstado(pais.getEstado())
            );
        }

        return paisRepository.save(pais);
    }

    public Pais actualizar(
            Long id,
            Pais datos
    ) {
        Pais pais = obtenerPorId(id);

        validarNombre(datos.getNombre());

        String nombre = datos.getNombre().trim();
        String codigoIso = normalizarCodigoIso(
            datos.getCodigoIso()
        );

        boolean nombreCambio =
            pais.getNombre() == null
                || !pais.getNombre().equalsIgnoreCase(nombre);

        if (nombreCambio
                && paisRepository.existsByNombreIgnoreCase(nombre)) {
            throw new IllegalArgumentException(
                "Ya existe otro país con ese nombre"
            );
        }

        String codigoActual = normalizarCodigoIso(
            pais.getCodigoIso()
        );

        boolean codigoCambio =
            codigoActual == null
                ? codigoIso != null
                : !codigoActual.equalsIgnoreCase(
                    codigoIso == null ? "" : codigoIso
                );

        if (codigoCambio
                && codigoIso != null
                && paisRepository.existsByCodigoIsoIgnoreCase(codigoIso)) {
            throw new IllegalArgumentException(
                "Ya existe otro país con ese código ISO"
            );
        }

        pais.setNombre(nombre);
        pais.setCodigoIso(codigoIso);

        if (datos.getEstado() != null
                && !datos.getEstado().isBlank()) {
            pais.setEstado(
                validarEstado(datos.getEstado())
            );
        }

        return paisRepository.save(pais);
    }

    public Pais cambiarEstado(
            Long id,
            String estado
    ) {
        Pais pais = obtenerPorId(id);

        pais.setEstado(
            validarEstado(estado)
        );

        return paisRepository.save(pais);
    }

    private void validarNombre(String nombre) {
        if (nombre == null || nombre.isBlank()) {
            throw new IllegalArgumentException(
                "El nombre del país es obligatorio"
            );
        }
    }

    private String normalizarCodigoIso(String codigoIso) {
        if (codigoIso == null || codigoIso.isBlank()) {
            return null;
        }

        String codigo = codigoIso.trim().toUpperCase();

        if (codigo.length() > 3) {
            throw new IllegalArgumentException(
                "El código ISO no puede tener más de 3 caracteres"
            );
        }

        return codigo;
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
