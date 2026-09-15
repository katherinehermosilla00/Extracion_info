package com.example.toursearch.entity;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

@Entity
@Table(name = "actividades")
public class Actividad {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String nombre;

    @Column(columnDefinition = "TEXT")
    private String descripcion;

    private String ubicacion;

    private String destino;

    // Ej: "4 horas", "Día completo"
    private String duracion;

    @Column(name = "edad_minima")
    private Integer edadMinima;

    @Column(name = "edad_maxima")
    private Integer edadMaxima;

    // ========================================================
    // IDIOMAS
    // ========================================================

    @ElementCollection
    @CollectionTable(
            name = "actividad_idiomas",
            joinColumns = @JoinColumn(name = "actividad_id")
    )
    @Column(name = "idioma")
    private List<String> idiomas = new ArrayList<>();

    // ========================================================
    // IMÁGENES
    // Se mantienen por compatibilidad.
    // No forman parte de la validación obligatoria actual.
    // ========================================================

    @ElementCollection
    @CollectionTable(
            name = "actividad_imagenes",
            joinColumns = @JoinColumn(name = "actividad_id")
    )
    @Column(
            name = "url_imagen",
            columnDefinition = "TEXT"
    )
    private List<String> imagenes = new ArrayList<>();

    // ========================================================
    // HIGHLIGHTS
    // ========================================================

    @ElementCollection
    @CollectionTable(
            name = "actividad_highlights",
            joinColumns = @JoinColumn(name = "actividad_id")
    )
    @Column(
            name = "highlight",
            columnDefinition = "TEXT"
    )
    private List<String> highlights = new ArrayList<>();

    // ========================================================
    // ITINERARIO
    // Por ahora se almacena como textos ordenados.
    // ========================================================

    @ElementCollection
    @CollectionTable(
            name = "actividad_itinerario",
            joinColumns = @JoinColumn(name = "actividad_id")
    )
    @Column(
            name = "paso",
            columnDefinition = "TEXT"
    )
    private List<String> itinerario = new ArrayList<>();

    // ========================================================
    // HORARIOS
    // ========================================================

    @ElementCollection
    @CollectionTable(
            name = "actividad_horarios",
            joinColumns = @JoinColumn(name = "actividad_id")
    )
    @Column(name = "horario")
    private List<String> horarios = new ArrayList<>();

    // ========================================================
    // RESTRICCIONES
    // ========================================================

    @ElementCollection
    @CollectionTable(
            name = "actividad_restricciones",
            joinColumns = @JoinColumn(name = "actividad_id")
    )
    @Column(
            name = "restriccion",
            columnDefinition = "TEXT"
    )
    private List<String> restricciones = new ArrayList<>();

    // ========================================================
    // URL DE ORIGEN
    // ========================================================

    @Column(
            name = "url_origen",
            columnDefinition = "TEXT"
    )
    private String urlOrigen;

    // ========================================================
    // OPERADOR
    // ========================================================

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "operador_turistico_id",
            nullable = false
    )
    private OperadorTuristico operadorTuristico;

    // ========================================================
    // ESTADO
    // ========================================================

    @Column(nullable = false)
    private boolean activo = true;

    // ========================================================
    // FECHAS
    // ========================================================

    @Column(
            name = "fecha_creacion",
            updatable = false
    )
    private LocalDateTime fechaCreacion;

    @Column(name = "fecha_modificacion")
    private LocalDateTime fechaModificacion;

    @PrePersist
    protected void onCreate() {
        this.fechaCreacion = LocalDateTime.now();
        this.fechaModificacion = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        this.fechaModificacion = LocalDateTime.now();
    }

    public Actividad() {
    }

    // ========================================================
    // GETTERS Y SETTERS
    // ========================================================

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

    public String getDescripcion() {
        return descripcion;
    }

    public void setDescripcion(String descripcion) {
        this.descripcion = descripcion;
    }

    public String getUbicacion() {
        return ubicacion;
    }

    public void setUbicacion(String ubicacion) {
        this.ubicacion = ubicacion;
    }

    public String getDestino() {
        return destino;
    }

    public void setDestino(String destino) {
        this.destino = destino;
    }

    public String getDuracion() {
        return duracion;
    }

    public void setDuracion(String duracion) {
        this.duracion = duracion;
    }

    public Integer getEdadMinima() {
        return edadMinima;
    }

    public void setEdadMinima(Integer edadMinima) {
        this.edadMinima = edadMinima;
    }

    public Integer getEdadMaxima() {
        return edadMaxima;
    }

    public void setEdadMaxima(Integer edadMaxima) {
        this.edadMaxima = edadMaxima;
    }

    public List<String> getIdiomas() {
        return idiomas;
    }

    public void setIdiomas(List<String> idiomas) {
        this.idiomas = idiomas;
    }

    public List<String> getImagenes() {
        return imagenes;
    }

    public void setImagenes(List<String> imagenes) {
        this.imagenes = imagenes;
    }

    public List<String> getHighlights() {
        return highlights;
    }

    public void setHighlights(List<String> highlights) {
        this.highlights = highlights;
    }

    public List<String> getItinerario() {
        return itinerario;
    }

    public void setItinerario(List<String> itinerario) {
        this.itinerario = itinerario;
    }

    public List<String> getHorarios() {
        return horarios;
    }

    public void setHorarios(List<String> horarios) {
        this.horarios = horarios;
    }

    public List<String> getRestricciones() {
        return restricciones;
    }

    public void setRestricciones(List<String> restricciones) {
        this.restricciones = restricciones;
    }

    public String getUrlOrigen() {
        return urlOrigen;
    }

    public void setUrlOrigen(String urlOrigen) {
        this.urlOrigen = urlOrigen;
    }

    public OperadorTuristico getOperadorTuristico() {
        return operadorTuristico;
    }

    public void setOperadorTuristico(
            OperadorTuristico operadorTuristico
    ) {
        this.operadorTuristico = operadorTuristico;
    }

    public boolean isActivo() {
        return activo;
    }

    public void setActivo(boolean activo) {
        this.activo = activo;
    }

    public LocalDateTime getFechaCreacion() {
        return fechaCreacion;
    }

    public LocalDateTime getFechaModificacion() {
        return fechaModificacion;
    }
}