import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import "@mantine/core/styles.css";

import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Loader,
  MantineProvider,
  Modal,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";

import heroImage from "./assets/volcan-hero.png";

import "./styles.css";
import "./navigation.css";

import AuthLogin from "./AuthLogin.jsx";


// ============================================================
// API
// ============================================================

const SCRAPER_API = "http://localhost:8000";
const BACKEND_API = "http://localhost:8080/api";


// ============================================================
// NAVEGACIÓN
// ============================================================

const NAV = [
  "Inicio",
  "Consultar",
  "Búsqueda",
  "Filtros",
  "Resultados",
  "Historial",
];


// ============================================================
// APP
// ============================================================

function App({ onLogout, isAdmin }) {
  const [view, setView] = useState("Inicio");

  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [directUrl, setDirectUrl] = useState("");
  const [nombreOperador, setNombreOperador] = useState("");

  const [searchForm, setSearchForm] = useState({
    url_operador: "",
    nombre_operador: "",
    pedido: "",
    max_paginas: 3,
    limite: 5,
    puntaje_minimo: 20,
  });

  const [apiResults, setApiResults] = useState([]);
  const [tour, setTour] = useState(null);

  const [operadores, setOperadores] = useState([]);
  const [paises, setPaises] = useState([]);
  const [actividades, setActividades] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [registros, setRegistros] = useState([]);

  const [term, setTerm] = useState("");
  const [filterType, setFilterType] = useState("activity");


  // ==========================================================
  // CARGA INICIAL
  // ==========================================================

  useEffect(() => {
    cargarDatosBase();
  }, []);

  useEffect(() => {
    if (!isAdmin && view === "Administrador") {
      setView("Inicio");
    }
  }, [isAdmin, view]);

  useEffect(() => {
    if (isAdmin) {
      cargarUsuarios();
      cargarRegistros();
    } else {
      setUsuarios([]);
      setRegistros([]);
    }
  }, [isAdmin]);


  async function cargarDatosBase() {
    await Promise.all([
      cargarOperadores(),
      cargarPaises(),
      cargarActividades(),
    ]);
  }


  async function cargarOperadores() {
    try {
      const response = await fetch(
        `${BACKEND_API}/operadores`
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setOperadores(
        Array.isArray(data)
          ? data
          : data.value || []
      );
    } catch (e) {
      console.error(
        "No se pudieron cargar operadores:",
        e
      );
    }
  }


  async function cargarPaises() {
    try {
      const response = await fetch(
        `${BACKEND_API}/paises`
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setPaises(
        Array.isArray(data)
          ? data
          : data.value || []
      );
    } catch (e) {
      console.error(
        "No se pudieron cargar países:",
        e
      );
    }
  }


  async function cargarActividades() {
    try {
      const response = await fetch(
        `${BACKEND_API}/actividades`
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setActividades(
        Array.isArray(data)
          ? data
          : data.value || []
      );
    } catch (e) {
      console.warn(
        "No se pudo cargar el listado general de actividades:",
        e
      );
    }
  }


  async function cargarUsuarios() {
    try {
      const token = sessionStorage.getItem(
        "tourSearchToken"
      );

      if (!token) {
        setUsuarios([]);
        return;
      }

      const response = await fetch(
        `${BACKEND_API}/admin/usuarios`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        setUsuarios([]);
        return;
      }

      const data = await response.json();

      setUsuarios(
        Array.isArray(data)
          ? data
          : []
      );
    } catch (e) {
      console.error(
        "No se pudieron cargar usuarios:",
        e
      );
      setUsuarios([]);
    }
  }


  async function cargarRegistros() {
    try {
      const token = sessionStorage.getItem(
        "tourSearchToken"
      );

      const response = await fetch(
        `${BACKEND_API}/registros`,
        {
          headers: token
            ? {
                Authorization:
                  `Bearer ${token}`,
              }
            : {},
        }
      );

      if (!response.ok) {
        setRegistros([]);
        return;
      }

      const data = await response.json();

      setRegistros(
        Array.isArray(data)
          ? data
          : []
      );
    } catch (e) {
      console.error(
        "No se pudieron cargar registros:",
        e
      );
      setRegistros([]);
    }
  }


  // ==========================================================
  // SCRAPER
  // ==========================================================

  async function postScraper(path, body) {
    const response = await fetch(
      `${SCRAPER_API}${path}`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify(body),
      }
    );

    const data =
      await response
        .json()
        .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
        "No fue posible completar la solicitud."
      );
    }

    return data;
  }


  async function extraerSolo(
    url,
    operador = ""
  ) {
    if (!url?.trim()) {
      setError(
        "Debes ingresar la URL de una actividad."
      );
      return;
    }

    setError("");
    setSuccess("");
    setTour(null);

    try {
      setLoading(
        "Extrayendo información publicada..."
      );

      const data = await postScraper(
        "/scraper/extract",
        {
          url: url.trim(),

          nombre_operador:
            operador.trim() || null,
        }
      );

      setTour(data);

      setView("Resultados");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading("");
    }
  }


  async function extraerYGuardar(
    url,
    operador
  ) {
    if (!url?.trim()) {
      setError(
        "Debes ingresar la URL de la actividad."
      );
      return;
    }

    if (!operador?.trim()) {
      setError(
        "Debes indicar el nombre del Tour Operador."
      );
      return;
    }

    setError("");
    setSuccess("");

    try {
      setLoading(
        "Extrayendo y guardando actividad..."
      );

      const data = await postScraper(
        "/scraper/extract-and-save",
        {
          url: url.trim(),
          nombre_operador: operador.trim(),
        }
      );

      setTour(
        data.tour_extraido ||
        actividadATour(data.actividad) ||
        data
      );

      if (data.accion === "ACTUALIZADA") {
        setSuccess(
          "La actividad ya existía y fue actualizada."
        );
      } else {
        setSuccess(
          "La actividad fue creada correctamente."
        );
      }

      setView("Resultados");

      await cargarActividades();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading("");
    }
  }


  async function buscarOperador(event) {
    event.preventDefault();

    setError("");
    setSuccess("");
    setTour(null);
    setApiResults([]);

    try {
      setLoading(
        "Buscando actividades relacionadas..."
      );

      const data = await postScraper(
        "/scraper/search",
        {
          url_operador:
            searchForm.url_operador,

          pedido:
            searchForm.pedido,

          nombre_operador:
            searchForm.nombre_operador ||
            null,

          max_paginas:
            Number(
              searchForm.max_paginas
            ),

          limite:
            Number(
              searchForm.limite
            ),

          puntaje_minimo:
            Number(
              searchForm.puntaje_minimo
            ),
        }
      );

      setApiResults(
        data.resultados || []
      );

      setView("Resultados");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading("");
    }
  }


  // ==========================================================
  // FILTROS
  // ==========================================================

  const actividadesFiltradas =
    useMemo(() => {
      const query = term
        .trim()
        .toLocaleLowerCase("es");

      if (!query) {
        return actividades;
      }

      return actividades.filter(
        (actividad) => {
          if (
            filterType ===
            "operator"
          ) {
            return (
              actividad
                .operadorTuristico
                ?.nombre || ""
            )
              .toLocaleLowerCase("es")
              .includes(query);
          }

          return (
            actividad.nombre || ""
          )
            .toLocaleLowerCase("es")
            .includes(query);
        }
      );
    }, [
      actividades,
      term,
      filterType,
    ]);


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="site-shell">

      <NavBar
        view={view}
        setView={setView}
        onLogout={onLogout}
        isAdmin={isAdmin}
      />


      {loading && (
        <div className="floating-loading">

          <Loader size="sm" />

          <span>
            {loading}
          </span>

        </div>
      )}


      {error && (
        <div className="container-xl pt-3">

          <Alert
            color="red"
            title="Ocurrió un problema"
            withCloseButton
            onClose={() =>
              setError("")
            }
          >
            {error}
          </Alert>

        </div>
      )}


      {success && (
        <div className="container-xl pt-3">

          <Alert
            color="green"
            title="Operación completada"
            withCloseButton
            onClose={() =>
              setSuccess("")
            }
          >
            {success}
          </Alert>

        </div>
      )}


      {view === "Inicio" && (
        <Home
          setView={setView}
          isAdmin={isAdmin}

          directUrl={directUrl}
          setDirectUrl={setDirectUrl}

          nombreOperador={
            nombreOperador
          }

          setNombreOperador={
            setNombreOperador
          }

          extraerYGuardar={
            extraerYGuardar
          }
        />
      )}


      {view !== "Inicio" && (
        <main
          className={
            view === "Administrador"
              ? "admin-main-wrap"
              : "page-wrap"
          }

          style={
            view === "Administrador"
              ? undefined
              : {
                  "--page-image":
                    `url(${heroImage})`,
                }
          }
        >

          {view !== "Administrador" && (
            <div className="container-xl page-tools">

              <button
                className="back-button"

                onClick={() =>
                  setView("Inicio")
                }
              >
                ← Volver
              </button>

            </div>
          )}


          {view === "Consultar" && (
            <Consultar
              url={directUrl}
              setUrl={setDirectUrl}

              operador={
                nombreOperador
              }

              setOperador={
                setNombreOperador
              }

              extraerSolo={
                extraerSolo
              }

              extraerYGuardar={
                extraerYGuardar
              }
            />
          )}


          {view === "Búsqueda" && (
            <Busqueda
              form={searchForm}

              setForm={
                setSearchForm
              }

              submit={
                buscarOperador
              }
            />
          )}


          {view === "Filtros" && (
            <Filtros
              term={term}
              setTerm={setTerm}

              filterType={
                filterType
              }

              setFilterType={
                setFilterType
              }

              actividades={
                actividadesFiltradas
              }

              setTour={setTour}

              setView={setView}
            />
          )}


          {view === "Resultados" && (
            <Resultados
              tour={tour}

              apiResults={
                apiResults
              }

              extraerSolo={
                extraerSolo
              }

              setNombreOperador={
                setNombreOperador
              }

              setDirectUrl={
                setDirectUrl
              }

              setView={setView}
            />
          )}


          {view === "Historial" && (
            <Historial
              actividades={
                actividades
              }

              setTour={setTour}

              setView={setView}
            />
          )}


          {view === "Administrador" && isAdmin && (
            <AdminPage
              operadores={operadores}
              paises={paises}
              actividades={actividades}
              usuarios={usuarios}
              registros={registros}

              setView={setView}
              setTour={setTour}
              cargarActividades={cargarActividades}
              cargarOperadores={cargarOperadores}
              cargarPaises={cargarPaises}
              cargarUsuarios={cargarUsuarios}
              cargarRegistros={cargarRegistros}
              setSuccess={setSuccess}
              setError={setError}
            />
          )}

        </main>
      )}


      {view !== "Administrador" && (
        <Footer />
      )}

    </div>
  );
}


// ============================================================
// NAVBAR
// ============================================================

