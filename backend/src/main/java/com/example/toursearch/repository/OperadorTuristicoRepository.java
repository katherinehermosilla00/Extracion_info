package com.example.toursearch.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.example.toursearch.entity.OperadorTuristico;

public interface OperadorTuristicoRepository
        extends JpaRepository<OperadorTuristico, Long> {

    List<OperadorTuristico> findAllByOrderByNombreAsc();

    List<OperadorTuristico> findByPaisIdOrderByNombreAsc(
            Long paisId
    );

    Optional<OperadorTuristico> findByPaisIdAndNombreIgnoreCase(
            Long paisId,
            String nombre
    );

    boolean existsByPaisIdAndNombreIgnoreCase(
            Long paisId,
            String nombre
    );
}