package com.example.toursearch.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.example.toursearch.entity.Usuario;

public interface UsuarioRepository
        extends JpaRepository<Usuario, Long> {

    Optional<Usuario> findByCorreoIgnoreCase(
            String correo
    );

    boolean existsByCorreoIgnoreCase(
            String correo
    );

    Optional<Usuario> findByPasswordResetToken(
            String passwordResetToken
    );
}