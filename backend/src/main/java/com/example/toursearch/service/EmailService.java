package com.example.toursearch.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

@Service
public class EmailService {

    private final JavaMailSender mailSender;

    @Value("${spring.mail.username:}")
    private String remitente;

    @Value("${app.frontend-url:http://localhost:5173}")
    private String frontendUrl;

    public EmailService(JavaMailSender mailSender) {
        this.mailSender = mailSender;
    }

    public void enviarCorreoRecuperacion(
            String destinatario,
            String nombre,
            String token
    ) {

        if (destinatario == null || destinatario.isBlank()) {
            throw new IllegalArgumentException(
                    "El destinatario es obligatorio"
            );
        }

        if (token == null || token.isBlank()) {
            throw new IllegalArgumentException(
                    "El token de recuperación es obligatorio"
            );
        }

        if (remitente == null || remitente.isBlank()) {
            throw new IllegalStateException(
                    "El servidor de correo todavía no está configurado"
            );
        }

        String enlace =
                frontendUrl
                        + "/?resetToken="
                        + token;

        String nombreUsuario =
                nombre == null || nombre.isBlank()
                        ? "usuario"
                        : nombre.trim();

        String cuerpo =
                """
                Hola %s,

                Recibimos una solicitud para cambiar la contraseña de tu cuenta en Tour Search.

                Para crear una nueva contraseña, utiliza el siguiente enlace:

                %s

                Este enlace tiene una duración limitada.

                Si no solicitaste este cambio, puedes ignorar este mensaje.

                Tour Search
                """.formatted(
                        nombreUsuario,
                        enlace
                );

        SimpleMailMessage mensaje =
                new SimpleMailMessage();

        mensaje.setFrom(remitente);
        mensaje.setTo(destinatario);
        mensaje.setSubject(
                "Recuperación de contraseña - Tour Search"
        );
        mensaje.setText(cuerpo);

        mailSender.send(mensaje);
    }
}