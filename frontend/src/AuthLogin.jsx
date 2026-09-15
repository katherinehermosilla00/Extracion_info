import React, { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Divider,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

const API_URL = "http://localhost:8080";

export default function AuthLogin({ onAuthenticated }) {
  const [modo, setModo] = useState("login");

  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [confirmarPassword, setConfirmarPassword] = useState("");

  const [codigo, setCodigo] = useState("");
  const [requiere2FA, setRequiere2FA] = useState(false);

  const [resetToken, setResetToken] = useState("");

  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("resetToken");

    if (token) {
      setResetToken(token);
      setModo("reset");
      setError("");
      setSuccess("");
      setPassword("");
      setConfirmarPassword("");
    }
  }, []);

  function limpiarFormulario() {
    setNombre("");
    setCorreo("");
    setPassword("");
    setConfirmarPassword("");
    setCodigo("");
    setRequiere2FA(false);
    setError("");
    setSuccess("");
  }

  function cambiarModo(nuevoModo) {
    limpiarFormulario();
    setModo(nuevoModo);
  }

  async function iniciarSesion(event) {
    event.preventDefault();

    setCargando(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_URL}/api/auth/login`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            correo: correo.trim(),
            password,
            codigo: codigo.trim() || null,
          }),
        }
      );

      const data = await response.json();

      if (data.requiresTwoFactor) {
        setRequiere2FA(true);
        setError("");
        return;
      }

      if (
        !response.ok ||
        !data.authenticated ||
        !data.token
      ) {
        throw new Error(
          data.message || "Credenciales inválidas"
        );
      }

      sessionStorage.setItem(
        "tourSearchToken",
        data.token
      );

      sessionStorage.setItem(
        "tourSearchUser",
        JSON.stringify({
          id: data.id,
          nombre: data.nombre,
          correo: data.correo,
          rol: data.rol,
          twoFactorEnabled: data.twoFactorEnabled,
        })
      );

      if (onAuthenticated) {
        onAuthenticated(data);
      }
    } catch (err) {
      setError(
        err.message ||
          "No fue posible iniciar sesión"
      );
    } finally {
      setCargando(false);
    }
  }

  async function registrar(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!nombre.trim()) {
      setError("Debes ingresar tu nombre");
      return;
    }

    if (!correo.trim()) {
      setError("Debes ingresar tu correo");
      return;
    }

    if (!password) {
      setError("Debes ingresar una contraseña");
      return;
    }

    if (password.length < 8) {
      setError(
        "La contraseña debe tener al menos 8 caracteres"
      );
      return;
    }

    if (password !== confirmarPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    setCargando(true);

    try {
      const response = await fetch(
        `${API_URL}/api/auth/register`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            nombre: nombre.trim(),
            correo: correo.trim(),
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.message ||
            "No fue posible crear la cuenta"
        );
      }

      limpiarFormulario();
      setModo("login");

      setSuccess(
        "Cuenta creada correctamente. Ya puedes iniciar sesión."
      );
    } catch (err) {
      setError(
        err.message ||
          "No fue posible crear la cuenta"
      );
    } finally {
      setCargando(false);
    }
  }

  async function recuperarPassword(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!correo.trim()) {
      setError("Debes ingresar tu correo");
      return;
    }

    setCargando(true);

    try {
      const response = await fetch(
        `${API_URL}/api/auth/forgot-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            correo: correo.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.message ||
            "No fue posible solicitar la recuperación"
        );
      }

      setSuccess(
        data.message ||
          "Si existe una cuenta asociada a ese correo, recibirás instrucciones para restablecer tu contraseña."
      );
    } catch (err) {
      setError(
        err.message ||
          "No fue posible solicitar la recuperación"
      );
    } finally {
      setCargando(false);
    }
  }

  async function restablecerPassword(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!resetToken) {
      setError(
        "El enlace de recuperación no contiene un token válido"
      );
      return;
    }

    if (!password) {
      setError(
        "Debes ingresar una nueva contraseña"
      );
      return;
    }

    if (password.length < 8) {
      setError(
        "La nueva contraseña debe tener al menos 8 caracteres"
      );
      return;
    }

    if (password !== confirmarPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    setCargando(true);

    try {
      const response = await fetch(
        `${API_URL}/api/auth/reset-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token: resetToken,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.message ||
            "No fue posible cambiar la contraseña"
        );
      }

      setPassword("");
      setConfirmarPassword("");
      setResetToken("");
      setModo("login");

      window.history.replaceState(
        {},
        document.title,
        window.location.pathname
      );

      setSuccess(
        data.message ||
          "La contraseña fue actualizada correctamente. Ya puedes iniciar sesión."
      );
    } catch (err) {
      setError(
        err.message ||
          "No fue posible cambiar la contraseña"
      );
    } finally {
      setCargando(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        boxSizing: "border-box",
      }}
    >
      <Paper
        shadow="xl"
        radius="lg"
        p="xl"
        w="100%"
        maw={500}
      >
        <Stack gap="md">
          <Title
            order={2}
            ta="center"
          >
            Tour Search
          </Title>

          {modo === "login" && (
            <Text
              ta="center"
              c="dimmed"
            >
              Acceso a la plataforma
            </Text>
          )}

          {modo === "register" && (
            <Text
              ta="center"
              c="dimmed"
            >
              Crear una cuenta
            </Text>
          )}

          {modo === "forgot" && (
            <Text
              ta="center"
              c="dimmed"
            >
              Recuperar contraseña
            </Text>
          )}

          {modo === "reset" && (
            <Text
              ta="center"
              c="dimmed"
            >
              Crear nueva contraseña
            </Text>
          )}

          {error && (
            <Alert
              color="red"
              title="No fue posible continuar"
            >
              {error}
            </Alert>
          )}

          {success && (
            <Alert
              color="green"
              title="Proceso completado"
            >
              {success}
            </Alert>
          )}

          {modo === "login" && (
            <form onSubmit={iniciarSesion}>
              <Stack gap="md">
                <TextInput
                  label="Correo electrónico"
                  placeholder="correo@ejemplo.com"
                  value={correo}
                  onChange={(event) =>
                    setCorreo(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <PasswordInput
                  label="Contraseña"
                  placeholder="Ingresa tu contraseña"
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                {requiere2FA && (
                  <TextInput
                    label="Código de Google Authenticator"
                    placeholder="123456"
                    value={codigo}
                    maxLength={6}
                    onChange={(event) =>
                      setCodigo(
                        event.currentTarget.value.replace(
                          /\D/g,
                          ""
                        )
                      )
                    }
                    required
                  />
                )}

                <Button
                  type="submit"
                  loading={cargando}
                  fullWidth
                >
                  Iniciar sesión
                </Button>

                <Button
                  variant="subtle"
                  type="button"
                  onClick={() =>
                    cambiarModo("forgot")
                  }
                >
                  ¿Olvidaste tu contraseña?
                </Button>
              </Stack>
            </form>
          )}

          {modo === "register" && (
            <form onSubmit={registrar}>
              <Stack gap="md">
                <TextInput
                  label="Nombre"
                  placeholder="Tu nombre"
                  value={nombre}
                  onChange={(event) =>
                    setNombre(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <TextInput
                  label="Correo electrónico"
                  placeholder="correo@ejemplo.com"
                  value={correo}
                  onChange={(event) =>
                    setCorreo(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <PasswordInput
                  label="Contraseña"
                  placeholder="Mínimo 8 caracteres"
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <PasswordInput
                  label="Confirmar contraseña"
                  placeholder="Repite tu contraseña"
                  value={confirmarPassword}
                  onChange={(event) =>
                    setConfirmarPassword(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <Button
                  type="submit"
                  loading={cargando}
                  fullWidth
                >
                  Crear cuenta
                </Button>

                <Button
                  variant="subtle"
                  type="button"
                  onClick={() =>
                    cambiarModo("login")
                  }
                >
                  Volver a iniciar sesión
                </Button>
              </Stack>
            </form>
          )}

          {modo === "forgot" && (
            <form
              onSubmit={recuperarPassword}
            >
              <Stack gap="md">
                <Text ta="center">
                  Ingresa el correo asociado a tu
                  cuenta. Te enviaremos un enlace
                  para crear una nueva contraseña.
                </Text>

                <TextInput
                  label="Correo electrónico"
                  placeholder="correo@ejemplo.com"
                  value={correo}
                  onChange={(event) =>
                    setCorreo(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <Button
                  type="submit"
                  loading={cargando}
                  fullWidth
                >
                  Enviar instrucciones
                </Button>

                <Button
                  variant="subtle"
                  type="button"
                  onClick={() =>
                    cambiarModo("login")
                  }
                >
                  Volver a iniciar sesión
                </Button>
              </Stack>
            </form>
          )}

          {modo === "reset" && (
            <form
              onSubmit={restablecerPassword}
            >
              <Stack gap="md">
                <Text ta="center">
                  Ingresa tu nueva contraseña.
                  Debe contener al menos 8
                  caracteres.
                </Text>

                <PasswordInput
                  label="Nueva contraseña"
                  placeholder="Nueva contraseña"
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <PasswordInput
                  label="Confirmar nueva contraseña"
                  placeholder="Repite la nueva contraseña"
                  value={confirmarPassword}
                  onChange={(event) =>
                    setConfirmarPassword(
                      event.currentTarget.value
                    )
                  }
                  required
                />

                <Button
                  type="submit"
                  loading={cargando}
                  fullWidth
                >
                  Cambiar contraseña
                </Button>

                <Button
                  variant="subtle"
                  type="button"
                  onClick={() => {
                    window.history.replaceState(
                      {},
                      document.title,
                      window.location.pathname
                    );

                    setResetToken("");
                    cambiarModo("login");
                  }}
                >
                  Volver a iniciar sesión
                </Button>
              </Stack>
            </form>
          )}

          {(modo === "login" ||
            modo === "register") && (
            <>
              <Divider
                label="o"
                labelPosition="center"
              />

              {modo === "login" && (
                <>
                  <Text ta="center">
                    ¿Aún no tienes una cuenta?
                  </Text>

                  <Button
                    variant="light"
                    type="button"
                    onClick={() =>
                      cambiarModo("register")
                    }
                    fullWidth
                  >
                    Crear cuenta
                  </Button>
                </>
              )}
            </>
          )}

          <Divider />

          <Text
            size="xs"
            ta="center"
            c="dimmed"
          >
            Acceso protegido con contraseña,
            Google Authenticator y JWT.
          </Text>
        </Stack>
      </Paper>
    </div>
  );
}