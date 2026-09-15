package com.example.toursearch.service;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.example.toursearch.entity.Usuario;
import com.example.toursearch.repository.UsuarioRepository;

@Service
public class AdminUsuarioService {

    private final UsuarioRepository usuarioRepository;

    public AdminUsuarioService(
            UsuarioRepository usuarioRepository
    ) {
        this.usuarioRepository = usuarioRepository;
    }

    public List<Usuario> listarUsuarios() {
        return usuarioRepository
                .findAll()
                .stream()
                .sorted(
                        Comparator.comparing(
                                Usuario::getNombre,
                                String.CASE_INSENSITIVE_ORDER
                        )
                )
                .toList();
    }

    @Transactional
    public Usuario cambiarRol(
            Long id,
            String nuevoRol,
            String correoAdministradorActual
    ) {
        Usuario usuario = obtenerUsuario(id);

        String rolNormalizado =
                normalizarRol(nuevoRol);

        if (esMismoUsuario(
                usuario,
                correoAdministradorActual
        ) && !"ADMIN".equals(rolNormalizado)) {

            throw new IllegalArgumentException(
                    "No puedes quitarte tu propio rol de administrador"
            );
        }

        usuario.setRol(rolNormalizado);

        return usuarioRepository.save(usuario);
    }

    @Transactional
    public Usuario cambiarEstado(
            Long id,
            boolean activo,
            String correoAdministradorActual
    ) {
        Usuario usuario = obtenerUsuario(id);

        if (esMismoUsuario(
                usuario,
                correoAdministradorActual
        ) && !activo) {

            throw new IllegalArgumentException(
                    "No puedes desactivar tu propia cuenta"
            );
        }

        usuario.setActivo(activo);

        return usuarioRepository.save(usuario);
    }

    private Usuario obtenerUsuario(
            Long id
    ) {
        if (id == null) {
            throw new IllegalArgumentException(
                    "El ID del usuario es obligatorio"
            );
        }

        return usuarioRepository
                .findById(id)
                .orElseThrow(
                        () ->
                                new IllegalArgumentException(
                                        "Usuario no encontrado"
                                )
                );
    }

    private String normalizarRol(
            String rol
    ) {
        if (rol == null || rol.isBlank()) {
            throw new IllegalArgumentException(
                    "El rol es obligatorio"
            );
        }

        String rolNormalizado =
                rol.trim()
                        .toUpperCase(
                                Locale.ROOT
                        );

        if (!rolNormalizado.equals("USER")
                && !rolNormalizado.equals("ADMIN")) {

            throw new IllegalArgumentException(
                    "El rol debe ser USER o ADMIN"
            );
        }

        return rolNormalizado;
    }

    private boolean esMismoUsuario(
            Usuario usuario,
            String correoActual
    ) {
        if (usuario == null
                || usuario.getCorreo() == null
                || correoActual == null) {

            return false;
        }

        return usuario
                .getCorreo()
                .equalsIgnoreCase(
                        correoActual.trim()
                );
    }
}
