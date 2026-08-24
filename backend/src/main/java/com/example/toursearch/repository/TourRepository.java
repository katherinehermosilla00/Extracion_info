package com.example.toursearch.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

import com.example.toursearch.entity.Tour;

public interface TourRepository
        extends JpaRepository<Tour, Long>, JpaSpecificationExecutor<Tour> {
}