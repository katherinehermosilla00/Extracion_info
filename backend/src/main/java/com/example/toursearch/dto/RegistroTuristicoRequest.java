package com.example.toursearch.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record RegistroTuristicoRequest(

    @Size(max = 100)
    String pedidoId,

    @NotBlank(message = "El nombre de la actividad es obligatorio")
    @Size(max = 300)
    String nombre,

    @NotBlank(message = "El operador es obligatorio")
    @Size(max = 200)
    String operador,

    @NotBlank(message = "La URL de origen es obligatoria")
    String sourceUrl,

    @NotNull(message = "Los datos extraídos son obligatorios")
    JsonNode datosExtraidos

) {
}
