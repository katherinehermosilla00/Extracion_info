package com.example.toursearch.security;

import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import java.net.URLEncoder;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;

@Service
public class TotpService {

    private static final String BASE32 =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

    private static final int SECRET_LENGTH = 20;

    private static final long TIME_STEP_SECONDS = 30;

    private static final int DIGITS = 6;

    private final SecureRandom secureRandom =
            new SecureRandom();

    public String generarSecreto() {

        byte[] bytes =
                new byte[SECRET_LENGTH];

        secureRandom.nextBytes(bytes);

        return codificarBase32(bytes);
    }

    public String generarOtpAuthUri(
            String correo,
            String secreto
    ) {

        String issuer =
                "Tour Search Platform";

        String label =
                issuer + ":" + correo;

        return "otpauth://totp/"
                + encode(label)
                + "?secret="
                + secreto
                + "&issuer="
                + encode(issuer)
                + "&algorithm=SHA1"
                + "&digits=6"
                + "&period=30";
    }

    public boolean validarCodigo(
            String secreto,
            String codigo
    ) {

        if (secreto == null ||
                secreto.isBlank() ||
                codigo == null ||
                !codigo.matches("\\d{6}")) {

            return false;
        }

        long contadorActual =
                System.currentTimeMillis()
                        / 1000
                        / TIME_STEP_SECONDS;

        // Permitimos una pequeña tolerancia de reloj:
        // intervalo anterior, actual y siguiente.
        for (long offset = -1;
             offset <= 1;
             offset++) {

            String esperado =
                    generarCodigo(
                            secreto,
                            contadorActual + offset
                    );

            if (esperado.equals(codigo)) {
                return true;
            }
        }

        return false;
    }

    private String generarCodigo(
            String secreto,
            long contador
    ) {

        try {

            byte[] clave =
                    decodificarBase32(secreto);

            byte[] data =
                    ByteBuffer
                            .allocate(8)
                            .putLong(contador)
                            .array();

            Mac mac =
                    Mac.getInstance("HmacSHA1");

            mac.init(
                    new SecretKeySpec(
                            clave,
                            "HmacSHA1"
                    )
            );

            byte[] hash =
                    mac.doFinal(data);

            int offset =
                    hash[hash.length - 1]
                            & 0x0F;

            int binario =
                    ((hash[offset] & 0x7F) << 24)
                            | ((hash[offset + 1] & 0xFF) << 16)
                            | ((hash[offset + 2] & 0xFF) << 8)
                            | (hash[offset + 3] & 0xFF);

            int modulo =
                    (int) Math.pow(
                            10,
                            DIGITS
                    );

            int otp =
                    binario % modulo;

            return String.format(
                    "%0" + DIGITS + "d",
                    otp
            );

        } catch (Exception e) {

            throw new IllegalStateException(
                    "No se pudo generar el código TOTP",
                    e
            );
        }
    }

    private String codificarBase32(
            byte[] datos
    ) {

        StringBuilder resultado =
                new StringBuilder();

        int buffer = 0;
        int bits = 0;

        for (byte dato : datos) {

            buffer =
                    (buffer << 8)
                            | (dato & 0xFF);

            bits += 8;

            while (bits >= 5) {

                int indice =
                        (buffer
                                >> (bits - 5))
                                & 0x1F;

                resultado.append(
                        BASE32.charAt(indice)
                );

                bits -= 5;
            }
        }

        if (bits > 0) {

            int indice =
                    (buffer << (5 - bits))
                            & 0x1F;

            resultado.append(
                    BASE32.charAt(indice)
            );
        }

        return resultado.toString();
    }

    private byte[] decodificarBase32(
            String secreto
    ) {

        String limpio =
                secreto
                        .replace("=", "")
                        .replace(" ", "")
                        .toUpperCase();

        ByteBuffer salida =
                ByteBuffer.allocate(
                        (limpio.length() * 5)
                                / 8
                                + 1
                );

        int buffer = 0;
        int bits = 0;

        for (char c :
                limpio.toCharArray()) {

            int valor =
                    BASE32.indexOf(c);

            if (valor < 0) {
                throw new IllegalArgumentException(
                        "Secreto TOTP inválido"
                );
            }

            buffer =
                    (buffer << 5)
                            | valor;

            bits += 5;

            if (bits >= 8) {

                salida.put(
                        (byte) (
                                buffer
                                        >> (bits - 8)
                        )
                );

                bits -= 8;
            }
        }

        byte[] resultado =
                new byte[salida.position()];

        salida.flip();
        salida.get(resultado);

        return resultado;
    }

    private String encode(
            String valor
    ) {

        return URLEncoder.encode(
                valor,
                StandardCharsets.UTF_8
        ).replace("+", "%20");
    }
}