package com.example.toursearch.service;

import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.Locale;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.example.toursearch.entity.Usuario;
import com.example.toursearch.repository.UsuarioRepository;
import com.example.toursearch.security.JwtService;
import com.example.toursearch.security.TotpService;

@Service
public class AuthService {

    private final UsuarioRepository usuarioRepository;
    private final PasswordEncoder passwordEncoder;
    private final TotpService totpService;
    private final JwtService jwtService;
    private final EmailService emailService;

    @Value("${app.password-reset.expiration-minutes:30}")
    private long passwordResetExpirationMinutes;

    public AuthService(
            UsuarioRepository usuarioRepository,
            PasswordEncoder passwordEncoder,
            TotpService totpService,
            JwtService jwtService,
            EmailService emailService
    ) {
        this.usuarioRepository = usuarioRepository;
        this.passwordEncoder = passwordEncoder;
        this.totpService = totpService;
        this.jwtService = jwtService;
        this.emailService = emailService;
    }

    @Transactional
    public Usuario registrar(
            String nombre,
            String correo,
            String password
    ) {

        if (nombre == null || nombre.isBlank()) {
            throw new IllegalArgumentException(
                    "El nombre es obligatorio"
            );
        }

        if (correo == null || correo.isBlank()) {
            throw new IllegalArgumentException(
                    "El correo es obligatorio"
            );
        }

        if (password == null || password.isBlank()) {
            throw new IllegalArgumentException(
                    "La contraseña es obligatoria"
            );
        }

        if (password.length() < 8) {
            throw new IllegalArgumentException(
                    "La contraseña debe tener al menos 8 caracteres"
            );
        }

        String correoNormalizado =
                normalizarCorreo(correo);

        if (usuarioRepository
                .existsByCorreoIgnoreCase(
                        correoNormalizado
                )) {

            throw new IllegalArgumentException(
                    "Ya existe un usuario con ese correo"
            );
        }

        Usuario usuario = new Usuario();

        usuario.setNombre(nombre.trim());
        usuario.setCorreo(correoNormalizado);

        usuario.setPasswordHash(
                passwordEncoder.encode(password)
        );

        usuario.setActivo(true);
        usuario.setTwoFactorEnabled(false);
        usuario.setTwoFactorSecret(null);
        usuario.setTwoFactorPendingSecret(null);

        usuario.setPasswordResetToken(null);
        usuario.setPasswordResetExpiration(null);

        return usuarioRepository.save(usuario);
    }

    public Usuario validarCredenciales(
            String correo,
            String password
    ) {

        if (correo == null || correo.isBlank()) {
            throw new IllegalArgumentException(
                    "El correo es obligatorio"
            );
        }

        if (password == null || password.isBlank()) {
            throw new IllegalArgumentException(
                    "La contraseña es obligatoria"
            );
        }

        String correoNormalizado =
                normalizarCorreo(correo);

        Usuario usuario =
                usuarioRepository
                        .findByCorreoIgnoreCase(
                                correoNormalizado
                        )
                        .orElseThrow(
                                () ->
                                        new IllegalArgumentException(
                                                "Credenciales inválidas"
                                        )
                        );

        if (!usuario.isActivo()) {
            throw new IllegalArgumentException(
                    "Usuario deshabilitado"
            );
        }

        if (!passwordEncoder.matches(
                password,
                usuario.getPasswordHash()
        )) {
            throw new IllegalArgumentException(
                    "Credenciales inválidas"
            );
        }

        return usuario;
    }

    /*
     * ========================================================
     * RECUPERACIÓN DE CONTRASEÑA
     * ========================================================
     */

