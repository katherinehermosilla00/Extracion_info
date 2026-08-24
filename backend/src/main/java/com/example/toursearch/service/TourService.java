package com.example.toursearch.service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.example.toursearch.dto.AvailabilityRequest;
import com.example.toursearch.dto.TourRequest;
import com.example.toursearch.entity.Tour;
import com.example.toursearch.entity.TourAvailability;
import com.example.toursearch.repository.TourAvailabilityRepository;
import com.example.toursearch.repository.TourRepository;

import jakarta.persistence.criteria.Predicate;

@Service
public class TourService {

    private final TourRepository tourRepository;
    private final TourAvailabilityRepository availabilityRepository;

    public TourService(
            TourRepository tourRepository,
            TourAvailabilityRepository availabilityRepository
    ) {
        this.tourRepository = tourRepository;
        this.availabilityRepository = availabilityRepository;
    }

    public List<Tour> findAll() {
        return tourRepository.findAll();
    }

    public Tour findById(Long id) {
        return tourRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Tour no encontrado"));
    }

    public List<Tour> search(
            String query,
            String location,
            String category,
            Integer age,
            BigDecimal minPrice,
            BigDecimal maxPrice,
            LocalDate dateFrom,
            LocalDate dateTo
    ) {

        Specification<Tour> spec = Specification.unrestricted();

        // Buscar por nombre o descripción
        if (query != null && !query.isBlank()) {
            String value = "%" + query.toLowerCase() + "%";

            spec = spec.and((root, criteriaQuery, cb) ->
                    cb.or(
                            cb.like(cb.lower(root.get("name")), value),
                            cb.like(cb.lower(root.get("description")), value)
                    )
            );
        }

        // Filtrar por ubicación
        if (location != null && !location.isBlank()) {
            spec = spec.and((root, criteriaQuery, cb) ->
                    cb.equal(
                            cb.lower(root.get("location")),
                            location.toLowerCase()
                    )
            );
        }

        // Filtrar por categoría
        if (category != null && !category.isBlank()) {
            spec = spec.and((root, criteriaQuery, cb) ->
                    cb.equal(
                            cb.lower(root.get("category")),
                            category.toLowerCase()
                    )
            );
        }

        // Filtrar por edad
        if (age != null) {
            spec = spec.and((root, criteriaQuery, cb) ->
                    cb.and(
                            cb.lessThanOrEqualTo(root.get("minAge"), age),
                            cb.greaterThanOrEqualTo(root.get("maxAge"), age)
                    )
            );
        }

        // Precio mínimo
        if (minPrice != null) {
            spec = spec.and((root, criteriaQuery, cb) ->
                    cb.greaterThanOrEqualTo(
                            root.get("price"),
                            minPrice
                    )
            );
        }

        // Precio máximo
        if (maxPrice != null) {
            spec = spec.and((root, criteriaQuery, cb) ->
                    cb.lessThanOrEqualTo(
                            root.get("price"),
                            maxPrice
                    )
            );
        }

        // Filtro por disponibilidad / calendario
        if (dateFrom != null || dateTo != null) {

            spec = spec.and((root, criteriaQuery, cb) -> {

                var availability = root.join("availability");

                criteriaQuery.distinct(true);

                List<Predicate> predicates = new ArrayList<>();

                // Solo fechas disponibles
                predicates.add(
                        cb.isTrue(
                                availability.get("available")
                        )
                );

                if (dateFrom != null) {
                    predicates.add(
                            cb.greaterThanOrEqualTo(
                                    availability.get("date"),
                                    dateFrom
                            )
                    );
                }

                if (dateTo != null) {
                    predicates.add(
                            cb.lessThanOrEqualTo(
                                    availability.get("date"),
                                    dateTo
                            )
                    );
                }

                return cb.and(
                       predicates.toArray(Predicate[]::new)
                );
            });
        }

        return tourRepository.findAll(spec);
    }

    @Transactional
    public Tour create(TourRequest request) {

        validateAgeRange(
                request.minAge(),
                request.maxAge()
        );

        Tour tour = Tour.builder()
                .name(request.name())
                .description(request.description())
                .price(request.price())
                .currency(request.currency())
                .duration(request.duration())
                .minAge(request.minAge())
                .maxAge(request.maxAge())
                .location(request.location())
                .category(request.category())
                .sourceUrl(request.sourceUrl())
                .build();

        return tourRepository.save(tour);
    }

    @Transactional
    public Tour update(
            Long id,
            TourRequest request
    ) {

        validateAgeRange(
                request.minAge(),
                request.maxAge()
        );

        Tour tour = findById(id);

        tour.setName(request.name());
        tour.setDescription(request.description());
        tour.setPrice(request.price());
        tour.setCurrency(request.currency());
        tour.setDuration(request.duration());
        tour.setMinAge(request.minAge());
        tour.setMaxAge(request.maxAge());
        tour.setLocation(request.location());
        tour.setCategory(request.category());
        tour.setSourceUrl(request.sourceUrl());

        return tourRepository.save(tour);
    }

    @Transactional
    public void delete(Long id) {
        tourRepository.delete(
                findById(id)
        );
    }

    @Transactional
    public TourAvailability addAvailability(
            Long tourId,
            AvailabilityRequest request
    ) {

        Tour tour = findById(tourId);

        TourAvailability availability =
                TourAvailability.builder()
                        .tour(tour)
                        .date(request.date())
                        .available(request.available())
                        .availableSlots(
                                request.availableSlots()
                        )
                        .startTime(request.startTime())
                        .endTime(request.endTime())
                        .build();

        return availabilityRepository.save(
                availability
        );
    }

    private void validateAgeRange(
            Integer minAge,
            Integer maxAge
    ) {

        if (
                minAge != null &&
                maxAge != null &&
                minAge > maxAge
        ) {
            throw new IllegalArgumentException(
                    "La edad mínima no puede ser mayor que la máxima"
            );
        }
    }
}