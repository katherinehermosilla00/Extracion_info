package com.example.toursearch.service;

import com.example.toursearch.dto.RegistroTuristicoRequest;
import com.example.toursearch.entity.RegistroTuristico;
import com.example.toursearch.repository.RegistroTuristicoRepository;
import jakarta.persistence.EntityManager;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
public class RegistroTuristicoService {

    private final RegistroTuristicoRepository repository;
    private final EntityManager entityManager;

    /*
     * Si la URL ya estaba registrada, actualiza ese registro.
     * Si no existe, crea uno nuevo con código 0001, 0002, etc.
     */
    @Transactional
    public RegistroTuristico guardar(
        RegistroTuristicoRequest request
    ) {
        RegistroTuristico registro = repository
            .findBySourceUrl(request.sourceUrl())
            .orElseGet(RegistroTuristico::new);

        copiarDatos(registro, request);
        registro.setEstado(
            RegistroTuristico.EstadoRegistro.ACTIVO
        );

        RegistroTuristico guardado =
            repository.saveAndFlush(registro);

        entityManager.refresh(guardado);

        return guardado;
    }

    public List<RegistroTuristico> listarActivos() {
        return repository.findByEstadoOrderByCreadoEnDesc(
            RegistroTuristico.EstadoRegistro.ACTIVO
        );
    }

    public RegistroTuristico buscarPorCodigo(
        String codigo
    ) {
        return repository.findByCodigoInterno(
            normalizarCodigo(codigo)
        ).orElseThrow(() -> new ResponseStatusException(
            HttpStatus.NOT_FOUND,
            "No existe un registro con el código " + codigo
        ));
    }

    public RegistroTuristico buscarPorUrl(
        String sourceUrl
    ) {
        return repository.findBySourceUrl(sourceUrl)
            .orElseThrow(() -> new ResponseStatusException(
                HttpStatus.NOT_FOUND,
                "La URL todavía no está registrada"
            ));
    }

    public List<RegistroTuristico> buscar(
        String tipo,
        String termino
    ) {
        if (termino == null || termino.isBlank()) {
            return listarActivos();
        }

        String tipoNormalizado = tipo == null
            ? "actividad"
            : tipo.trim().toLowerCase();

        if (
            tipoNormalizado.equals("operador")
            || tipoNormalizado.equals("to")
        ) {
            return repository
                .findByOperadorContainingIgnoreCaseAndEstadoOrderByCreadoEnDesc(
                    termino.trim(),
                    RegistroTuristico.EstadoRegistro.ACTIVO
                );
        }

        return repository
            .findByNombreContainingIgnoreCaseAndEstadoOrderByCreadoEnDesc(
                termino.trim(),
                RegistroTuristico.EstadoRegistro.ACTIVO
            );
    }

    @Transactional
    public RegistroTuristico actualizar(
        String codigo,
        RegistroTuristicoRequest request
    ) {
        RegistroTuristico registro = buscarPorCodigo(codigo);

        repository.findBySourceUrl(request.sourceUrl())
            .filter(encontrado ->
                !encontrado.getId().equals(registro.getId())
            )
            .ifPresent(encontrado -> {
                throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "La URL pertenece a otro registro"
                );
            });

        copiarDatos(registro, request);

        return repository.save(registro);
    }

    @Transactional
    public RegistroTuristico cambiarEstado(
        String codigo,
        RegistroTuristico.EstadoRegistro estado
    ) {
        RegistroTuristico registro = buscarPorCodigo(codigo);
        registro.setEstado(estado);

        return repository.save(registro);
    }

    @Transactional
    public void eliminar(
        String codigo
    ) {
        RegistroTuristico registro = buscarPorCodigo(codigo);

        /*
         * Eliminación lógica:
         * permanece en la base de datos y puede recuperarse.
         */
        registro.setEstado(
            RegistroTuristico.EstadoRegistro.ELIMINADO
        );

        repository.save(registro);
    }

    private void copiarDatos(
        RegistroTuristico registro,
        RegistroTuristicoRequest request
    ) {
        registro.setPedidoId(limpiar(request.pedidoId()));
        registro.setNombre(request.nombre().trim());
        registro.setOperador(request.operador().trim());
        registro.setSourceUrl(request.sourceUrl().trim());
        registro.setDatosExtraidos(request.datosExtraidos());
    }

    private String limpiar(
        String valor
    ) {
        if (valor == null || valor.isBlank()) {
            return null;
        }

        return valor.trim();
    }

    private String normalizarCodigo(
        String codigo
    ) {
        if (codigo == null || codigo.isBlank()) {
            throw new ResponseStatusException(
                HttpStatus.BAD_REQUEST,
                "El código es obligatorio"
            );
        }

        String limpio = codigo.trim();

        if (!limpio.matches("\\d{1,4}")) {
            throw new ResponseStatusException(
                HttpStatus.BAD_REQUEST,
                "El código debe contener entre uno y cuatro números"
            );
        }

        return String.format(
            "%04d",
            Integer.parseInt(limpio)
        );
    }
}
