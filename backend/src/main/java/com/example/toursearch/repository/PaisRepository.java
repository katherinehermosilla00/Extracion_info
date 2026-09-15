package com.example.toursearch.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.example.toursearch.entity.Pais;

public interface PaisRepository
        extends JpaRepository<Pais, Long> {

    List<Pais> findAllByOrderByNombreAsc();

    Optional<Pais> findByNombreIgnoreCase(
        String nombre
    );

    boolean existsByNombreIgnoreCase(
        String nombre
    );

    boolean existsByCodigoIsoIgnoreCase(
        String codigoIso
    );
}