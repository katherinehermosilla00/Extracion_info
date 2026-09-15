package com.example.toursearch.controller;

import java.util.HashMap;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.example.toursearch.security.UrlValidationService;

@RestController
@RequestMapping("/api/security")
@CrossOrigin(origins = "*")
public class SecurityController {

    private final UrlValidationService urlValidationService;

    public SecurityController(
            UrlValidationService urlValidationService
    ) {
        this.urlValidationService = urlValidationService;
    }

    @GetMapping("/validate")
    public ResponseEntity<Map<String, Object>> validateUrl(
            @RequestParam String url
    ) {

        Map<String, Object> response = new HashMap<>();

        try {

            urlValidationService.validate(url);

            response.put("valid", true);
            response.put("url", url);
            response.put("message", "URL permitida");

            return ResponseEntity.ok(response);

        } catch (IllegalArgumentException e) {

            response.put("valid", false);
            response.put("url", url);
            response.put("message", e.getMessage());

            return ResponseEntity.badRequest().body(response);
        }
    }
}