function NavBar({
  view,
  setView,
  onLogout,
  isAdmin,
}) {
  return (
    <nav className="main-nav">

      <div className="container-fluid nav-inner">

        <button
          className="brand"

          onClick={() =>
            setView("Inicio")
          }
        >

          <span className="brand-icon">
            ◈
          </span>


          <span>

            <strong>
              Tour Search
            </strong>

            <small>
              Plataforma de extracción
              de información
            </small>

          </span>

        </button>


        <div className="nav-links">

          {[...NAV, ...(isAdmin ? ["Administrador"] : [])].map((item) => (

            <button
              key={item}

              className={
                view === item
                  ? "active"
                  : ""
              }

              onClick={() =>
                setView(item)
              }
            >

              <span className="nav-icon">
                {navIcon(item)}
              </span>

              {item}

            </button>

          ))}

        </div>


        <div className="nav-session-actions">

          <div className="service">
            <i />
            Servicio activo
          </div>

          <button
            className="logout-button"
            onClick={onLogout}
          >
            Cerrar sesión
          </button>

        </div>

      </div>

    </nav>
  );
}


// ============================================================
// INICIO
// ============================================================

function Home({
  setView,
  isAdmin,

  directUrl,
  setDirectUrl,

  nombreOperador,
  setNombreOperador,

  extraerYGuardar,
}) {
  return (
    <>

      <section
        className="hero"

        style={{
          backgroundImage:
            `
            linear-gradient(
              90deg,
              rgba(5,14,24,.94),
              rgba(6,16,27,.45)
            ),
            url(${heroImage})
            `,
        }}
      >

        <div className="container-xl hero-inner">

          <span className="kicker">
            TOUR SEARCH
          </span>


          <h1>
            Descubre.
            <br />

            Extrae.
            <br />

            Organiza.
          </h1>


          <p className="hero-copy">
            Busca actividades publicadas
            por operadores turísticos,
            revisa su información y
            almacénala directamente en
            la plataforma.
          </p>


          <div className="hero-quick-form">

            <TextInput
              placeholder="URL de la actividad"

              value={directUrl}

              onChange={(e) =>
                setDirectUrl(
                  e.currentTarget.value
                )
              }

              size="md"
            />


            <TextInput
              placeholder="Nombre del Tour Operador"

              value={
                nombreOperador
              }

              onChange={(e) =>
                setNombreOperador(
                  e.currentTarget.value
                )
              }

              size="md"
            />


            <Button
              size="md"

              onClick={() =>
                extraerYGuardar(
                  directUrl,
                  nombreOperador
                )
              }
            >
              Extraer y guardar
            </Button>

          </div>

        </div>

      </section>


      <section className="home-actions">

        <div className="container-xl">

          <div className="section-heading-modern">

            <span>
              ⚡
            </span>

            <h2>
              Acciones rápidas
            </h2>

          </div>


          <div className="quick-grid">

            <QuickCard
              icon="⌕"

              title="Nueva consulta"

              description="Extrae una actividad directamente desde su URL."

              button="Consultar"

              className="blue"

              onClick={() =>
                setView("Consultar")
              }
            />


            <QuickCard
              icon="⌕"

              title="Búsqueda avanzada"

              description="Busca actividades relacionadas dentro del sitio de un operador."

              button="Buscar"

              className="green"

              onClick={() =>
                setView("Búsqueda")
              }
            />


            <QuickCard
              icon="▽"

              title="Filtros"

              description="Encuentra actividades registradas por nombre u operador."

              button="Configurar"

              className="orange"

              onClick={() =>
                setView("Filtros")
              }
            />


            <QuickCard
              icon="◷"

              title="Historial"

              description="Revisa las actividades almacenadas en la plataforma."

              button="Ver historial"

              className="purple"

              onClick={() =>
                setView("Historial")
              }
            />


            {isAdmin && (
              <QuickCard
                icon="♢"

                title="Administrador"

                description="Administra contenido, operadores, actividades y países."

                button="Ir al panel"

                className="pink"

                onClick={() =>
                  setView(
                    "Administrador"
                  )
                }
              />
            )}

          </div>

        </div>

      </section>

    </>
  );
}


// ============================================================
// QUICK CARD
// ============================================================

function QuickCard({
  icon,
  title,
  description,
  button,
  className,
  onClick,
}) {
  return (
    <article
      className={
        `quick-card ${className}`
      }
    >

      <div className="quick-card-top">

        <div className="quick-icon">
          {icon}
        </div>


        <div>

          <h3>
            {title}
          </h3>

          <p>
            {description}
          </p>

        </div>

      </div>


      <button
        onClick={onClick}
      >
        {button}
      </button>

    </article>
  );
}


// ============================================================
// CONSULTAR
// ============================================================

function Consultar({
  url,
  setUrl,

  operador,
  setOperador,

  extraerSolo,
  extraerYGuardar,
}) {
  return (
    <div className="container-xl">

      <PageTitle
        eyebrow="CONSULTAR"

        title="Extraer una actividad"

        text="Pega la URL de una actividad y revisa la información publicada."
      />


      <Paper
        className="modern-panel"
        p="xl"
      >

        <Stack gap="lg">

          <TextInput
            label="URL de la actividad"

            placeholder="https://..."

            value={url}

            onChange={(event) =>
              setUrl(
                event.currentTarget.value
              )
            }
          />


          <TextInput
            label="Tour Operador"

            placeholder="Ej: Let's Walk Medellín"

            value={operador}

            onChange={(event) =>
              setOperador(
                event.currentTarget.value
              )
            }
          />


          <Group justify="flex-end">

            <Button
              variant="default"

              onClick={() =>
                extraerSolo(
                  url,
                  operador
                )
              }
            >
              Solo extraer
            </Button>


            <Button
              onClick={() =>
                extraerYGuardar(
                  url,
                  operador
                )
              }
            >
              Extraer y guardar
            </Button>

          </Group>

        </Stack>

      </Paper>

    </div>
  );
}


// ============================================================
// BÚSQUEDA
// ============================================================

function Busqueda({
  form,
  setForm,
  submit,
}) {
  function change(
    field,
    value
  ) {
    setForm({
      ...form,
      [field]: value,
    });
  }


  return (
    <div className="container-xl">

      <PageTitle
        eyebrow="BÚSQUEDA"

        title="Búsqueda avanzada"

        text="Busca actividades relacionadas directamente dentro del sitio web del Tour Operador."
      />


      <Paper
        className="modern-panel"
        p="xl"
      >

        <form onSubmit={submit}>

          <SimpleGrid
            cols={{
              base: 1,
              md: 2,
            }}
          >

            <TextInput
              label="Sitio web del operador"

              placeholder="https://operador.com"

              value={
                form.url_operador
              }

              onChange={(e) =>
                change(
                  "url_operador",
                  e.currentTarget.value
                )
              }

              required
            />


            <TextInput
              label="Nombre del operador"

              placeholder="Tour Operador"

              value={
                form.nombre_operador
              }

              onChange={(e) =>
                change(
                  "nombre_operador",
                  e.currentTarget.value
                )
              }
            />


            <TextInput
              label="¿Qué actividad buscas?"

              placeholder="Ej: avistamiento de aves"

              value={
                form.pedido
              }

              onChange={(e) =>
                change(
                  "pedido",
                  e.currentTarget.value
                )
              }

              required
            />


            <NumberInput
              label="Máximo de páginas"

              value={
                form.max_paginas
              }

              onChange={(value) =>
                change(
                  "max_paginas",
                  value
                )
              }

              min={1}
              max={100}
            />


            <NumberInput
              label="Resultados"

              value={
                form.limite
              }

              onChange={(value) =>
                change(
                  "limite",
                  value
                )
              }

              min={1}
              max={50}
            />


            <NumberInput
              label="Puntaje mínimo"

              value={
                form.puntaje_minimo
              }

              onChange={(value) =>
                change(
                  "puntaje_minimo",
                  value
                )
              }

              min={0}
              max={100}
            />

          </SimpleGrid>


          <Group
            justify="flex-end"
            mt="xl"
          >

            <Button type="submit">
              Buscar actividades
            </Button>

          </Group>

        </form>

      </Paper>

    </div>
  );
}


// ============================================================
// FILTROS
// ============================================================

function Filtros({
  term,
  setTerm,

  filterType,
  setFilterType,

  actividades,

  setTour,
  setView,
}) {
  return (
    <div className="container-xl">

      <PageTitle
        eyebrow="FILTROS"

        title="Filtrar actividades"

        text="Busca rápidamente actividades almacenadas en la plataforma."
      />


      <Paper
        className="modern-panel"
        p="lg"
        mb="xl"
      >

        <SimpleGrid
          cols={{
            base: 1,
            md: 2,
          }}
        >

          <TextInput
            label="Buscar"

            placeholder="Nombre de actividad u operador..."

            value={term}

            onChange={(e) =>
              setTerm(
                e.currentTarget.value
              )
            }
          />


          <Select
            label="Buscar por"

            value={filterType}

            onChange={(value) =>
              setFilterType(
                value ||
                "activity"
              )
            }

            data={[
              {
                value: "activity",
                label: "Actividad",
              },
              {
                value: "operator",
                label: "Tour Operador",
              },
            ]}
          />

        </SimpleGrid>

      </Paper>


      <ActivityCards
        actividades={actividades}

        openActivity={(item) => {
          setTour(
            actividadATour(item)
          );

          setView(
            "Resultados"
          );
        }}
      />

    </div>
  );
}


// ============================================================
// RESULTADOS
// ============================================================

function Resultados({
  tour,
  apiResults,

  extraerSolo,

  setNombreOperador,
  setDirectUrl,
  setView,
}) {
  return (
    <div className="container-xl">

      <PageTitle
        eyebrow="RESULTADOS"

        title="Información encontrada"

        text="Revisa los datos y consulta siempre la fuente original."
      />


      {apiResults.length > 0 &&
      !tour && (

        <div className="results-list">

          {apiResults.map(
            (item, index) => (

              <Card
                key={
                  item.url ||
                  index
                }

                className="result-card"

                padding="lg"
              >

                <Group
                  justify="space-between"
                  align="center"
                >

                  <div>

                    <Title order={3}>
                      {
                        item.titulo_encontrado ||
                        item.titulo ||
                        "Actividad encontrada"
                      }
                    </Title>


                    <Group
                      mt="xs"
                      gap="xs"
                    >

                      <Badge>
                        {
                          item.nivel ||
                          "coincidencia"
                        }
                      </Badge>


                      {item.puntaje != null && (

                        <Badge color="gray">
                          {item.puntaje} puntos
                        </Badge>

                      )}

                    </Group>

                  </div>


                  <Group>

                    <Button
                      variant="default"

                      onClick={() =>
                        extraerSolo(
                          item.url
                        )
                      }
                    >
                      Revisar
                    </Button>


                    <Button
                      onClick={() => {
                        setDirectUrl(
                          item.url
                        );

                        setNombreOperador(
                          item.nombre_operador ||
                          ""
                        );

                        setView(
                          "Consultar"
                        );
                      }}
                    >
                      Extraer
                    </Button>

                  </Group>

                </Group>

              </Card>

            )
          )}

        </div>

      )}


      {tour && (
        <TourDetail
          tour={tour}
        />
      )}


      {!tour &&
      apiResults.length === 0 && (

        <EmptyResults
          onConsultar={() =>
            setView("Consultar")
          }
        />

      )}

    </div>
  );
}


// ============================================================
// VACÍO
// ============================================================

