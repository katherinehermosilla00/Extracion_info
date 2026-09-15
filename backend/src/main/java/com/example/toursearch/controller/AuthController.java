package com.example.toursearch.controller;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.toursearch.entity.Usuario;
import com.example.toursearch.service.AuthService;
import com.example.toursearch.service.AuthService.Setup2FA;
import com.example.toursearch.service.AuthService.TwoFactorRequiredException;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /*
     * ========================================================
     * REGISTRO
     * ========================================================
     */

    @PostMapping("/register")
    public ResponseEntity<?> registrar(
            @RequestBody RegisterRequest request
    ) {

        try {

            Usuario usuario = authService.registrar(
                    request.nombre(),
                    request.correo(),
                    request.password()
            );

            return ResponseEntity
                    .status(HttpStatus.CREATED)
                    .body(
                            Map.of(
                                    "ok", true,
                                    "id", usuario.getId(),
                                    "nombre", usuario.getNombre(),
                                    "correo", usuario.getCorreo(),
                                    "rol", usuario.getRol(),
                                    "twoFactorEnabled",
                                    usuario.isTwoFactorEnabled()
                            )
                    );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .badRequest()
                    .body(
                            Map.of(
                                    "ok", false,
                                    "message", e.getMessage()
                            )
                    );
        }
    }

    /*
     * ========================================================
     * LOGIN
     * ========================================================
     */

    @PostMapping("/login")
    public ResponseEntity<?> login(
            @RequestBody LoginRequest request
    ) {

        try {

            Usuario usuario = authService.login(
                    request.correo(),
                    request.password(),
                    request.codigo()
            );

            String token =
                    authService.generarToken(usuario);

            return ResponseEntity.ok(
                    Map.of(
                            "ok", true,
                            "authenticated", true,
                            "requiresTwoFactor", false,
                            "token", token,
                            "id", usuario.getId(),
                            "nombre", usuario.getNombre(),
                            "correo", usuario.getCorreo(),
                            "rol", usuario.getRol(),
                            "twoFactorEnabled",
                            usuario.isTwoFactorEnabled()
                    )
            );

        } catch (TwoFactorRequiredException e) {

            return ResponseEntity.ok(
                    Map.of(
                            "ok", true,
                            "authenticated", false,
                            "requiresTwoFactor", true,
                            "message", e.getMessage()
                    )
            );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .status(HttpStatus.UNAUTHORIZED)
                    .body(
                            Map.of(
                                    "ok", false,
                                    "authenticated", false,
                                    "message", e.getMessage()
                            )
                    );
        }
    }

    /*
     * ========================================================
     * RECUPERACIÓN DE CONTRASEÑA
     * ========================================================
     */

    @PostMapping("/forgot-password")
    public ResponseEntity<?> solicitarRecuperacion(
            @RequestBody ForgotPasswordRequest request
    ) {

        try {

            authService.solicitarRecuperacionPassword(
                    request.correo()
            );

            return ResponseEntity.ok(
                    Map.of(
                            "ok", true,
                            "message",
                            "Si existe una cuenta asociada a ese correo, recibirás instrucciones para restablecer tu contraseña."
                    )
            );

        } catch (Exception e) {

            return ResponseEntity
                    .status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(
                            Map.of(
                                    "ok", false,
                                    "message",
                                    "No fue posible procesar la recuperación de contraseña."
                            )
                    );
        }
    }

    @PostMapping("/reset-password")
    public ResponseEntity<?> restablecerPassword(
            @RequestBody ResetPasswordRequest request
    ) {

        try {

            authService.restablecerPassword(
                    request.token(),
                    request.password()
            );

            return ResponseEntity.ok(
                    Map.of(
                            "ok", true,
                            "message",
                            "La contraseña fue actualizada correctamente."
                    )
            );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .badRequest()
                    .body(
                            Map.of(
                                    "ok", false,
                                    "message", e.getMessage()
                            )
                    );
        }
    }

    /*
     * ========================================================
     * CONFIGURACIÓN 2FA
     * ========================================================
     */

    @PostMapping("/2fa/setup")
    public ResponseEntity<?> iniciar2FA(
            @RequestBody TwoFactorSetupRequest request
    ) {

        try {

            Setup2FA setup =
                    authService.iniciarConfiguracion2FA(
                            request.correo(),
                            request.password(),
                            request.codigoActual()
                    );

            return ResponseEntity.ok(
                    Map.of(
                            "ok", true,
                            "secret", setup.secreto(),
                            "otpauthUri", setup.otpauthUri()
                    )
            );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .badRequest()
                    .body(
                            Map.of(
                                    "ok", false,
                                    "message", e.getMessage()
                            )
                    );
        }
    }

    @PostMapping("/2fa/confirm")
    public ResponseEntity<?> confirmar2FA(
            @RequestBody TwoFactorConfirmRequest request
    ) {

        try {

            authService.confirmar2FA(
                    request.correo(),
                    request.password(),
                    request.codigo()
            );

            return ResponseEntity.ok(
                    Map.of(
                            "ok", true,
                            "message",
                            "Google Authenticator fue configurado correctamente."
                    )
            );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .badRequest()
                    .body(
                            Map.of(
                                    "ok", false,
                                    "message", e.getMessage()
                            )
                    );
        }
    }

    @PostMapping("/2fa/verify")
    public ResponseEntity<?> verificar2FA(
            @RequestBody TwoFactorVerifyRequest request
    ) {

        try {

            boolean valido =
                    authService.verificarCodigo2FA(
                            request.correo(),
                            request.password(),
                            request.codigo()
                    );

            return ResponseEntity.ok(
                    Map.of(
                            "ok", true,
                            "valid", valido
                    )
            );

        } catch (IllegalArgumentException e) {

            return ResponseEntity
                    .badRequest()
                    .body(
                            Map.of(
                                    "ok", false,
                                    "valid", false,
                                    "message", e.getMessage()
                            )
                    );
        }
    }

    /*
     * ========================================================
     * USUARIO AUTENTICADO
     * ========================================================
     */

    @GetMapping("/me")
    public ResponseEntity<Map<String, Object>> me(
            Authentication authentication
    ) {

        Map<String, Object> response =
                new LinkedHashMap<>();

        if (authentication == null ||
                !authentication.isAuthenticated()) {

            response.put("ok", true);
            response.put("authenticated", false);
            response.put("correo", null);
            response.put("roles", List.of());
            response.put("admin", false);

            return ResponseEntity.ok(response);
        }

        List<String> roles =
                authentication
                        .getAuthorities()
                        .stream()
                        .map(authority ->
                                authority.getAuthority()
                        )
                        .toList();

        response.put("ok", true);
        response.put("authenticated", true);
        response.put(
                "correo",
                authentication.getName()
        );
        response.put("roles", roles);
        response.put(
                "admin",
                roles.contains("ROLE_ADMIN")
        );

        return ResponseEntity.ok(response);
    }

    /*
     * ========================================================
     * DTOs
     * ========================================================
     */

    public record RegisterRequest(
            String nombre,
            String correo,
            String password
    ) {
    }

    public record LoginRequest(
            String correo,
            String password,
            String codigo
    ) {
    }

    public record ForgotPasswordRequest(
            String correo
    ) {
    }

    public record ResetPasswordRequest(
            String token,
            String password
    ) {
    }

    public record TwoFactorSetupRequest(
            String correo,
            String password,
            String codigoActual
    ) {
    }

    public record TwoFactorConfirmRequest(
            String correo,
            String password,
            String codigo
    ) {
    }

    public record TwoFactorVerifyRequest(
            String correo,
            String password,
            String codigo
    ) {
    }
}