    @Transactional
    public void solicitarRecuperacionPassword(
            String correo
    ) {

        if (correo == null || correo.isBlank()) {
            return;
        }

        String correoNormalizado =
                normalizarCorreo(correo);

        Usuario usuario =
                usuarioRepository
                        .findByCorreoIgnoreCase(
                                correoNormalizado
                        )
                        .orElse(null);

        /*
         * No informamos si el correo existe o no.
         * Esto evita exponer usuarios registrados.
         */
        if (usuario == null) {
            return;
        }

        if (!usuario.isActivo()) {
            return;
        }

        String token =
                generarTokenRecuperacion();

        LocalDateTime expiracion =
                LocalDateTime
                        .now()
                        .plusMinutes(
                                passwordResetExpirationMinutes
                        );

        usuario.setPasswordResetToken(token);
        usuario.setPasswordResetExpiration(expiracion);

        usuarioRepository.save(usuario);

        try {

            emailService.enviarCorreoRecuperacion(
                    usuario.getCorreo(),
                    usuario.getNombre(),
                    token
            );

        } catch (RuntimeException e) {

            /*
             * Si falla el envío del correo, eliminamos
             * el token para no dejar una recuperación
             * inválida pendiente.
             */

            usuario.setPasswordResetToken(null);
            usuario.setPasswordResetExpiration(null);

            usuarioRepository.save(usuario);

            throw e;
        }
    }

    @Transactional
    public void restablecerPassword(
            String token,
            String nuevaPassword
    ) {

        if (token == null || token.isBlank()) {
            throw new IllegalArgumentException(
                    "El token de recuperación es obligatorio"
            );
        }

        if (nuevaPassword == null ||
                nuevaPassword.isBlank()) {

            throw new IllegalArgumentException(
                    "La nueva contraseña es obligatoria"
            );
        }

        if (nuevaPassword.length() < 8) {
            throw new IllegalArgumentException(
                    "La nueva contraseña debe tener al menos 8 caracteres"
            );
        }

        Usuario usuario =
                usuarioRepository
                        .findByPasswordResetToken(token)
                        .orElseThrow(
                                () ->
                                        new IllegalArgumentException(
                                                "El enlace de recuperación no es válido"
                                        )
                        );

        LocalDateTime expiracion =
                usuario.getPasswordResetExpiration();

        if (expiracion == null ||
                expiracion.isBefore(
                        LocalDateTime.now()
                )) {

            usuario.setPasswordResetToken(null);
            usuario.setPasswordResetExpiration(null);

            usuarioRepository.save(usuario);

            throw new IllegalArgumentException(
                    "El enlace de recuperación ha expirado"
            );
        }

        if (!usuario.isActivo()) {
            throw new IllegalArgumentException(
                    "Usuario deshabilitado"
            );
        }

        usuario.setPasswordHash(
                passwordEncoder.encode(
                        nuevaPassword
                )
        );

        /*
         * Token de un solo uso:
         * después del cambio se elimina.
         */
        usuario.setPasswordResetToken(null);
        usuario.setPasswordResetExpiration(null);

        usuarioRepository.save(usuario);
    }

    private String generarTokenRecuperacion() {

        byte[] bytes =
                new byte[32];

        SecureRandom secureRandom =
                new SecureRandom();

        secureRandom.nextBytes(bytes);

        return Base64
                .getUrlEncoder()
                .withoutPadding()
                .encodeToString(bytes);
    }

    /*
     * ========================================================
     * CONFIGURACIÓN / RECONFIGURACIÓN 2FA
     * ========================================================
     */

