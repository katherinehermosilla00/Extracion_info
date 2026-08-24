package com.example.toursearch.entity;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;

@Entity
@Table(name = "registros_turisticos")
@Getter
@Setter
@NoArgsConstructor
public class RegistroTuristico {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /*
     * PostgreSQL genera automáticamente este código:
     * 0001, 0002, 0003...
     */
    @Column(
        name = "codigo_interno",
        nullable = false,
        unique = true,
        length = 4,
        insertable = false,
        updatable = false
    )
    private String codigoInterno;

    @Column(name = "pedido_id", length = 100)
    private String pedidoId;

    @Column(nullable = false, length = 300)
    private String nombre;

    @Column(nullable = false, length = 200)
    private String operador;

    @Column(
        name = "source_url",
        nullable = false,
        unique = true,
        columnDefinition = "text"
    )
    private String sourceUrl;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(
        name = "datos_extraidos",
        nullable = false,
        columnDefinition = "jsonb"
    )
    private JsonNode datosExtraidos;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private EstadoRegistro estado = EstadoRegistro.ACTIVO;

    @CreationTimestamp
    @Column(
        name = "creado_en",
        nullable = false,
        updatable = false
    )
    private OffsetDateTime creadoEn;

    @UpdateTimestamp
    @Column(
        name = "actualizado_en",
        nullable = false
    )
    private OffsetDateTime actualizadoEn;

    public enum EstadoRegistro {
        ACTIVO,
        INACTIVO,
        ELIMINADO
    }
}
