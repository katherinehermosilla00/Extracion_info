package com.example.toursearch.controller;

import com.example.toursearch.dto.*;
import com.example.toursearch.entity.*;
import com.example.toursearch.service.TourService;
import jakarta.validation.Valid;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/tours")
@CrossOrigin(origins = "http://localhost:5173")
public class TourController {

    private final TourService tourService;

    public TourController(TourService tourService) {
        this.tourService = tourService;
    }

    @GetMapping
    public List<Tour> getAll() {
        return tourService.findAll();
    }

    @GetMapping("/{id}")
    public Tour getById(@PathVariable Long id) {
        return tourService.findById(id);
    }

    @GetMapping("/search")
    public List<Tour> search(
            @RequestParam(required = false) String query,
            @RequestParam(required = false) String location,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) Integer age,
            @RequestParam(required = false) BigDecimal minPrice,
            @RequestParam(required = false) BigDecimal maxPrice,
            @RequestParam(required = false) LocalDate dateFrom,
            @RequestParam(required = false) LocalDate dateTo) {

        return tourService.search(
                query, location, category, age,
                minPrice, maxPrice, dateFrom, dateTo
        );
    }

    @PostMapping
    public ResponseEntity<Tour> create(@Valid @RequestBody TourRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(tourService.create(request));
    }

    @PutMapping("/{id}")
    public Tour update(@PathVariable Long id, @Valid @RequestBody TourRequest request) {
        return tourService.update(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        tourService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/availability")
    public ResponseEntity<TourAvailability> addAvailability(
            @PathVariable Long id,
            @Valid @RequestBody AvailabilityRequest request) {

        return ResponseEntity.status(HttpStatus.CREATED)
                .body(tourService.addAvailability(id, request));
    }
}
