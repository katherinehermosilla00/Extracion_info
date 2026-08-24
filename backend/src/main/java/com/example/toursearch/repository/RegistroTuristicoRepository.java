package com.example.toursearch.repository;

import com.example.toursearch.entity.RegistroTuristico;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface RegistroTuristicoRepository
        extends JpaRepository<RegistroTuristico, Long> {

    Optional<RegistroTuristico> findByCodigoInterno(
        String codigoInterno
    );

    Optional<RegistroTuristico> findBySourceUrl(
        String sourceUrl
    );

    Optional<RegistroTuristico> findByPedidoId(
        String pedidoId
    );

    boolean existsBySourceUrl(
        String sourceUrl
    );

    List<RegistroTuristico> findByEstadoOrderByCreadoEnDesc(
        RegistroTuristico.EstadoRegistro estado
    );

    List<RegistroTuristico>
        findByOperadorContainingIgnoreCaseAndEstadoOrderByCreadoEnDesc(
            String operador,
            RegistroTuristico.EstadoRegistro estado
        );

    List<RegistroTuristico>
        findByNombreContainingIgnoreCaseAndEstadoOrderByCreadoEnDesc(
            String nombre,
            RegistroTuristico.EstadoRegistro estado
        );
}
