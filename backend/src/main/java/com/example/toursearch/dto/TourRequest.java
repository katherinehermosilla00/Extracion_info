package com.example.toursearch.dto;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;

public record TourRequest(
        @NotBlank String name,
        String description,
        @PositiveOrZero BigDecimal price,
        String currency,
        String duration,
        @Min(0) Integer minAge,
        @Min(0) Integer maxAge,
        String location,
        String category,
        String sourceUrl
) {}