function EmptyResults({
  onConsultar,
}) {
  return (
    <section className="empty-results-modern">

      <div className="empty-icon">
        ⌕
      </div>


      <h2>
        Todavía no hay resultados
      </h2>


      <p>
        Realiza una consulta o abre
        una ficha del historial.
      </p>


      {onConsultar && (

        <Button
          size="md"

          onClick={
            onConsultar
          }
        >
          Ir a Consultar
        </Button>

      )}

    </section>
  );
}


// ============================================================
// FUENTES / URLS
// ============================================================

function esUrlWeb(url) {
  return /^https?:\/\//i.test(
    String(url || "").trim()
  );
}

function esFuenteLocal(url) {
  return /^local:/i.test(
    String(url || "").trim()
  );
}

function etiquetaFuente(url) {
  if (esUrlWeb(url)) {
    return "Ver fuente original ↗";
  }

  if (esFuenteLocal(url)) {
    return "Documento importado localmente";
  }

  return "Fuente no disponible";
}


// ============================================================
// DETALLE
// ============================================================

function TourDetail({
  tour,
}) {
  const ubicacion =
    typeof tour.ubicacion ===
    "string"
      ? tour.ubicacion
      : [
          tour.ubicacion?.ciudad,
          tour.ubicacion?.region,
          tour.ubicacion?.pais,
        ]
          .filter(Boolean)
          .join(", ");


  const duracion =
    tour.duracion ||
    tour.duracion_original;


  const descripcion =
    tour.descripcion_original ||
    tour.descripcion ||
    tour.descripcion_corta;


  const fuente =
    tour.source_url ||
    tour.urlOrigen ||
    "";


  return (
    <article className="tour-detail-modern">

      <header>

        <div>

          <Badge mb="sm">

            {
              tour.nombre_operador ||
              tour.operadorTuristico
                ?.nombre ||
              "Tour Operador"
            }

          </Badge>


          <h2>
            {
              tour.nombre ||
              "Actividad"
            }
          </h2>

        </div>


        {fuente && (
          esUrlWeb(fuente) ? (

            <a
              href={fuente}
              target="_blank"
              rel="noreferrer"
            >
              {etiquetaFuente(fuente)}
            </a>

          ) : (

            <span
              title={
                esFuenteLocal(fuente)
                  ? fuente.replace(/^local:/i, "")
                  : fuente
              }
              style={{
                opacity: 0.75,
                fontSize: "0.9rem",
              }}
            >
              {etiquetaFuente(fuente)}
            </span>

          )
        )}

      </header>


      <div className="facts-modern">

        <Fact
          label="Ubicación"
          value={ubicacion}
        />

        <Fact
          label="Destino"
          value={tour.destino}
        />

        <Fact
          label="Duración"
          value={duracion}
        />

        <Fact
          label="Idiomas"

          value={
            tour.idiomas?.join(
              ", "
            )
          }
        />

        <Fact
          label="Edad mínima"

          value={
            tour.edad_minima ??
            tour.edadMinima
          }
        />

      </div>


      {descripcion && (

        <section className="tour-description">

          <h3>
            Descripción
          </h3>

          <p style={{ whiteSpace: "pre-line" }}>
            {descripcion}
          </p>

        </section>

      )}


      {tour.imagenes?.length > 0 && (

        <div className="tour-gallery-modern">

          {tour.imagenes
            .slice(0, 6)
            .map(
              (imagen, index) => (

                <img
                  key={index}

                  src={imagen}

                  alt={
                    `Actividad ${index + 1}`
                  }
                />

              )
            )}

        </div>

      )}


      <div className="detail-grid-modern">

        <Info
          title="Highlights"
          values={tour.highlights}
        />

        <Info
          title="Horarios"
          values={tour.horarios || tour.calendario?.horarios}
        />

        <Info
          title="Incluye"
          values={tour.incluye}
        />

        <Info
          title="No incluye"
          values={tour.no_incluye}
        />

        <Info
          title="Qué llevar"
          values={tour.que_llevar}
        />

        <Info
          title="No llevar"
          values={tour.no_llevar}
        />

        <Info
          title="Recomendaciones"
          values={
            tour.recomendaciones
          }
        />

        <Info
          title="Restricciones"
          values={
            tour.restricciones
          }
        />

      </div>


      {tour.itinerario?.length > 0 && (

        <section className="itinerary-modern">

          <h3>
            Itinerario
          </h3>


          {tour.itinerario.map(
            (paso, index) => {
              const esTexto =
                typeof paso === "string";

              const orden =
                esTexto
                  ? index + 1
                  : paso.orden ?? index + 1;

              const titulo =
                esTexto
                  ? null
                  : paso.titulo || null;

              const detalle =
                esTexto
                  ? paso
                  : paso.descripcion ||
                    paso.texto ||
                    "";

              return (
                <div
                  className="itinerary-step"
                  key={`${orden}-${index}`}
                >
                  <span>
                    {orden}
                  </span>

                  <div>
                    {titulo && (
                      <strong>
                        {titulo}
                      </strong>
                    )}

                    <p style={{ whiteSpace: "pre-line" }}>
                      {detalle}
                    </p>
                  </div>
                </div>
              );
            }
          )}

        </section>

      )}

    </article>
  );
}


// ============================================================
// FACT
// ============================================================

function Fact({
  label,
  value,
}) {
  return (
    <div>

      <span>
        {label}
      </span>

      <strong>
        {
          value ??
          "No publicado"
        }
      </strong>

    </div>
  );
}


// ============================================================
// INFO
// ============================================================

function Info({
  title,
  values,
}) {
  if (!values?.length) {
    return null;
  }

  return (
    <section>

      <h3>
        {title}
      </h3>

      <ul>

        {values.map(
          (item, index) => (

            <li key={index}>
              {item}
            </li>

          )
        )}

      </ul>

    </section>
  );
}


// ============================================================
// HISTORIAL
// ============================================================

function Historial({
  actividades,
  setTour,
  setView,
}) {
  return (
    <div className="container-xl">

      <PageTitle
        eyebrow="HISTORIAL"

        title="Actividades registradas"

        text="Consulta las actividades almacenadas actualmente en PostgreSQL."
      />


      <ActivityCards
        actividades={
          actividades
        }

        openActivity={(item) => {
          setTour(
            actividadATour(item)
          );

          setView(
            "Resultados"
          );
        }}
      />

    </div>
  );
}


// ============================================================
// TARJETAS ACTIVIDADES
// ============================================================

function ActivityCards({
  actividades,
  openActivity,
}) {
  if (!actividades.length) {
    return (
      <EmptyResults />
    );
  }


  return (
    <SimpleGrid
      cols={{
        base: 1,
        sm: 2,
        lg: 3,
      }}
    >

      {actividades.map(
        (actividad) => (

          <Card
            key={actividad.id}

            className="activity-card"

            padding="lg"
          >

            <Group
              justify="space-between"
              mb="xs"
            >

              <Badge variant="light">
                ID {actividad.id}
              </Badge>


              <Badge
                color={
                  actividad.activo
                    ? "green"
                    : "gray"
                }
              >
                {
                  actividad.activo
                    ? "ACTIVA"
                    : "INACTIVA"
                }
              </Badge>

            </Group>


            <Title order={3}>
              {actividad.nombre}
            </Title>


            <Text
              size="sm"
              c="dimmed"
              mt="xs"
            >
              {
                actividad
                  .operadorTuristico
                  ?.nombre ||
                "Operador"
              }
            </Text>


            <Divider my="md" />


            <Text size="sm">
              📍{" "}
              {
                actividad.ubicacion ||
                "Sin ubicación"
              }
            </Text>


            <Text
              size="sm"
              mt="xs"
            >
              ◷{" "}
              {
                actividad.duracion ||
                "Sin duración"
              }
            </Text>


            <Button
              fullWidth
              variant="light"
              mt="lg"

              onClick={() =>
                openActivity(
                  actividad
                )
              }
            >
              Abrir ficha
            </Button>

          </Card>

        )
      )}

    </SimpleGrid>
  );
}


// ============================================================
// ADMINISTRADOR
// ============================================================

function AdminPage({
  operadores,
  paises,
  actividades,
  usuarios,
  registros,
  setView,
  setTour,
  cargarActividades,
  cargarOperadores,
  cargarPaises,
  cargarUsuarios,
  cargarRegistros,
  setSuccess,
  setError,
}) {
  const [adminSection, setAdminSection] =
    useState("dashboard");


  const actividadesActivas =
    actividades.filter(
      (item) => item.activo
    ).length;


  const recientes =
    [...actividades]
      .sort((a, b) => {
        const fechaA =
          new Date(
            a.fechaModificacion ||
            a.fechaCreacion ||
            0
          );

        const fechaB =
          new Date(
            b.fechaModificacion ||
            b.fechaCreacion ||
            0
          );

        return fechaB - fechaA;
      })
      .slice(0, 5);


  function renderAdminContent() {
    switch (
      adminSection
    ) {
      case "actividades":

        return (
          <AdminActivities
            actividades={actividades}
            setView={setView}
            setTour={setTour}
            cargarActividades={cargarActividades}
            setSuccess={setSuccess}
            setError={setError}
          />
        );


      case "operadores":

        return (
          <AdminOperators
            operadores={operadores}
            paises={paises}
            cargarOperadores={cargarOperadores}
            setSuccess={setSuccess}
            setError={setError}
          />
        );


      case "paises":

        return (
          <AdminCountries
            paises={paises}
            cargarPaises={cargarPaises}
            setSuccess={setSuccess}
            setError={setError}
          />
        );


      case "sitio":

        return (
          <AdminSite />
        );


      case "usuarios":

        return (
          <AdminUsers
            usuarios={usuarios}
            cargarUsuarios={cargarUsuarios}
            setSuccess={setSuccess}
            setError={setError}
          />
        );


      case "configuracion":

        return (
          <AdminPlaceholder
            title="Configuración"

            text="Configuración general de Tour Search."
          />
        );


      case "registros":

        return (
          <AdminRecords
            registros={registros}
            cargarRegistros={cargarRegistros}
            setSuccess={setSuccess}
            setError={setError}
          />
        );


      case "respaldos":

        return (
          <AdminPlaceholder
            title="Respaldos"

            text="Aquí gestionaremos copias de seguridad de PostgreSQL."
          />
        );


      default:

        return (
          <AdminDashboard
            actividades={
              actividades
            }

            operadores={
              operadores
            }

            paises={paises}

            actividadesActivas={
              actividadesActivas
            }

            recientes={
              recientes
            }

            setAdminSection={
              setAdminSection
            }
          />
        );
    }
  }


  return (
    <div className="admin-page">

      <aside className="admin-sidebar">

        <div className="admin-sidebar-title">

          <div className="admin-shield">
            ◇
          </div>


          <div>

            <strong>
              Panel de administración
            </strong>

            <small>
              Gestión de Tour Search
            </small>

          </div>

        </div>


        <nav className="admin-menu">

          <AdminMenuItem
            icon="▦"
            label="Dashboard"

            active={
              adminSection ===
              "dashboard"
            }

            onClick={() =>
              setAdminSection(
                "dashboard"
              )
            }
          />


          <AdminMenuItem
            icon="☷"
            label="Actividades"

            active={
              adminSection ===
              "actividades"
            }

            onClick={() =>
              setAdminSection(
                "actividades"
              )
            }
          />


          <AdminMenuItem
            icon="♙"
            label="Operadores"

            active={
              adminSection ===
              "operadores"
            }

            onClick={() =>
              setAdminSection(
                "operadores"
              )
            }
          />


          <AdminMenuItem
            icon="◎"
            label="Países"

            active={
              adminSection ===
              "paises"
            }

            onClick={() =>
              setAdminSection(
                "paises"
              )
            }
          />


          <AdminMenuItem
            icon="▣"
            label="Sitio"

            active={
              adminSection ===
              "sitio"
            }

            onClick={() =>
              setAdminSection(
                "sitio"
              )
            }
          />


          <div className="admin-menu-separator" />


          <AdminMenuItem
            icon="♙"
            label="Usuarios"

            active={
              adminSection ===
              "usuarios"
            }

            onClick={() =>
              setAdminSection(
                "usuarios"
              )
            }
          />


          <AdminMenuItem
            icon="⚙"
            label="Configuración"

            active={
              adminSection ===
              "configuracion"
            }

            onClick={() =>
              setAdminSection(
                "configuracion"
              )
            }
          />


          <AdminMenuItem
            icon="▤"
            label="Registros"

            active={
              adminSection ===
              "registros"
            }

            onClick={() =>
              setAdminSection(
                "registros"
              )
            }
          />


          <AdminMenuItem
            icon="▣"
            label="Respaldos"

            active={
              adminSection ===
              "respaldos"
            }

            onClick={() =>
              setAdminSection(
                "respaldos"
              )
            }
          />

        </nav>


        <div className="admin-system-card">

          <h4>
            Información del sistema
          </h4>


          <div>
            <span>
              Versión
            </span>

            <strong>
              v1.0.0
            </strong>
          </div>


          <div>
            <span>
              Base de datos
            </span>

            <strong>
              PostgreSQL
            </strong>
          </div>


          <div>

            <span>
              Estado
            </span>

            <Badge
              color="green"
              size="sm"
            >
              Conectado
            </Badge>

          </div>


          <div>

            <span>
              Operadores
            </span>

            <strong>
              {operadores.length}
            </strong>

          </div>


          <button
            className="admin-backup-button"

            onClick={() =>
              setAdminSection(
                "respaldos"
              )
            }
          >
            ◉ Realizar respaldo
          </button>

        </div>

      </aside>


      <section className="admin-content">

        {renderAdminContent()}


        <div className="admin-close-row">

          <Button
            variant="default"

            onClick={() =>
              setView("Inicio")
            }
          >
            Cerrar administrador
          </Button>

        </div>

      </section>

    </div>
  );
}