    @Transactional
    public Setup2FA iniciarConfiguracion2FA(
            String correo,
            String password,
            String codigoActual
    ) {

        Usuario usuario =
                validarCredenciales(
                        correo,
                        password
                );

        if (usuario.isTwoFactorEnabled()) {

            if (codigoActual == null
                    || codigoActual.isBlank()) {

                throw new IllegalArgumentException(
                        "Debes ingresar el código actual de Google Authenticator para reconfigurar el 2FA"
                );
            }

            String secretoActual =
                    usuario.getTwoFactorSecret();

            if (secretoActual == null
                    || secretoActual.isBlank()) {

                throw new IllegalArgumentException(
                        "El usuario no posee un secreto 2FA válido"
                );
            }

            if (!totpService.validarCodigo(
                    secretoActual,
                    codigoActual
            )) {

                throw new IllegalArgumentException(
                        "Código actual de Google Authenticator inválido"
                );
            }
        }

        String secretoPendiente =
                totpService.generarSecreto();

        usuario.setTwoFactorPendingSecret(
                secretoPendiente
        );

        usuarioRepository.save(usuario);

        String otpauthUri =
                totpService.generarOtpAuthUri(
                        usuario.getCorreo(),
                        secretoPendiente
                );

        return new Setup2FA(
                secretoPendiente,
                otpauthUri
        );
    }

    @Transactional
    public void confirmar2FA(
            String correo,
            String password,
            String codigo
    ) {

        Usuario usuario =
                validarCredenciales(
                        correo,
                        password
                );

        if (codigo == null || codigo.isBlank()) {
            throw new IllegalArgumentException(
                    "El código de Google Authenticator es obligatorio"
            );
        }

        String secretoPendiente =
                usuario.getTwoFactorPendingSecret();

        if (secretoPendiente == null
                || secretoPendiente.isBlank()) {

            throw new IllegalArgumentException(
                    "No existe una configuración 2FA pendiente"
            );
        }

        boolean valido =
                totpService.validarCodigo(
                        secretoPendiente,
                        codigo
                );

        if (!valido) {
            throw new IllegalArgumentException(
                    "Código de Google Authenticator inválido"
            );
        }

        usuario.setTwoFactorSecret(
                secretoPendiente
        );

        usuario.setTwoFactorPendingSecret(null);
        usuario.setTwoFactorEnabled(true);

        usuarioRepository.save(usuario);
    }

    public Usuario login(
            String correo,
            String password,
            String codigo
    ) {

        Usuario usuario =
                validarCredenciales(
                        correo,
                        password
                );

        if (usuario.isTwoFactorEnabled()) {

            if (codigo == null || codigo.isBlank()) {
                throw new TwoFactorRequiredException();
            }

            String secreto =
                    usuario.getTwoFactorSecret();

            if (secreto == null
                    || secreto.isBlank()) {

                throw new IllegalArgumentException(
                        "Configuración 2FA inválida"
                );
            }

            boolean valido =
                    totpService.validarCodigo(
                            secreto,
                            codigo
                    );

            if (!valido) {
                throw new IllegalArgumentException(
                        "Código de Google Authenticator inválido"
                );
            }
        }

        return usuario;
    }

    public boolean verificarCodigo2FA(
            String correo,
            String password,
            String codigo
    ) {

        Usuario usuario =
                validarCredenciales(
                        correo,
                        password
                );

        if (!usuario.isTwoFactorEnabled()) {
            throw new IllegalArgumentException(
                    "El usuario no tiene 2FA activado"
            );
        }

        String secreto =
                usuario.getTwoFactorSecret();

        if (secreto == null ||
                secreto.isBlank()) {

            throw new IllegalArgumentException(
                    "Configuración 2FA inválida"
            );
        }

        if (codigo == null || codigo.isBlank()) {
            return false;
        }

        return totpService.validarCodigo(
                secreto,
                codigo
        );
    }

    public String generarToken(
            Usuario usuario
    ) {

        if (usuario == null) {
            throw new IllegalArgumentException(
                    "Usuario inválido"
            );
        }

        return jwtService.generarToken(usuario);
    }

    private String normalizarCorreo(
            String correo
    ) {

        return correo
                .trim()
                .toLowerCase(Locale.ROOT);
    }

    public record Setup2FA(
            String secreto,
            String otpauthUri
    ) {
    }

    public static class TwoFactorRequiredException
            extends RuntimeException {

        private static final long serialVersionUID = 1L;

        public TwoFactorRequiredException() {
            super(
                    "Se requiere código de Google Authenticator"
            );
        }
    }
}