package com.example.toursearch.dto;

import jakarta.validation.constraints.*;
import java.time.LocalDate;
import java.time.LocalTime;

public record AvailabilityRequest(
        @NotNull LocalDate date,
        @NotNull Boolean available,
        @Min(0) Integer availableSlots,
        LocalTime startTime,
        LocalTime endTime
) {}
