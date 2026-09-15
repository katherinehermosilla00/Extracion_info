package com.example.toursearch.security;

import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.Set;

import org.springframework.stereotype.Service;

@Service
public class UrlValidationService {

    private static final Set<String> ALLOWED_SCHEMES =
            Set.of("http", "https");

    public void validate(String url) {

        if (url == null || url.isBlank()) {
            throw new IllegalArgumentException(
                    "La URL no puede estar vacía"
            );
        }

        try {

            URI uri = URI.create(url);

            String scheme = uri.getScheme();
            String host = uri.getHost();

            // Solo permitimos HTTP y HTTPS
            if (scheme == null ||
                    !ALLOWED_SCHEMES.contains(
                            scheme.toLowerCase()
                    )) {

                throw new IllegalArgumentException(
                        "Solo se permiten URLs HTTP o HTTPS"
                );
            }

            // La URL debe tener dominio/host
            if (host == null || host.isBlank()) {

                throw new IllegalArgumentException(
                        "La URL no contiene un host válido"
                );
            }

            String normalizedHost = host.toLowerCase();

            // Bloquear localhost
            if (normalizedHost.equals("localhost")
                    || normalizedHost.endsWith(
                            ".localhost"
                    )) {

                throw new IllegalArgumentException(
                        "No se permite acceder a localhost"
                );
            }

            // Resolver el dominio a todas sus direcciones IP
            InetAddress[] addresses =
                    InetAddress.getAllByName(host);

            for (InetAddress address : addresses) {

                // Bloquear direcciones locales,
                // privadas y link-local
                if (address.isLoopbackAddress()
                        || address.isSiteLocalAddress()
                        || address.isLinkLocalAddress()
                        || address.isAnyLocalAddress()) {

                    throw new IllegalArgumentException(
                            "La URL apunta a una red interna o privada"
                    );
                }
            }

        } catch (IllegalArgumentException e) {

            // Mantener nuestros bloqueos de seguridad
            // con su mensaje original.
            throw e;

        } catch (UnknownHostException e) {

            // El dominio no pudo resolverse por DNS.
            throw new IllegalArgumentException(
                    "No fue posible resolver el dominio de la URL: "
                            + e.getMessage(),
                    e
            );
        }
    }
}