// ============================================================
// ADMIN MENU ITEM
// ============================================================

function AdminMenuItem({
  icon,
  label,
  active,
  onClick,
}) {
  return (
    <button
      className={
        `admin-menu-item ${
          active
            ? "active"
            : ""
        }`
      }

      onClick={onClick}
    >

      <span>
        {icon}
      </span>

      {label}

    </button>
  );
}


// ============================================================
// ADMIN DASHBOARD
// ============================================================

function AdminDashboard({
  actividades,
  operadores,
  paises,

  actividadesActivas,
  recientes,

  setAdminSection,
}) {
  return (
    <>

      <div className="admin-heading">

        <div>

          <h1>
            Dashboard
          </h1>

          <p>
            Resumen general de la plataforma
          </p>

        </div>


        <button className="admin-date-button">
          ▣ Rango de fechas
        </button>

      </div>


      <div className="admin-stats-grid">

        <AdminMetric
          icon="▣"

          value={
            actividades.length
          }

          label="Actividades"

          detail={
            `${actividadesActivas} activas`
          }

          color="purple"
        />


        <AdminMetric
          icon="♙"

          value={
            operadores.length
          }

          label="Operadores"

          detail="Registrados"

          color="blue"
        />


        <AdminMetric
          icon="◎"

          value={
            paises.length
          }

          label="Países"

          detail="Disponibles"

          color="green"
        />


        <AdminMetric
          icon="◉"

          value={
            actividades.length
          }

          label="Registros"

          detail="En PostgreSQL"

          color="orange"
        />

      </div>


      <div className="admin-dashboard-grid">

        <section className="admin-dashboard-card">

          <div className="admin-card-title">
            Actividad reciente
          </div>


          <div className="admin-table">

            <div className="admin-table-head">

              <span>
                Actividad
              </span>

              <span>
                Operador
              </span>

              <span>
                Estado
              </span>

            </div>


            {recientes.length > 0 ? (

              recientes.map(
                (item) => (

                  <div
                    className="admin-table-row"

                    key={item.id}
                  >

                    <strong>
                      {item.nombre}
                    </strong>


                    <span>
                      {
                        item
                          .operadorTuristico
                          ?.nombre ||
                        "Sin operador"
                      }
                    </span>


                    <Badge
                      color={
                        item.activo
                          ? "green"
                          : "gray"
                      }
                    >
                      {
                        item.activo
                          ? "Activa"
                          : "Inactiva"
                      }
                    </Badge>

                  </div>

                )
              )

            ) : (

              <div className="admin-empty">
                No hay actividades disponibles.
              </div>

            )}

          </div>


          <button
            className="admin-text-link"

            onClick={() =>
              setAdminSection(
                "actividades"
              )
            }
          >
            Ver todas las actividades →
          </button>

        </section>


        <section className="admin-dashboard-card">

          <div className="admin-card-title">
            Actividad de la plataforma
          </div>

          <AdminChart />

        </section>

      </div>


      <h3 className="admin-actions-title">
        Acciones rápidas
      </h3>


      <div className="admin-quick-grid">

        <AdminQuickAction
          icon="+"

          title="Nueva actividad"

          subtitle="Extraer y registrar"

          color="purple"

          onClick={() =>
            setAdminSection(
              "actividades"
            )
          }
        />


        <AdminQuickAction
          icon="♙"

          title="Nuevo operador"

          subtitle="Registrar operador turístico"

          color="blue"

          onClick={() =>
            setAdminSection(
              "operadores"
            )
          }
        />


        <AdminQuickAction
          icon="◎"

          title="Nuevo país"

          subtitle="Agregar país"

          color="green"

          onClick={() =>
            setAdminSection(
              "paises"
            )
          }
        />


        <AdminQuickAction
          icon="⚙"

          title="Configurar sitio"

          subtitle="Editar información visible"

          color="orange"

          onClick={() =>
            setAdminSection(
              "sitio"
            )
          }
        />


        <AdminQuickAction
          icon="▣"

          title="Respaldos"

          subtitle="Copias de seguridad"

          color="pink"

          onClick={() =>
            setAdminSection(
              "respaldos"
            )
          }
        />

      </div>

    </>
  );
}


// ============================================================
// ADMIN METRIC
// ============================================================

function AdminMetric({
  icon,
  value,
  label,
  detail,
  color,
}) {
  return (
    <article className="admin-metric">

      <div
        className={
          `admin-metric-icon ${color}`
        }
      >
        {icon}
      </div>


      <div>

        <strong>
          {value}
        </strong>

        <span>
          {label}
        </span>

        <small>
          {detail}
        </small>

      </div>

    </article>
  );
}


// ============================================================
// ADMIN QUICK
// ============================================================

function AdminQuickAction({
  icon,
  title,
  subtitle,
  color,
  onClick,
}) {
  return (
    <button
      className="admin-quick-action"

      onClick={onClick}
    >

      <div
        className={
          `admin-quick-icon ${color}`
        }
      >
        {icon}
      </div>


      <div>

        <strong>
          {title}
        </strong>

        <small>
          {subtitle}
        </small>

      </div>

    </button>
  );
}


// ============================================================
// GRÁFICO
// ============================================================

function AdminChart() {
  return (
    <div className="admin-chart">

      <svg
        viewBox="0 0 600 260"

        preserveAspectRatio="none"
      >

        <defs>

          <linearGradient
            id="chartGradient"

            x1="0"
            y1="0"

            x2="0"
            y2="1"
          >

            <stop
              offset="0%"

              stopColor="#934cff"

              stopOpacity=".35"
            />

            <stop
              offset="100%"

              stopColor="#934cff"

              stopOpacity="0"
            />

          </linearGradient>

        </defs>


        <line
          x1="30"
          y1="220"

          x2="570"
          y2="220"

          stroke="#29405a"
        />


        <line
          x1="30"
          y1="160"

          x2="570"
          y2="160"

          stroke="#1d3248"
        />


        <line
          x1="30"
          y1="100"

          x2="570"
          y2="100"

          stroke="#1d3248"
        />


        <path
          d="
            M30,175
            L120,145
            L210,85
            L300,115
            L390,70
            L480,112
            L570,112
            L570,220
            L30,220
            Z
          "

          fill="url(#chartGradient)"
        />


        <polyline
          points="
            30,175
            120,145
            210,85
            300,115
            390,70
            480,112
            570,112
          "

          fill="none"

          stroke="#934cff"

          strokeWidth="4"
        />


        {[
          [30, 175],
          [120, 145],
          [210, 85],
          [300, 115],
          [390, 70],
          [480, 112],
          [570, 112],
        ].map(
          ([x, y], index) => (

            <circle
              key={index}

              cx={x}
              cy={y}

              r="6"

              fill="#a65cff"
            />

          )
        )}

      </svg>


      <div className="admin-chart-labels">

        <span>19 Ago</span>
        <span>20 Ago</span>
        <span>21 Ago</span>
        <span>22 Ago</span>
        <span>23 Ago</span>
        <span>24 Ago</span>
        <span>25 Ago</span>

      </div>

    </div>
  );
}


// ============================================================
// ADMIN ACTIVIDADES
// ============================================================

