package com.example.toursearch.controller;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.example.toursearch.entity.Usuario;
import com.example.toursearch.service.AdminUsuarioService;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final AdminUsuarioService adminUsuarioService;

    public AdminController(
            AdminUsuarioService adminUsuarioService
    ) {
        this.adminUsuarioService = adminUsuarioService;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status(
            Authentication authentication
    ) {

        Map<String, Object> response =
                new LinkedHashMap<>();

        List<String> roles =
                authentication
                        .getAuthorities()
                        .stream()
                        .map(authority ->
                                authority.getAuthority()
                        )
                        .toList();

        response.put("ok", true);
        response.put("admin", true);
        response.put(
                "correo",
                authentication.getName()
        );
        response.put(
                "roles",
                roles
        );
        response.put(
                "mensaje",
                "Acceso administrativo autorizado"
        );

        return ResponseEntity.ok(response);
    }

    @GetMapping("/usuarios")
    public ResponseEntity<List<UsuarioAdminResponse>> listarUsuarios() {

        List<UsuarioAdminResponse> usuarios =
                adminUsuarioService
                        .listarUsuarios()
                        .stream()
                        .map(this::toResponse)
                        .toList();

        return ResponseEntity.ok(usuarios);
    }

    @PatchMapping("/usuarios/{id}/rol")
    public ResponseEntity<?> cambiarRol(
            @PathVariable Long id,
            @RequestParam String rol,
            Authentication authentication
    ) {
        try {

            Usuario usuario =
                    adminUsuarioService
                            .cambiarRol(
                                    id,
                                    rol,
                                    authentication.getName()
                            );

            return ResponseEntity.ok(
                    toResponse(usuario)
            );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .badRequest()
                    .body(
                            error(e.getMessage())
                    );
        }
    }

    @PatchMapping("/usuarios/{id}/estado")
    public ResponseEntity<?> cambiarEstado(
            @PathVariable Long id,
            @RequestParam boolean activo,
            Authentication authentication
    ) {
        try {

            Usuario usuario =
                    adminUsuarioService
                            .cambiarEstado(
                                    id,
                                    activo,
                                    authentication.getName()
                            );

            return ResponseEntity.ok(
                    toResponse(usuario)
            );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .badRequest()
                    .body(
                            error(e.getMessage())
                    );
        }
    }

    private UsuarioAdminResponse toResponse(
            Usuario usuario
    ) {
        return new UsuarioAdminResponse(
                usuario.getId(),
                usuario.getNombre(),
                usuario.getCorreo(),
                usuario.getRol(),
                usuario.isActivo(),
                usuario.isTwoFactorEnabled(),
                usuario.getFechaCreacion(),
                usuario.getFechaModificacion()
        );
    }

    private Map<String, Object> error(
            String mensaje
    ) {
        Map<String, Object> response =
                new LinkedHashMap<>();

        response.put("ok", false);
        response.put("error", mensaje);

        return response;
    }

    public record UsuarioAdminResponse(
            Long id,
            String nombre,
            String correo,
            String rol,
            boolean activo,
            boolean twoFactorEnabled,
            java.time.LocalDateTime fechaCreacion,
            java.time.LocalDateTime fechaModificacion
    ) {
    }
}
