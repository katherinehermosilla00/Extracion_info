package com.example.toursearch.entity;

import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

@Entity
@Table(name = "paises")
public class Pais {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(
        name = "nombre",
        nullable = false,
        unique = true,
        length = 100
    )
    private String nombre;

    @Column(
        name = "codigo_iso",
        unique = true,
        length = 3
    )
    private String codigoIso;

    @Column(
        name = "estado",
        nullable = false,
        length = 20
    )
    private String estado = "ACTIVO";

    @Column(
        name = "creado_en",
        nullable = false,
        updatable = false
    )
    private OffsetDateTime creadoEn;

    @Column(
        name = "actualizado_en",
        nullable = false
    )
    private OffsetDateTime actualizadoEn;

    @PrePersist
    public void antesDeCrear() {
        OffsetDateTime ahora = OffsetDateTime.now();

        creadoEn = ahora;
        actualizadoEn = ahora;

        if (estado == null || estado.isBlank()) {
            estado = "ACTIVO";
        }
    }

    @PreUpdate
    public void antesDeActualizar() {
        actualizadoEn = OffsetDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getNombre() {
        return nombre;
    }

    public void setNombre(String nombre) {
        this.nombre = nombre;
    }

    public String getCodigoIso() {
        return codigoIso;
    }

    public void setCodigoIso(String codigoIso) {
        this.codigoIso = codigoIso;
    }

    public String getEstado() {
        return estado;
    }

    public void setEstado(String estado) {
        this.estado = estado;
    }

    public OffsetDateTime getCreadoEn() {
        return creadoEn;
    }

    public void setCreadoEn(OffsetDateTime creadoEn) {
        this.creadoEn = creadoEn;
    }

    public OffsetDateTime getActualizadoEn() {
        return actualizadoEn;
    }

    public void setActualizadoEn(OffsetDateTime actualizadoEn) {
        this.actualizadoEn = actualizadoEn;
    }
}