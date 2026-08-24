import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import heroImage from "./assets/volcan-hero.png";
import "./styles.css";
import "./navigation.css";

const SCRAPER_API = "http://localhost:8001";
const REGISTRY_API = "http://localhost:8080/api/registros";
const NAV = ["Inicio", "Consultar", "Búsqueda", "Filtros", "Resultados", "Historial"];

function registeredTour(record) {
  return {
    ...(record.datosExtraidos || {}),
    nombre: record.nombre,
    nombre_operador: record.operador,
    source_url: record.sourceUrl,
    codigo_interno: record.codigoInterno,
    pedido_id: record.pedidoId,
    estado: record.estado,
    consulted_at: record.actualizadoEn || record.creadoEn,
  };
}

function App() {
  const [view, setView] = useState("Inicio");
  const [previousView, setPreviousView] = useState("Inicio");
  const [directUrl, setDirectUrl] = useState("");
  const [operatorForm, setOperatorForm] = useState({ url_operador: "", nombre_operador: "", pedido: "", max_paginas: 3, limite: 5, puntaje_minimo: 20 });
  const [apiResults, setApiResults] = useState([]);
  const [tour, setTour] = useState(null);
  const [history, setHistory] = useState([]);
  const [term, setTerm] = useState("");
  const [filterType, setFilterType] = useState("to");
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  const loadHistory = async () => {
    const response = await fetch(REGISTRY_API);
    const data = await response.json().catch(() => []);
    if (!response.ok) throw new Error(data.detail || "No fue posible cargar los registros guardados.");
    const records = Array.isArray(data) ? data.map(registeredTour) : [];
    setHistory(records);
    return records;
  };

  useEffect(() => {
    loadHistory().catch((e) => setError(e.message));
  }, []);

  const navigate = (nextView) => {
    if (nextView === view) return;
    setPreviousView(view);
    setView(nextView);
  };

  const postScraper = async (path, body) => {
    const response = await fetch(`${SCRAPER_API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "No fue posible completar la solicitud.");
    return data;
  };

  const findRegisteredByUrl = async (url) => {
    const response = await fetch(`${REGISTRY_API}/por-url?sourceUrl=${encodeURIComponent(url)}`);
    if (response.status === 404) return null;
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "No fue posible revisar los registros existentes.");
    return registeredTour(data);
  };

  const saveRegistry = async (item) => {
    const response = await fetch(REGISTRY_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pedidoId: item.pedido_id || null,
        nombre: item.nombre,
        operador: item.nombre_operador || "Operador no publicado",
        sourceUrl: item.source_url,
        datosExtraidos: item,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "La información se extrajo, pero no pudo guardarse.");
    return registeredTour(data);
  };

  const extract = async (url, operator = "") => {
    setLoading("Revisando si la actividad ya está registrada..."); setError("");
    try {
      const stored = await findRegisteredByUrl(url);
      if (stored) {
        setTour(stored);
        navigate("Resultados");
        return;
      }

      setLoading("Extrayendo información publicada...");
      const extracted = await postScraper("/scraper/extract", { url, nombre_operador: operator || null });
      setLoading("Guardando la información...");
      const saved = await saveRegistry(extracted);
      setTour(saved);
      await loadHistory();
      navigate("Resultados");
    }
    catch (e) { setError(e.message); } finally { setLoading(""); }
  };
  const directExtract = (event) => { event.preventDefault(); extract(directUrl.trim()); };
  const searchOperator = async (event) => {
    event.preventDefault(); setLoading("Buscando coincidencias en el operador..."); setError("");
    try { const data = await postScraper("/scraper/search", { ...operatorForm, nombre_operador: operatorForm.nombre_operador || null, max_paginas: Number(operatorForm.max_paginas), limite: Number(operatorForm.limite), puntaje_minimo: Number(operatorForm.puntaje_minimo) }); setApiResults(data.resultados || []); setTour(null); navigate("Resultados"); }
    catch (e) { setError(e.message); } finally { setLoading(""); }
  };
  const existing = useMemo(() => {
    const q = term.trim().toLocaleLowerCase("es");
    if (!q) return history;
    return history.filter((item) => (filterType === "to" ? item.nombre_operador : item.nombre)?.toLocaleLowerCase("es").includes(q));
  }, [history, term, filterType]);
  const openStored = (item) => { setTour(item); navigate("Resultados"); };

  return <div className="site-shell">
    <Nav view={view} setView={navigate} />
    {view === "Inicio" && <Home setView={navigate} directUrl={directUrl} setDirectUrl={setDirectUrl} directExtract={directExtract} loading={loading} />}
    <main className={view === "Inicio" ? "" : "page-wrap"} style={view === "Inicio" ? undefined : { "--page-image": `url(${heroImage})` }}>
      {view !== "Inicio" && <div className="container-xl page-tools"><button className="back-button" onClick={() => navigate(previousView || "Inicio")}><span aria-hidden="true">←</span> Volver</button></div>}
      {error && <div className="container-xl pt-4"><div className="alert alert-danger">{error}</div></div>}
      {loading && <div className="container-xl pt-4"><div className="loading-line"><span className="spinner-border spinner-border-sm" />{loading}</div></div>}
      {view === "Consultar" && <Consult directUrl={directUrl} setDirectUrl={setDirectUrl} directExtract={directExtract} form={operatorForm} setForm={setOperatorForm} search={searchOperator} loading={loading} />}
      {view === "Búsqueda" && <ExistingSearch term={term} setTerm={setTerm} filterType={filterType} setFilterType={setFilterType} records={existing} openStored={openStored} setView={navigate} />}
      {view === "Filtros" && <Filters term={term} setTerm={setTerm} filterType={filterType} setFilterType={setFilterType} records={existing} openStored={openStored} />}
      {view === "Resultados" && <Results tour={tour} apiResults={apiResults} extract={(url) => extract(url, operatorForm.nombre_operador)} />}
      {view === "Historial" && <History records={history} openStored={openStored} />}
    </main>
    <footer><div className="container-xl">Extraer información · Investigación turística</div></footer>
  </div>;
}

function Nav({ view, setView }) { return <nav className="main-nav"><div className="container-xl nav-inner"><button className="brand" onClick={() => setView("Inicio")}>Extraer información</button><div className="nav-links">{NAV.map((item) => <button key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}>{item}</button>)}</div><span className="service"><i /> Servicio activo</span></div></nav>; }

function Home({ setView, directUrl, setDirectUrl, directExtract, loading }) { return <><section className="hero" style={{ backgroundImage: `linear-gradient(90deg, rgba(9,15,18,.88), rgba(9,15,18,.28)), url(${heroImage})` }}><div className="container-xl hero-inner"><p className="kicker">INVESTIGACIÓN DE EXPERIENCIAS</p><h1>Extraer información</h1><p className="hero-copy">Consulta fuentes de operadores turísticos y conserva la información necesaria para construir fichas confiables.</p><form className="hero-search" onSubmit={directExtract}><input type="url" required placeholder="Pega el enlace de una actividad" value={directUrl} onChange={(e) => setDirectUrl(e.target.value)} /><button disabled={!!loading}>Extraer</button></form><button className="text-action" onClick={() => setView("Búsqueda")}>Buscar primero en los registros existentes →</button></div></section><section className="home-guide"><div className="container-xl"><header><span>FLUJO DE TRABAJO</span><h2>Consulta solo cuando sea necesario</h2></header><div className="guide-grid"><article><b>Buscar</b><p>Comprueba si el TO o la actividad ya están registrados.</p></article><article><b>Revisar</b><p>Abre la ficha existente y verifica su fuente original.</p></article><article><b>Extraer</b><p>Ejecuta el scraper solamente cuando no existan resultados.</p></article></div></div></section></>; }

function PageTitle({ eyebrow, title, text }) { return <header className="page-title"><span>{eyebrow}</span><h1>{title}</h1><p>{text}</p></header>; }
function Consult({ directUrl, setDirectUrl, directExtract, form, setForm, search, loading }) { const change = ({ target }) => setForm((old) => ({ ...old, [target.name]: target.value })); return <div className="container-xl"><PageTitle eyebrow="NUEVA CONSULTA" title="Consultar una fuente" text="Extrae una actividad mediante su enlace o encuéntrala dentro del sitio de un operador." /><section className="dark-panel"><h2>Enlace directo</h2><form className="inline-form" onSubmit={directExtract}><input type="url" required placeholder="https://operador.com/tour/actividad" value={directUrl} onChange={(e) => setDirectUrl(e.target.value)} /><button disabled={!!loading}>Extraer información</button></form></section><section className="operator-panel"><h2>Buscar dentro del operador</h2><form onSubmit={search}><div className="form-grid"><Field label="Sitio del operador" name="url_operador" value={form.url_operador} change={change} type="url" /><Field label="Nombre del TO" name="nombre_operador" value={form.nombre_operador} change={change} /><Field label="Actividad solicitada" name="pedido" value={form.pedido} change={change} /></div><div className="form-actions"><button disabled={!!loading}>Buscar actividades relacionadas</button></div></form></section></div>; }
function Field({ label, name, value, change, type = "text" }) { return <label>{label}<input type={type} required={name !== "nombre_operador"} name={name} value={value} onChange={change} /></label>; }

function ExistingSearch({ term, setTerm, filterType, setFilterType, records, openStored, setView }) { return <div className="container-xl"><PageTitle eyebrow="REGISTROS EXISTENTES" title="Buscar antes de extraer" text="Evita repetir el scraping comprobando si la información ya está disponible." /><SearchBar term={term} setTerm={setTerm} filterType={filterType} setFilterType={setFilterType} /><RecordGrid records={records} openStored={openStored} emptyAction={() => setView("Consultar")} /></div>; }
function Filters({ term, setTerm, filterType, setFilterType, records, openStored }) { return <div className="container-xl"><PageTitle eyebrow="FILTROS" title="Filtrar información registrada" text="Organiza las fichas existentes por tour operador o por actividad." /><SearchBar term={term} setTerm={setTerm} filterType={filterType} setFilterType={setFilterType} /><RecordGrid records={records} openStored={openStored} /></div>; }
function SearchBar({ term, setTerm, filterType, setFilterType }) { return <section className="search-module"><div><label>Buscar en los registros</label><input placeholder="Nombre del TO o actividad" value={term} onChange={(e) => setTerm(e.target.value)} /></div><div><label>Filtrar por</label><div className="segmented"><button className={filterType === "to" ? "active" : ""} onClick={() => setFilterType("to")}>Tour operador</button><button className={filterType === "activity" ? "active" : ""} onClick={() => setFilterType("activity")}>Actividad</button></div></div></section>; }
function RecordGrid({ records, openStored, emptyAction }) { return records.length ? <section className="record-section"><div className="section-heading"><h2>Información registrada</h2><span>{records.length} coincidencia(s)</span></div><div className="record-grid">{records.map((item) => <article className="record-card" key={item.codigo_interno || item.source_url}><small>REGISTRO {item.codigo_interno || "SIN CÓDIGO"}</small><h3>{item.nombre}</h3><p className="record-operator">{item.nombre_operador || "Operador no publicado"}</p><dl><div><dt>ID del pedido</dt><dd>{item.pedido_id || "No asignado"}</dd></div><div><dt>Ubicación</dt><dd>{[item.ubicacion?.ciudad, item.ubicacion?.pais].filter(Boolean).join(", ") || "No publicada"}</dd></div><div><dt>Última actualización</dt><dd>{formatDate(item.consulted_at)}</dd></div></dl><button onClick={() => openStored(item)}>Abrir ficha</button></article>)}</div></section> : <div className="empty-records"><h2>No se encontraron registros</h2><p>Prueba otro término o realiza una nueva extracción.</p>{emptyAction && <button onClick={emptyAction}>Ir a Consultar</button>}</div>; }

function Results({ tour, apiResults, extract }) { return <div className="container-xl"><PageTitle eyebrow="RESULTADOS" title="Información encontrada" text="Revisa los datos y consulta siempre la fuente original." />{apiResults.length > 0 && !tour && <section className="api-list">{apiResults.map((item) => <article key={item.url}><div><h3>{item.titulo_encontrado}</h3><p>Coincidencia {item.nivel} · {item.puntaje} puntos</p></div><button onClick={() => extract(item.url)}>Extraer ficha</button></article>)}</section>}{tour ? <TourDetail tour={tour} /> : apiResults.length === 0 && <div className="empty-records"><h2>Todavía no hay resultados</h2><p>Realiza una consulta o abre una ficha del historial.</p></div>}</div>; }
function TourDetail({ tour }) { const location = [tour.ubicacion?.ciudad, tour.ubicacion?.region, tour.ubicacion?.pais].filter(Boolean).join(", "); return <article className="tour-detail"><header><div><small>{tour.codigo_interno ? `REGISTRO ${tour.codigo_interno} · ` : ""}{tour.nombre_operador}</small><h2>{tour.nombre}</h2>{tour.pedido_id && <p>ID del pedido: {tour.pedido_id}</p>}</div><a href={tour.source_url} target="_blank" rel="noreferrer">Ver fuente original ↗</a></header><div className="facts"><Fact label="Ubicación" value={location} /><Fact label="Duración" value={tour.duracion_original} /><Fact label="Idiomas" value={tour.idiomas?.join(", ")} /><Fact label="Disponibilidad" value={tour.calendario?.tipo?.replaceAll("_", " ")} /></div><p className="description">{tour.descripcion_original || tour.descripcion_corta}</p><div className="detail-grid">{tour.itinerario?.length > 0 && <Info title="Itinerario" ordered values={tour.itinerario.map((x) => `${x.titulo || `Paso ${x.orden}`}: ${x.descripcion}`)} />}<Info title="Incluye" values={tour.incluye} /><Info title="No incluye" values={tour.no_incluye} /><Info title="Qué llevar" values={tour.que_llevar} /><Info title="No llevar" values={tour.no_llevar} /><Info title="Recomendaciones" values={tour.recomendaciones} /><Info title="Restricciones" values={tour.restricciones} /></div></article>; }
function Fact({ label, value }) { return <div><span>{label}</span><b>{value || "No publicado"}</b></div>; }
function Info({ title, values, ordered }) { if (!values?.length) return null; const Tag = ordered ? "ol" : "ul"; return <section><h3>{title}</h3><Tag>{values.map((x, i) => <li key={i}>{x}</li>)}</Tag></section>; }

function History({ records, openStored }) { return <div className="container-xl"><PageTitle eyebrow="HISTORIAL" title="Consultas realizadas" text="Registros guardados en PostgreSQL. Puedes reabrirlos sin ejecutar nuevamente el scraper." />{records.length > 0 ? <><div className="history-actions"><span>{records.length} registro(s) guardado(s)</span></div><div className="history-table"><div className="history-head"><span>Actividad</span><span>Tour operador</span><span>Última actualización</span><span>Acción</span></div>{records.map((item) => <div className="history-row" key={item.codigo_interno || item.source_url}><strong>{item.codigo_interno ? `${item.codigo_interno} · ` : ""}{item.nombre}</strong><span>{item.nombre_operador || "No publicado"}</span><time>{formatDate(item.consulted_at)}</time><button onClick={() => openStored(item)}>Abrir ficha</button></div>)}</div></> : <div className="empty-records"><h2>El historial está vacío</h2><p>Las fichas guardadas en la base de datos aparecerán aquí.</p></div>}</div>; }
function formatDate(value) { return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Sin fecha"; }

createRoot(document.getElementById("root")).render(<App />);
