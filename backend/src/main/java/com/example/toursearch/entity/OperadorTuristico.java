package com.example.toursearch.entity;

import java.time.OffsetDateTime;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.ForeignKey;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
    name = "operadores_turisticos",
    uniqueConstraints = {
        @UniqueConstraint(
            name = "operadores_pais_nombre_unique",
            columnNames = {"pais_id", "nombre"}
        )
    }
)
@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})
public class OperadorTuristico {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.EAGER, optional = false)
    @JoinColumn(
        name = "pais_id",
        nullable = false,
        foreignKey = @ForeignKey(
            name = "operadores_pais_fk"
        )
    )
    private Pais pais;

    @Column(
        name = "nombre",
        nullable = false,
        length = 200
    )
    private String nombre;

    @Column(
        name = "sitio_web",
        columnDefinition = "text"
    )
    private String sitioWeb;

    @Column(
        name = "correo",
        length = 200
    )
    private String correo;

    @Column(
        name = "telefono",
        length = 50
    )
    private String telefono;

    @Column(
        name = "estado",
        nullable = false,
        length = 20
    )
    private String estado = "ACTIVO";

    @Column(
        name = "creado_en",
        nullable = false
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

        if (estado == null || estado.isBlank()) {
            estado = "ACTIVO";
        }

        creadoEn = ahora;
        actualizadoEn = ahora;
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

    public Pais getPais() {
        return pais;
    }

    public void setPais(Pais pais) {
        this.pais = pais;
    }

    public String getNombre() {
        return nombre;
    }

    public void setNombre(String nombre) {
        this.nombre = nombre;
    }

    public String getSitioWeb() {
        return sitioWeb;
    }

    public void setSitioWeb(String sitioWeb) {
        this.sitioWeb = sitioWeb;
    }

    public String getCorreo() {
        return correo;
    }

    public void setCorreo(String correo) {
        this.correo = correo;
    }

    public String getTelefono() {
        return telefono;
    }

    public void setTelefono(String telefono) {
        this.telefono = telefono;
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

    public void setActualizadoEn(
        OffsetDateTime actualizadoEn
    ) {
        this.actualizadoEn = actualizadoEn;
    }
}