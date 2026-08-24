package com.example.toursearch.repository;

import com.example.toursearch.entity.TourAvailability;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TourAvailabilityRepository extends JpaRepository<TourAvailability, Long> {
}
