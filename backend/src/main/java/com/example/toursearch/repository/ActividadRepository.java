package com.example.toursearch.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.example.toursearch.entity.Actividad;

public interface ActividadRepository extends JpaRepository<Actividad, Long> {

    // Todas las actividades activas de un operador
    List<Actividad> findByOperadorTuristicoIdAndActivoTrue(Long operadorTuristicoId);

    // Búsqueda por nombre dentro de un operador (para evitar re-scrapear si ya existe)
    Optional<Actividad> findByOperadorTuristicoIdAndNombreIgnoreCaseAndActivoTrue(
            Long operadorTuristicoId, String nombre);

    // Búsqueda por URL de origen (coincidencia exacta con lo que devuelve el scraper)
    Optional<Actividad> findByUrlOrigenAndActivoTrue(String urlOrigen);

    // Búsqueda flexible por nombre parecido, útil para el flujo "Buscar → Revisar → Extraer"
    @Query("SELECT a FROM Actividad a WHERE a.activo = true " +
           "AND LOWER(a.nombre) LIKE LOWER(CONCAT('%', :texto, '%'))")
    List<Actividad> buscarPorTextoEnNombre(@Param("texto") String texto);
}