function AdminActivities({
  actividades,
  setView,
  setTour,
  cargarActividades,
  setSuccess,
  setError,
}) {
  const [editando, setEditando] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [eliminandoId, setEliminandoId] = useState(null);
  const [desactivandoId, setDesactivandoId] = useState(null);
  const [busqueda, setBusqueda] = useState("");

  const [form, setForm] = useState({
    nombre: "",
    descripcion: "",
    ubicacion: "",
    duracion: "",
  });

  const actividadesVisibles = useMemo(() => {
    const q = busqueda.trim().toLocaleLowerCase("es");
    if (!q) return actividades;

    return actividades.filter((item) => {
      const campos = [
        item.nombre,
        item.operadorTuristico?.nombre,
        item.ubicacion,
        item.destino,
        item.duracion,
        item.id != null ? String(item.id) : "",
      ];

      return campos.some((valor) =>
        String(valor || "")
          .toLocaleLowerCase("es")
          .includes(q)
      );
    });
  }, [actividades, busqueda]);

  function abrirFicha(item) {
    setTour(actividadATour(item));
    setView("Resultados");
  }

  function abrirEdicion(item) {
    setEditando(item);
    setForm({
      nombre: item.nombre || "",
      descripcion: item.descripcion || "",
      ubicacion: item.ubicacion || "",
      duracion: item.duracion || "",
    });
  }

  async function guardarEdicion() {
    if (!editando) return;

    if (!form.nombre.trim()) {
      setError("El nombre de la actividad es obligatorio.");
      return;
    }

    setGuardando(true);
    setError("");
    setSuccess("");

    try {
      const token = sessionStorage.getItem("tourSearchToken");

      const response = await fetch(
        `${BACKEND_API}/actividades/${editando.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            ...(token
              ? { Authorization: `Bearer ${token}` }
              : {}),
          },
          body: JSON.stringify({
            ...editando,
            nombre: form.nombre.trim(),
            descripcion: form.descripcion,
            ubicacion: form.ubicacion.trim(),
            duracion: form.duracion.trim(),
          }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error ||
          data.message ||
          "No fue posible actualizar la actividad."
        );
      }

      setEditando(null);
      await cargarActividades();
      setSuccess("Actividad actualizada correctamente.");
    } catch (e) {
      setError(e.message);
    } finally {
      setGuardando(false);
    }
  }

  async function desactivarActividad(item) {
    const confirmar = window.confirm(
      `¿Desactivar la actividad "${item.nombre}"?\n\nLa actividad se conservará en PostgreSQL, pero dejará de aparecer entre las actividades activas.`
    );

    if (!confirmar) return;

    setDesactivandoId(item.id);
    setError("");
    setSuccess("");

    try {
      const token = sessionStorage.getItem("tourSearchToken");

      const response = await fetch(
        `${BACKEND_API}/actividades/${item.id}/desactivar`,
        {
          method: "PATCH",
          headers: token
            ? { Authorization: `Bearer ${token}` }
            : {},
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data.error ||
          data.message ||
          `No fue posible desactivar la actividad (HTTP ${response.status}).`
        );
      }

      await cargarActividades();
      setSuccess(`Actividad "${item.nombre}" desactivada correctamente.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setDesactivandoId(null);
    }
  }

  async function eliminarActividad(item) {
    const confirmar = window.confirm(
      `¿Eliminar definitivamente la actividad "${item.nombre}"?\n\nEsta acción la borrará de PostgreSQL y no se puede deshacer.`
    );

    if (!confirmar) return;

    setEliminandoId(item.id);
    setError("");
    setSuccess("");

    try {
      const token = sessionStorage.getItem("tourSearchToken");

      const response = await fetch(
        `${BACKEND_API}/actividades/${item.id}`,
        {
          method: "DELETE",
          headers: token
            ? { Authorization: `Bearer ${token}` }
            : {},
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data.error ||
          data.message ||
          `No fue posible eliminar la actividad (HTTP ${response.status}).`
        );
      }

      await cargarActividades();
      setSuccess(`Actividad "${item.nombre}" eliminada correctamente.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setEliminandoId(null);
    }
  }

  return (
    <>
      <div className="admin-heading">
        <div>
          <h1>Actividades</h1>
          <p>Gestión de actividades registradas.</p>
        </div>

        <Button onClick={() => setView("Consultar")}>
          + Nueva actividad
        </Button>
      </div>

      <Paper className="admin-dashboard-card" p="lg" mb="lg">
        <TextInput
          label="Buscar actividad"
          placeholder="Nombre, operador, ubicación, destino o ID..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.currentTarget.value)}
        />
        <Text size="xs" c="dimmed" mt="xs">
          Mostrando {actividadesVisibles.length} de {actividades.length} actividades.
        </Text>
      </Paper>

      <div className="admin-dashboard-card">
        {actividadesVisibles.length > 0 ? (
          actividadesVisibles.map((item) => (
            <div className="admin-activity-row" key={item.id}>
              <div>
                <button
                  type="button"
                  onClick={() => abrirFicha(item)}
                  style={{
                    background: "none",
                    border: 0,
                    padding: 0,
                    color: "inherit",
                    cursor: "pointer",
                    textAlign: "left",
                    font: "inherit",
                  }}
                  title="Abrir ficha de la actividad"
                >
                  <strong>{item.nombre}</strong>
                </button>
                <small>
                  {item.operadorTuristico?.nombre || "Sin operador"}
                  {item.destino ? ` · ${item.destino}` : ""}
                </small>
              </div>

              <div className="admin-row-actions">
                <Button
                  component="div"
                  size="xs"
                  color={item.activo ? "green" : "gray"}
                  variant="light"
                  style={{ pointerEvents: "none", minWidth: "82px" }}
                >
                  {item.activo ? "ACTIVA" : "INACTIVA"}
                </Button>

                <Button
                  size="xs"
                  variant="subtle"
                  onClick={() => abrirFicha(item)}
                  disabled={eliminandoId === item.id}
                >
                  Abrir ficha
                </Button>

                <Button
                  size="xs"
                  variant="light"
                  onClick={() => abrirEdicion(item)}
                  disabled={eliminandoId === item.id}
                >
                  Editar
                </Button>

                <Button
                  size="xs"
                  color="yellow"
                  variant="light"
                  loading={desactivandoId === item.id}
                  disabled={eliminandoId === item.id}
                  onClick={() => desactivarActividad(item)}
                >
                  Desactivar
                </Button>

                <Button
                  size="xs"
                  color="red"
                  variant="light"
                  loading={eliminandoId === item.id}
                  disabled={desactivandoId === item.id}
                  onClick={() => eliminarActividad(item)}
                >
                  Eliminar
                </Button>
              </div>
            </div>
          ))
        ) : (
          <div className="admin-empty">
            {busqueda.trim()
              ? "No se encontraron actividades para esa búsqueda."
              : "No hay actividades registradas."}
          </div>
        )}
      </div>

      <Modal
        opened={Boolean(editando)}
        onClose={() => setEditando(null)}
        title="Editar actividad"
        centered
      >
        <Stack>
          <TextInput
            label="Nombre"
            required
            value={form.nombre}
            onChange={(e) =>
              setForm({ ...form, nombre: e.currentTarget.value })
            }
          />

          <Textarea
            label="Descripción"
            minRows={4}
            value={form.descripcion}
            onChange={(e) =>
              setForm({ ...form, descripcion: e.currentTarget.value })
            }
          />

          <TextInput
            label="Ubicación"
            value={form.ubicacion}
            onChange={(e) =>
              setForm({ ...form, ubicacion: e.currentTarget.value })
            }
          />

          <TextInput
            label="Duración"
            value={form.duracion}
            onChange={(e) =>
              setForm({ ...form, duracion: e.currentTarget.value })
            }
          />

          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => setEditando(null)}
              disabled={guardando}
            >
              Cancelar
            </Button>

            <Button
              onClick={guardarEdicion}
              loading={guardando}
              disabled={!form.nombre.trim()}
            >
              Guardar cambios
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

// ============================================================
// ADMIN OPERADORES
// ============================================================

function AdminOperators({
  operadores,
  paises,
  cargarOperadores,
  setSuccess,
  setError,
}) {
  const [modalAbierto, setModalAbierto] = useState(false);
  const [operadorEditando, setOperadorEditando] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [cambiandoEstadoId, setCambiandoEstadoId] = useState(null);
  const [busqueda, setBusqueda] = useState("");

  const [form, setForm] = useState({
    paisId: "",
    nombre: "",
    sitioWeb: "",
    estado: "ACTIVO",
  });

  const operadoresVisibles = useMemo(() => {
    const q = busqueda.trim().toLocaleLowerCase("es");
    if (!q) return operadores;

    return operadores.filter((item) => {
      const campos = [
        item.nombre,
        item.pais?.nombre,
        item.pais?.codigoIso,
        item.sitioWeb,
        item.estado,
        item.id != null ? String(item.id) : "",
      ];

      return campos.some((valor) =>
        String(valor || "")
          .toLocaleLowerCase("es")
          .includes(q)
      );
    });
  }, [operadores, busqueda]);

  function limpiarFormulario() {
    setOperadorEditando(null);
    setForm({ paisId: "", nombre: "", sitioWeb: "", estado: "ACTIVO" });
  }

  function abrirNuevoOperador() {
    limpiarFormulario();
    setModalAbierto(true);
  }

  function abrirEditarOperador(item) {
    setOperadorEditando(item);
    setForm({
      paisId: item.pais?.id != null ? String(item.pais.id) : "",
      nombre: item.nombre || "",
      sitioWeb: item.sitioWeb || "",
      estado: item.estado || "ACTIVO",
    });
    setModalAbierto(true);
  }

  function cerrarModal() {
    if (guardando) return;
    setModalAbierto(false);
    limpiarFormulario();
  }

  function actualizarCampo(campo, valor) {
    setForm((actual) => ({ ...actual, [campo]: valor }));
  }

  async function guardarOperador() {
    if (!form.paisId) {
      setError("Debes seleccionar un país.");
      return;
    }
    if (!form.nombre.trim()) {
      setError("El nombre del operador es obligatorio.");
      return;
    }

    setError("");
    setSuccess("");
    setGuardando(true);

    try {
      const token = sessionStorage.getItem("tourSearchToken");
      const esEdicion = Boolean(operadorEditando?.id);
      const url = esEdicion
        ? `${BACKEND_API}/operadores/${operadorEditando.id}?paisId=${encodeURIComponent(form.paisId)}`
        : `${BACKEND_API}/operadores?paisId=${encodeURIComponent(form.paisId)}`;

      const response = await fetch(url, {
        method: esEdicion ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          nombre: form.nombre.trim(),
          sitioWeb: form.sitioWeb.trim() || null,
          estado: form.estado || "ACTIVO",
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          data.message || data.error || "No fue posible guardar el operador."
        );
      }

      await cargarOperadores();
      setSuccess(
        esEdicion
          ? "Operador actualizado correctamente."
          : "Operador creado correctamente."
      );
      setModalAbierto(false);
      limpiarFormulario();
    } catch (e) {
      setError(e.message || "No fue posible guardar el operador.");
    } finally {
      setGuardando(false);
    }
  }

  async function cambiarEstadoOperador(item) {
    const estadoActual = String(item.estado || "ACTIVO").toUpperCase();
    const nuevoEstado = estadoActual === "ACTIVO" ? "INACTIVO" : "ACTIVO";
    const accion = nuevoEstado === "ACTIVO" ? "activar" : "desactivar";

    if (!window.confirm(`¿Seguro que deseas ${accion} el operador "${item.nombre}"?`)) {
      return;
    }

    setError("");
    setSuccess("");
    setCambiandoEstadoId(item.id);

    try {
      const token = sessionStorage.getItem("tourSearchToken");
      const response = await fetch(
        `${BACKEND_API}/operadores/${item.id}/estado?estado=${nuevoEstado}`,
        {
          method: "PATCH",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          data.message || data.error || "No fue posible cambiar el estado del operador."
        );
      }

      await cargarOperadores();
      setSuccess(
        nuevoEstado === "ACTIVO"
          ? "Operador activado correctamente."
          : "Operador desactivado correctamente."
      );
    } catch (e) {
      setError(e.message || "No fue posible cambiar el estado del operador.");
    } finally {
      setCambiandoEstadoId(null);
    }
  }

  const opcionesPaises = paises.map((pais) => ({
    value: String(pais.id),
    label: pais.codigoIso ? `${pais.nombre} (${pais.codigoIso})` : pais.nombre,
  }));

  return (
    <>
      <div className="admin-heading">
        <div>
          <h1>Operadores</h1>
          <p>Gestión de Tour Operadores.</p>
        </div>
        <Button onClick={abrirNuevoOperador}>+ Nuevo operador</Button>
      </div>

      <Paper className="admin-dashboard-card" p="lg" mb="lg">
        <TextInput
          label="Buscar operador"
          placeholder="Nombre, país, código ISO, sitio web o ID..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.currentTarget.value)}
        />
        <Text size="xs" c="dimmed" mt="xs">
          Mostrando {operadoresVisibles.length} de {operadores.length} operadores.
        </Text>
      </Paper>

      <div className="admin-dashboard-card">
        {operadoresVisibles.length > 0 ? (
          operadoresVisibles.map((item) => {
            const activo = String(item.estado || "ACTIVO").toUpperCase() === "ACTIVO";
            return (
              <div className="admin-activity-row" key={item.id}>
                <div>
                  <strong>{item.nombre}</strong>
                  <small>
                    {item.pais?.nombre || "Sin país"}
                    {item.sitioWeb ? ` · ${item.sitioWeb}` : ""}
                  </small>
                </div>

                <div className="admin-row-actions">
                  <Button
                    component="div"
                    size="xs"
                    color={activo ? "green" : "gray"}
                    variant="light"
                    style={{ pointerEvents: "none", minWidth: "82px" }}
                  >
                    {activo ? "ACTIVO" : "INACTIVO"}
                  </Button>

                  <Button size="xs" variant="light" onClick={() => abrirEditarOperador(item)}>
                    Editar
                  </Button>

                  {esUrlWeb(item.sitioWeb) && (
                    <Button
                      component="a"
                      href={item.sitioWeb}
                      target="_blank"
                      rel="noreferrer"
                      size="xs"
                      variant="subtle"
                    >
                      Abrir sitio
                    </Button>
                  )}

                  <Button
                    size="xs"
                    color={activo ? "orange" : "green"}
                    variant="light"
                    loading={cambiandoEstadoId === item.id}
                    disabled={cambiandoEstadoId != null}
                    onClick={() => cambiarEstadoOperador(item)}
                  >
                    {activo ? "Desactivar" : "Activar"}
                  </Button>
                </div>
              </div>
            );
          })
        ) : (
          <div className="admin-empty">
            {busqueda.trim()
              ? "No se encontraron operadores para esa búsqueda."
              : "No hay operadores registrados."}
          </div>
        )}
      </div>

      <Modal
        opened={modalAbierto}
        onClose={cerrarModal}
        title={operadorEditando ? "Editar operador" : "Nuevo operador"}
        centered
      >
        <Stack>
          <Select
            label="País"
            placeholder="Selecciona un país"
            data={opcionesPaises}
            value={form.paisId}
            onChange={(value) => actualizarCampo("paisId", value || "")}
            searchable
            required
          />

          <TextInput
            label="Nombre"
            placeholder="Nombre del Tour Operador"
            value={form.nombre}
            onChange={(e) => actualizarCampo("nombre", e.currentTarget.value)}
            required
          />

          <TextInput
            label="Página web (opcional)"
            placeholder="https://..."
            value={form.sitioWeb}
            onChange={(e) => actualizarCampo("sitioWeb", e.currentTarget.value)}
          />

          <Select
            label="Estado"
            data={[
              { value: "ACTIVO", label: "ACTIVO" },
              { value: "INACTIVO", label: "INACTIVO" },
            ]}
            value={form.estado}
            onChange={(value) => actualizarCampo("estado", value || "ACTIVO")}
          />

          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={cerrarModal} disabled={guardando}>
              Cancelar
            </Button>
            <Button onClick={guardarOperador} loading={guardando}>
              {operadorEditando ? "Guardar cambios" : "Crear operador"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

// ============================================================
// ADMIN PAÍSES
// ============================================================

function AdminCountries({
  paises,
  cargarPaises,
  setSuccess,
  setError,
}) {
  const [modalAbierto, setModalAbierto] = useState(false);
  const [paisEditando, setPaisEditando] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [cambiandoEstadoId, setCambiandoEstadoId] = useState(null);
  const [busqueda, setBusqueda] = useState("");

  const [form, setForm] = useState({
    nombre: "",
    codigoIso: "",
    estado: "ACTIVO",
  });

  const paisesVisibles = useMemo(() => {
    const q = busqueda.trim().toLocaleLowerCase("es");
    if (!q) return paises;

    return paises.filter((pais) => {
      const campos = [
        pais.nombre,
        pais.codigoIso,
        pais.estado,
        pais.id != null ? String(pais.id) : "",
      ];

      return campos.some((valor) =>
        String(valor || "")
          .toLocaleLowerCase("es")
          .includes(q)
      );
    });
  }, [paises, busqueda]);

  function limpiarFormulario() {
    setPaisEditando(null);
    setForm({ nombre: "", codigoIso: "", estado: "ACTIVO" });
  }

  function abrirNuevoPais() {
    limpiarFormulario();
    setModalAbierto(true);
  }

  function abrirEditarPais(pais) {
    setPaisEditando(pais);
    setForm({
      nombre: pais.nombre || "",
      codigoIso: pais.codigoIso || "",
      estado: pais.estado || "ACTIVO",
    });
    setModalAbierto(true);
  }

  function cerrarModal() {
    if (guardando) return;
    setModalAbierto(false);
    limpiarFormulario();
  }

  function actualizarCampo(campo, valor) {
    setForm((actual) => ({ ...actual, [campo]: valor }));
  }

  async function guardarPais() {
    if (!form.nombre.trim()) {
      setError("El nombre del país es obligatorio.");
      return;
    }

    setError("");
    setSuccess("");
    setGuardando(true);

    try {
      const token = sessionStorage.getItem("tourSearchToken");
      const esEdicion = Boolean(paisEditando?.id);

      const response = await fetch(
        esEdicion ? `${BACKEND_API}/paises/${paisEditando.id}` : `${BACKEND_API}/paises`,
        {
          method: esEdicion ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            nombre: form.nombre.trim(),
            codigoIso: form.codigoIso.trim()
              ? form.codigoIso.trim().toUpperCase()
              : null,
            estado: form.estado || "ACTIVO",
          }),
        }
      );

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          data.message || data.error || "No fue posible guardar el país."
        );
      }

      await cargarPaises();
      setSuccess(
        esEdicion ? "País actualizado correctamente." : "País creado correctamente."
      );
      setModalAbierto(false);
      limpiarFormulario();
    } catch (e) {
      setError(e.message || "No fue posible guardar el país.");
    } finally {
      setGuardando(false);
    }
  }

  async function cambiarEstadoPais(pais) {
    const activo = String(pais.estado || "ACTIVO").toUpperCase() === "ACTIVO";
    const nuevoEstado = activo ? "INACTIVO" : "ACTIVO";
    const accion = activo ? "desactivar" : "activar";

    if (!window.confirm(`¿Seguro que deseas ${accion} el país "${pais.nombre}"?`)) {
      return;
    }

    setError("");
    setSuccess("");
    setCambiandoEstadoId(pais.id);

    try {
      const token = sessionStorage.getItem("tourSearchToken");
      const response = await fetch(
        `${BACKEND_API}/paises/${pais.id}/estado?estado=${nuevoEstado}`,
        {
          method: "PATCH",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          data.message || data.error || "No fue posible cambiar el estado del país."
        );
      }

      await cargarPaises();
      setSuccess(
        nuevoEstado === "ACTIVO"
          ? `País "${pais.nombre}" activado correctamente.`
          : `País "${pais.nombre}" desactivado correctamente.`
      );
    } catch (e) {
      setError(e.message || "No fue posible cambiar el estado del país.");
    } finally {
      setCambiandoEstadoId(null);
    }
  }

  return (
    <>
      <div className="admin-heading">
        <div>
          <h1>Países</h1>
          <p>Gestión de países disponibles en la plataforma.</p>
        </div>
        <Button onClick={abrirNuevoPais}>+ Nuevo país</Button>
      </div>

      <Paper className="admin-dashboard-card" p="lg" mb="lg">
        <TextInput
          label="Buscar país"
          placeholder="Nombre, código ISO, estado o ID..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.currentTarget.value)}
        />
        <Text size="xs" c="dimmed" mt="xs">
          Mostrando {paisesVisibles.length} de {paises.length} países.
        </Text>
      </Paper>

      <div className="admin-dashboard-card">
        {paisesVisibles.length > 0 ? (
          paisesVisibles.map((pais) => {
            const activo = String(pais.estado || "ACTIVO").toUpperCase() === "ACTIVO";
            return (
              <div className="admin-activity-row" key={pais.id}>
                <div>
                  <strong>{pais.nombre}</strong>
                  <small>{pais.codigoIso || "Sin código ISO"}</small>
                </div>

                <div className="admin-row-actions">
                  <Button
                    component="div"
                    size="xs"
                    color={activo ? "green" : "gray"}
                    variant="light"
                    style={{ pointerEvents: "none", minWidth: "82px" }}
                  >
                    {activo ? "ACTIVO" : "INACTIVO"}
                  </Button>

                  <Button size="xs" variant="light" onClick={() => abrirEditarPais(pais)}>
                    Editar
                  </Button>

                  <Button
                    size="xs"
                    color={activo ? "orange" : "green"}
                    variant="light"
                    loading={cambiandoEstadoId === pais.id}
                    disabled={cambiandoEstadoId != null}
                    onClick={() => cambiarEstadoPais(pais)}
                  >
                    {activo ? "Desactivar" : "Activar"}
                  </Button>
                </div>
              </div>
            );
          })
        ) : (
          <div className="admin-empty">
            {busqueda.trim()
              ? "No se encontraron países para esa búsqueda."
              : "No hay países registrados."}
          </div>
        )}
      </div>

      <Modal
        opened={modalAbierto}
        onClose={cerrarModal}
        title={paisEditando ? "Editar país" : "Nuevo país"}
        centered
      >
        <Stack>
          <TextInput
            label="Nombre"
            placeholder="Ej: Chile"
            value={form.nombre}
            onChange={(e) => actualizarCampo("nombre", e.currentTarget.value)}
            required
          />

          <TextInput
            label="Código ISO"
            placeholder="Ej: CHL"
            value={form.codigoIso}
            maxLength={3}
            onChange={(e) => actualizarCampo("codigoIso", e.currentTarget.value.toUpperCase())}
          />

          <Select
            label="Estado"
            data={[
              { value: "ACTIVO", label: "ACTIVO" },
              { value: "INACTIVO", label: "INACTIVO" },
            ]}
            value={form.estado}
            onChange={(value) => actualizarCampo("estado", value || "ACTIVO")}
          />

          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={cerrarModal} disabled={guardando}>
              Cancelar
            </Button>
            <Button onClick={guardarPais} loading={guardando}>
              {paisEditando ? "Guardar cambios" : "Crear país"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

// ============================================================
// ADMIN USUARIOS
// ============================================================

function AdminUsers({
  usuarios,
  cargarUsuarios,
  setSuccess,
  setError,
}) {
  const [cambiandoRolId, setCambiandoRolId] =
    useState(null);

  const [cambiandoEstadoId, setCambiandoEstadoId] =
    useState(null);

  const [busqueda, setBusqueda] =
    useState("");

  const usuariosVisibles = useMemo(() => {
    const q = busqueda.trim().toLocaleLowerCase("es");
    if (!q) return usuarios;

    return usuarios.filter((usuario) => {
      const campos = [
        usuario.nombre,
        usuario.correo,
        usuario.rol,
        usuario.id != null ? String(usuario.id) : "",
      ];

      return campos.some((valor) =>
        String(valor || "")
          .toLocaleLowerCase("es")
          .includes(q)
      );
    });
  }, [usuarios, busqueda]);

  async function cambiarRol(usuario) {
    const rolActual =
      String(
        usuario.rol || "USER"
      ).toUpperCase();

    const nuevoRol =
      rolActual === "ADMIN"
        ? "USER"
        : "ADMIN";

    const accion =
      nuevoRol === "ADMIN"
        ? "convertir en administrador"
        : "cambiar a usuario";

    if (
      !window.confirm(
        `¿Seguro que deseas ${accion} a "${usuario.nombre}"?`
      )
    ) {
      return;
    }

    setError("");
    setSuccess("");
    setCambiandoRolId(usuario.id);

    try {
      const token =
        sessionStorage.getItem(
          "tourSearchToken"
        );

      const response = await fetch(
        `${BACKEND_API}/admin/usuarios/${usuario.id}/rol?rol=${nuevoRol}`,
        {
          method: "PATCH",
          headers: {
            Authorization:
              `Bearer ${token}`,
          },
        }
      );

      const data =
        await response
          .json()
          .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error ||
          data.message ||
          "No fue posible cambiar el rol del usuario."
        );
      }

      await cargarUsuarios();

      setSuccess(
        nuevoRol === "ADMIN"
          ? `Usuario "${usuario.nombre}" ahora es administrador.`
          : `Usuario "${usuario.nombre}" ahora tiene rol USER.`
      );
    } catch (e) {
      setError(
        e.message ||
        "No fue posible cambiar el rol del usuario."
      );
    } finally {
      setCambiandoRolId(null);
    }
  }


  async function cambiarEstado(usuario) {
    const nuevoEstado =
      !usuario.activo;

    const accion =
      nuevoEstado
        ? "activar"
        : "desactivar";

    if (
      !window.confirm(
        `¿Seguro que deseas ${accion} a "${usuario.nombre}"?`
      )
    ) {
      return;
    }

    setError("");
    setSuccess("");
    setCambiandoEstadoId(usuario.id);

    try {
      const token =
        sessionStorage.getItem(
          "tourSearchToken"
        );

      const response = await fetch(
        `${BACKEND_API}/admin/usuarios/${usuario.id}/estado?activo=${nuevoEstado}`,
        {
          method: "PATCH",
          headers: {
            Authorization:
              `Bearer ${token}`,
          },
        }
      );

      const data =
        await response
          .json()
          .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error ||
          data.message ||
          "No fue posible cambiar el estado del usuario."
        );
      }

      await cargarUsuarios();

      setSuccess(
        nuevoEstado
          ? `Usuario "${usuario.nombre}" activado correctamente.`
          : `Usuario "${usuario.nombre}" desactivado correctamente.`
      );
    } catch (e) {
      setError(
        e.message ||
        "No fue posible cambiar el estado del usuario."
      );
    } finally {
      setCambiandoEstadoId(null);
    }
  }


  return (
    <>

      <div className="admin-heading">

        <div>

          <h1>
            Usuarios
          </h1>

          <p>
            Gestión de usuarios y administradores de la plataforma.
          </p>

        </div>

      </div>


      <Paper className="admin-dashboard-card" p="lg" mb="lg">
        <TextInput
          label="Buscar usuario"
          placeholder="Nombre, correo, rol o ID..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.currentTarget.value)}
        />
        <Text size="xs" c="dimmed" mt="xs">
          Mostrando {usuariosVisibles.length} de {usuarios.length} usuarios.
        </Text>
      </Paper>

      <div className="admin-dashboard-card">

        {usuariosVisibles.length > 0 ? (

          usuariosVisibles.map(
            (usuario) => {
              const esAdmin =
                String(
                  usuario.rol ||
                  "USER"
                ).toUpperCase() ===
                "ADMIN";

              return (
                <div
                  className="admin-activity-row"
                  key={usuario.id}
                >

                  <div>

                    <strong>
                      {usuario.nombre}
                    </strong>

                    <small>
                      {usuario.correo}
                      {" · "}
                      2FA: {
                        usuario.twoFactorEnabled
                          ? "ACTIVO"
                          : "INACTIVO"
                      }
                    </small>

                  </div>


                  <div className="admin-row-actions">

                    <Button
                      component="div"
                      size="xs"
                      color={
                        usuario.activo
                          ? "green"
                          : "gray"
                      }
                      variant="light"
                      style={{
                        pointerEvents:
                          "none",
                        minWidth:
                          "82px",
                      }}
                    >
                      {
                        usuario.activo
                          ? "ACTIVO"
                          : "INACTIVO"
                      }
                    </Button>


                    <Button
                      component="div"
                      size="xs"
                      color={
                        esAdmin
                          ? "violet"
                          : "blue"
                      }
                      variant="light"
                      style={{
                        pointerEvents:
                          "none",
                        minWidth:
                          "72px",
                      }}
                    >
                      {
                        esAdmin
                          ? "ADMIN"
                          : "USER"
                      }
                    </Button>


                    <Button
                      size="xs"
                      variant="light"
                      loading={
                        cambiandoRolId ===
                        usuario.id
                      }
                      disabled={
                        cambiandoRolId != null ||
                        cambiandoEstadoId != null
                      }
                      onClick={() =>
                        cambiarRol(
                          usuario
                        )
                      }
                    >
                      {
                        esAdmin
                          ? "Cambiar a USER"
                          : "Hacer ADMIN"
                      }
                    </Button>


                    <Button
                      size="xs"
                      color={
                        usuario.activo
                          ? "orange"
                          : "green"
                      }
                      variant="light"
                      loading={
                        cambiandoEstadoId ===
                        usuario.id
                      }
                      disabled={
                        cambiandoEstadoId != null ||
                        cambiandoRolId != null
                      }
                      onClick={() =>
                        cambiarEstado(
                          usuario
                        )
                      }
                    >
                      {
                        usuario.activo
                          ? "Desactivar"
                          : "Activar"
                      }
                    </Button>

                  </div>

                </div>
              );
            }
          )

        ) : (

          <div className="admin-empty">
            {busqueda.trim() ? "No se encontraron usuarios para esa búsqueda." : "No hay usuarios disponibles."}
          </div>

        )}

      </div>

    </>
  );
}


// ============================================================
// ADMIN REGISTROS
// ============================================================

function AdminRecords({
  registros,
  cargarRegistros,
  setSuccess,
  setError,
}) {
  const [termino, setTermino] =
    useState("");

  const [tipoBusqueda, setTipoBusqueda] =
    useState("actividad");

  const [resultados, setResultados] =
    useState(null);

  const [buscando, setBuscando] =
    useState(false);

  const [cambiandoEstadoCodigo, setCambiandoEstadoCodigo] =
    useState(null);

  const [eliminandoCodigo, setEliminandoCodigo] =
    useState(null);


  const lista =
    resultados !== null
      ? resultados
      : registros;


  async function buscarRegistros() {
    const texto =
      termino.trim();

    if (!texto) {
      setResultados(null);
      await cargarRegistros();
      return;
    }

    setError("");
    setSuccess("");
    setBuscando(true);

    try {
      const token =
        sessionStorage.getItem(
          "tourSearchToken"
        );

      const response = await fetch(
        `${BACKEND_API}/registros/buscar?tipo=${encodeURIComponent(tipoBusqueda)}&termino=${encodeURIComponent(texto)}`,
        {
          headers: token
            ? {
                Authorization:
                  `Bearer ${token}`,
              }
            : {},
        }
      );

      const data =
        await response
          .json()
          .catch(() => []);

      if (!response.ok) {
        throw new Error(
          data.error ||
          data.message ||
          "No fue posible buscar registros."
        );
      }

      setResultados(
        Array.isArray(data)
          ? data
          : []
      );
    } catch (e) {
      setError(
        e.message ||
        "No fue posible buscar registros."
      );
    } finally {
      setBuscando(false);
    }
  }


  async function cambiarEstado(
    registro,
    nuevoEstado
  ) {
    const codigo =
      registro.codigoInterno;

    if (!codigo) {
      setError(
        "El registro no tiene código interno."
      );
      return;
    }

    if (
      !window.confirm(
        `¿Cambiar el registro ${codigo} a estado ${nuevoEstado}?`
      )
    ) {
      return;
    }

    setError("");
    setSuccess("");
    setCambiandoEstadoCodigo(codigo);

    try {
      const token =
        sessionStorage.getItem(
          "tourSearchToken"
        );

      const response = await fetch(
        `${BACKEND_API}/registros/${encodeURIComponent(codigo)}/estado?estado=${encodeURIComponent(nuevoEstado)}`,
        {
          method: "PATCH",
          headers: token
            ? {
                Authorization:
                  `Bearer ${token}`,
              }
            : {},
        }
      );

      const data =
        await response
          .json()
          .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error ||
          data.message ||
          "No fue posible cambiar el estado del registro."
        );
      }

      await cargarRegistros();
      setResultados(null);

      setSuccess(
        `Registro ${codigo} actualizado a ${nuevoEstado}.`
      );
    } catch (e) {
      setError(
        e.message ||
        "No fue posible cambiar el estado del registro."
      );
    } finally {
      setCambiandoEstadoCodigo(null);
    }
  }


  async function eliminarRegistro(
    registro
  ) {
    const codigo =
      registro.codigoInterno;

    if (!codigo) {
      setError(
        "El registro no tiene código interno."
      );
      return;
    }

    if (
      !window.confirm(
        `¿Eliminar definitivamente el registro ${codigo} de "${registro.nombre}"?\n\nEsta acción no se puede deshacer.`
      )
    ) {
      return;
    }

    setError("");
    setSuccess("");
    setEliminandoCodigo(codigo);

    try {
      const token =
        sessionStorage.getItem(
          "tourSearchToken"
        );

      const response = await fetch(
        `${BACKEND_API}/registros/${encodeURIComponent(codigo)}`,
        {
          method: "DELETE",
          headers: token
            ? {
                Authorization:
                  `Bearer ${token}`,
              }
            : {},
        }
      );

      if (!response.ok) {
        const data =
          await response
            .json()
            .catch(() => ({}));

        throw new Error(
          data.error ||
          data.message ||
          "No fue posible eliminar el registro."
        );
      }

      await cargarRegistros();
      setResultados(null);

      setSuccess(
        `Registro ${codigo} eliminado correctamente.`
      );
    } catch (e) {
      setError(
        e.message ||
        "No fue posible eliminar el registro."
      );
    } finally {
      setEliminandoCodigo(null);
    }
  }


  function colorEstado(
    estado
  ) {
    switch (
      String(
        estado ||
        ""
      ).toUpperCase()
    ) {
      case "ACTIVO":
        return "green";

      case "INACTIVO":
        return "gray";

      case "ELIMINADO":
        return "red";

      default:
        return "blue";
    }
  }


  return (
    <>

      <div className="admin-heading">

        <div>

          <h1>
            Registros
          </h1>

          <p>
            Consulta y administra los registros turísticos almacenados.
          </p>

        </div>

      </div>


      <Paper
        className="admin-dashboard-card"
        p="lg"
        mb="lg"
      >

        <SimpleGrid
          cols={{
            base: 1,
            md: 3,
          }}
        >

          <Select
            label="Buscar por"
            value={tipoBusqueda}
            onChange={(value) =>
              setTipoBusqueda(
                value ||
                "actividad"
              )
            }
            data={[
              {
                value: "actividad",
                label: "Actividad",
              },
              {
                value: "operador",
                label: "Operador",
              },
            ]}
          />


          <TextInput
            label="Término"
            placeholder="Nombre de actividad u operador"
            value={termino}
            onChange={(e) =>
              setTermino(
                e.currentTarget.value
              )
            }
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                buscarRegistros();
              }
            }}
          />


          <Group
            align="flex-end"
            gap="sm"
          >

            <Button
              onClick={
                buscarRegistros
              }
              loading={
                buscando
              }
            >
              Buscar
            </Button>


            <Button
              variant="default"
              onClick={async () => {
                setTermino("");
                setResultados(null);
                await cargarRegistros();
              }}
            >
              Limpiar
            </Button>

          </Group>

        </SimpleGrid>

      </Paper>


      <div className="admin-dashboard-card">

        {lista.length > 0 ? (

          lista.map(
            (registro) => {
              const codigo =
                registro.codigoInterno ||
                String(
                  registro.id ||
                  ""
                );

              const estado =
                String(
                  registro.estado ||
                  "ACTIVO"
                ).toUpperCase();

              return (
                <div
                  className="admin-activity-row"
                  key={
                    registro.id ||
                    codigo
                  }
                >

                  <div>

                    <strong>
                      {registro.nombre}
                    </strong>

                    <small>
                      Código: {
                        registro.codigoInterno ||
                        "Sin código"
                      }
                      {" · "}
                      Operador: {
                        registro.operador ||
                        "Sin operador"
                      }
                    </small>

                    {registro.sourceUrl && (
                      <small>
                        {esUrlWeb(registro.sourceUrl) ? (
                          <a
                            href={registro.sourceUrl}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Ver fuente original ↗
                          </a>
                        ) : (
                          <span
                            title={
                              esFuenteLocal(registro.sourceUrl)
                                ? registro.sourceUrl.replace(/^local:/i, "")
                                : registro.sourceUrl
                            }
                          >
                            {etiquetaFuente(registro.sourceUrl)}
                          </span>
                        )}
                      </small>
                    )}

                  </div>


                  <div className="admin-row-actions">

                    <Button
                      component="div"
                      size="xs"
                      color={
                        colorEstado(
                          estado
                        )
                      }
                      variant="light"
                      style={{
                        pointerEvents:
                          "none",
                        minWidth:
                          "88px",
                      }}
                    >
                      {estado}
                    </Button>


                    {estado !== "ACTIVO" && (

                      <Button
                        size="xs"
                        color="green"
                        variant="light"
                        loading={
                          cambiandoEstadoCodigo ===
                          registro.codigoInterno
                        }
                        disabled={
                          cambiandoEstadoCodigo != null ||
                          eliminandoCodigo != null
                        }
                        onClick={() =>
                          cambiarEstado(
                            registro,
                            "ACTIVO"
                          )
                        }
                      >
                        Activar
                      </Button>

                    )}


                    {estado !== "INACTIVO" && (

                      <Button
                        size="xs"
                        color="orange"
                        variant="light"
                        loading={
                          cambiandoEstadoCodigo ===
                          registro.codigoInterno
                        }
                        disabled={
                          cambiandoEstadoCodigo != null ||
                          eliminandoCodigo != null
                        }
                        onClick={() =>
                          cambiarEstado(
                            registro,
                            "INACTIVO"
                          )
                        }
                      >
                        Desactivar
                      </Button>

                    )}


                    <Button
                      size="xs"
                      color="red"
                      variant="light"
                      loading={
                        eliminandoCodigo ===
                        registro.codigoInterno
                      }
                      disabled={
                        eliminandoCodigo != null ||
                        cambiandoEstadoCodigo != null
                      }
                      onClick={() =>
                        eliminarRegistro(
                          registro
                        )
                      }
                    >
                      Eliminar
                    </Button>

                  </div>

                </div>
              );
            }
          )

        ) : (

          <div className="admin-empty">
            No hay registros disponibles.
          </div>

        )}

      </div>

    </>
  );
}


// ============================================================
// ADMIN SITIO
// ============================================================

function AdminSite() {
  return (
    <>

      <div className="admin-heading">

        <div>

          <h1>
            Configuración del sitio
          </h1>

          <p>
            Modifica los contenidos visibles sin tocar el código.
          </p>

        </div>

      </div>


      <div className="admin-site-layout">

        <Paper
          className="admin-dashboard-card"

          p="xl"
        >

          <Stack>

            <TextInput
              label="Nombre de la plataforma"

              defaultValue="Tour Search"
            />


            <TextInput
              label="Título principal"

              defaultValue="Descubre. Extrae. Organiza."
            />


            <Textarea
              label="Descripción de portada"

              defaultValue="Busca actividades publicadas por operadores turísticos."

              minRows={4}
            />


            <TextInput
              label="Texto del pie de página"

              defaultValue="Tour Search Platform"
            />


            <Group justify="flex-end">

              <Button>
                Guardar cambios
              </Button>

            </Group>


            <Text
              size="xs"
              c="dimmed"
            >
              En la siguiente etapa
              conectaremos esta
              configuración a PostgreSQL.
            </Text>

          </Stack>

        </Paper>

      </div>

    </>
  );
}


// ============================================================
// PLACEHOLDER
// ============================================================

function AdminPlaceholder({
  title,
  text,
}) {
  return (
    <>

      <div className="admin-heading">

        <div>

          <h1>
            {title}
          </h1>

          <p>
            {text}
          </p>

        </div>

      </div>


      <div className="admin-dashboard-card admin-placeholder">

        <span>
          ◈
        </span>

        <h2>
          {title}
        </h2>

        <p>
          Este módulo quedará conectado
          en una siguiente etapa.
        </p>

      </div>

    </>
  );
}


// ============================================================
// PAGE TITLE
// ============================================================

function PageTitle({
  eyebrow,
  title,
  text,
}) {
  return (
    <header className="page-title">

      <span>
        {eyebrow}
      </span>

      <h1>
        {title}
      </h1>

      <p>
        {text}
      </p>

    </header>
  );
}


// ============================================================
// FOOTER
// ============================================================

function Footer() {
  return (
    <footer className="site-footer">

      <span>
        ◎ Tour Search Platform
      </span>

      <span>
        •
      </span>

      <span>
        v1.0.0
      </span>

      <span>
        •
      </span>

      <span>
        Todos los derechos reservados
      </span>

    </footer>
  );
}


// ============================================================
// ICONOS
// ============================================================

function navIcon(item) {
  const icons = {
    Inicio: "⌂",
    Consultar: "⌕",
    Búsqueda: "⌕",
    Filtros: "▽",
    Resultados: "☷",
    Historial: "◷",
    Administrador: "♢",
  };

  return icons[item] || "•";
}


// ============================================================
// CONVERTIR ACTIVIDAD BACKEND -> TOUR
// ============================================================

function actividadATour(actividad) {
  if (!actividad) {
    return null;
  }

  const itinerario = (actividad.itinerario || []).map((paso, index) => {
    if (typeof paso === "string") {
      return {
        orden: index + 1,
        titulo: null,
        descripcion: paso,
      };
    }

    return {
      orden: paso.orden ?? index + 1,
      titulo: paso.titulo ?? null,
      descripcion: paso.descripcion || String(paso || ""),
      duracion: paso.duracion ?? null,
    };
  });

  return {
    id: actividad.id,
    nombre: actividad.nombre,
    descripcion: actividad.descripcion,
    descripcion_original: actividad.descripcion,
    ubicacion: actividad.ubicacion,
    destino: actividad.destino,
    duracion: actividad.duracion,
    duracion_original: actividad.duracion,
    edadMinima: actividad.edadMinima,
    edadMaxima: actividad.edadMaxima,
    edad_minima: actividad.edadMinima,
    edad_maxima: actividad.edadMaxima,
    idiomas: actividad.idiomas || [],
    imagenes: actividad.imagenes || [],
    highlights: actividad.highlights || [],
    itinerario,
    horarios: actividad.horarios || [],
    restricciones: actividad.restricciones || [],
    incluye: actividad.incluye || [],
    no_incluye: actividad.noIncluye || actividad.no_incluye || [],
    que_llevar: actividad.queLlevar || actividad.que_llevar || [],
    no_llevar: actividad.noLlevar || actividad.no_llevar || [],
    recomendaciones: actividad.recomendaciones || [],
    urlOrigen: actividad.urlOrigen,
    source_url: actividad.urlOrigen,
    operadorTuristico: actividad.operadorTuristico,
    nombre_operador: actividad.operadorTuristico?.nombre,
    activo: actividad.activo,
  };
}

// ============================================================
// AUTENTICACIÓN
// ============================================================

function AppProtegida() {
  const [estadoSesion, setEstadoSesion] =
    useState({
      cargando: true,
      autenticado: false,
      isAdmin: false,
    });

  useEffect(() => {
    validarSesion();
  }, []);

  async function validarSesion() {
    const token =
      sessionStorage.getItem(
        "tourSearchToken"
      );

    if (!token) {
      setEstadoSesion({
        cargando: false,
        autenticado: false,
        isAdmin: false,
      });

      return;
    }

    try {
      const response = await fetch(
        `${BACKEND_API}/auth/me`,
        {
          headers: {
            Authorization:
              `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        cerrarSesion();
        return;
      }

      const data =
        await response.json();

      if (!data.authenticated) {
        cerrarSesion();
        return;
      }

      setEstadoSesion({
        cargando: false,
        autenticado: true,
        isAdmin:
          data.admin === true ||
          data.roles?.includes(
            "ROLE_ADMIN"
          ),
      });
    } catch (e) {
      console.error(
        "No se pudo validar la sesión:",
        e
      );

      cerrarSesion();
    }
  }

  function manejarAutenticacion() {
    validarSesion();
  }

  function cerrarSesion() {
    sessionStorage.removeItem(
      "tourSearchToken"
    );

    sessionStorage.removeItem(
      "tourSearchUser"
    );

    setEstadoSesion({
      cargando: false,
      autenticado: false,
      isAdmin: false,
    });
  }

  if (estadoSesion.cargando) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
        }}
      >
        <Stack align="center">
          <Loader />
          <Text>
            Validando sesión...
          </Text>
        </Stack>
      </div>
    );
  }

  if (!estadoSesion.autenticado) {
    return (
      <AuthLogin
        onAuthenticated={
          manejarAutenticacion
        }
      />
    );
  }

  return (
    <App
      onLogout={
        cerrarSesion
      }
      isAdmin={
        estadoSesion.isAdmin
      }
    />
  );
}

// ============================================================
// REACT
// ============================================================

createRoot(
  document.getElementById(
    "root"
  )
).render(

  <MantineProvider
    defaultColorScheme="dark"
  >

    <AppProtegida />

  </MantineProvider>

);