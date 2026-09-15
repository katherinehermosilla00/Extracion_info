# Tour Search Platform

Plataforma desarrollada para automatizar la extracción, almacenamiento, validación y consulta de información de actividades y operadores turísticos.

El sistema permite obtener información desde sitios web y documentos, almacenarla en PostgreSQL mediante una API desarrollada con Spring Boot y visualizarla desde una interfaz web desarrollada con React.

## Tecnologías utilizadas

### Frontend
- React
- Vite
- Mantine
- JavaScript

### Backend
- Java 21
- Spring Boot
- Spring Data JPA / Hibernate
- Maven
- Swagger / OpenAPI

### Base de datos
- PostgreSQL 17
- Docker

### Extracción de información
- Python
- FastAPI
- BeautifulSoup
- Extracción desde sitios web
- Extracción desde archivos PDF y Word

---

## Arquitectura general

El proyecto está compuesto por los siguientes módulos:

```text
tour-search-platform/
│
├── backend/
│   └── API REST desarrollada con Spring Boot
│
├── frontend/
│   └── Aplicación web React + Vite
│
├── scraper_v2/
│   └── Servicio FastAPI para extracción desde sitios web
│
├── extractor_pdf_word/
│   └── Extracción e importación desde documentos PDF y Word
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

El flujo principal de información es:

```text
Sitio web / PDF / Word
          ↓
Scraper / Extractor
          ↓
Backend Spring Boot
          ↓
PostgreSQL
          ↓
Frontend React
```

---

## 1. Base de datos PostgreSQL

Desde la raíz del proyecto:

```bash
docker compose up -d postgres
```

Para comprobar el estado de los contenedores:

```bash
docker compose ps
```

PostgreSQL utiliza por defecto el puerto:

```text
5432
```

---

## 2. Backend Java

### Requisitos

- Java 21
- Maven
- PostgreSQL iniciado

Ingresar a la carpeta:

```bash
cd backend
```

Ejecutar:

```bash
mvn spring-boot:run
```

Backend:

```text
http://localhost:8080
```

Swagger:

```text
http://localhost:8080/swagger-ui.html
```

### API de actividades

Endpoint principal:

```text
GET /api/actividades
```

Consultar una actividad:

```text
GET /api/actividades/{id}
```

Consultar actividades por operador:

```text
GET /api/actividades/operador/{operadorTuristicoId}
```

Buscar actividades:

```text
GET /api/actividades/buscar?texto={texto}
```

Crear una actividad:

```text
POST /api/actividades
```

Actualizar una actividad:

```text
PUT /api/actividades/{id}
```

Desactivar una actividad:

```text
PATCH /api/actividades/{id}/desactivar
```

Eliminar una actividad:

```text
DELETE /api/actividades/{id}
```

---

## 3. Información almacenada de las actividades

Actualmente una actividad puede almacenar:

- Nombre
- Descripción
- Ubicación
- Destino
- Duración
- Edad mínima
- Edad máxima
- Idiomas
- Highlights
- Itinerario
- Horarios
- Restricciones
- URL de origen
- Operador turístico asociado
- Estado activo/inactivo

Las actividades están relacionadas con sus respectivos operadores turísticos.

---

## 4. Búsqueda de tours

El backend dispone del endpoint:

```text
GET /api/tours/search
```

Permite utilizar filtros como:

```text
query
location
category
minPrice
maxPrice
minDuration
maxDuration
age
startDate
endDate
```

Ejemplo:

```text
GET /api/tours/search?location=Santiago&category=Trekking&age=25
```

---

## 5. Scraper Web con FastAPI

El scraper actual se encuentra en:

```text
scraper_v2/
```

Ingresar a la carpeta:

```bash
cd scraper_v2
```

Crear un entorno virtual:

```bash
python -m venv .venv
```

En Windows:

```bash
.venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar FastAPI:

```bash
python -m uvicorn main:app --reload --port 8000
```

API del scraper:

```text
http://localhost:8000
```

Swagger de FastAPI:

```text
http://localhost:8000/docs
```

### Funcionamiento del scraper

El scraper analiza páginas de actividades turísticas y busca extraer información estructurada como:

- Nombre de la actividad
- Descripción
- Destino
- Duración
- Edad mínima y máxima
- Idiomas
- Highlights
- Itinerario
- Horarios
- Restricciones

La extracción utiliza reglas genéricas y análisis contextual para poder trabajar con diferentes estructuras de sitios web.

También existe detección de fuentes que bloquean el scraping mediante mecanismos como CAPTCHA o sistemas anti-bot.

---

## 6. Extracción desde PDF y Word

El proyecto incluye el módulo:

```text
extractor_pdf_word/
```

Este módulo permite procesar información proveniente de documentos de operadores turísticos.

El extractor puede identificar y almacenar información como:

- Actividad
- Descripción
- Destino
- Duración
- Highlights
- Itinerario
- Horarios
- Restricciones
- Idiomas
- Edades, cuando están disponibles

Los datos extraídos son enviados al backend y almacenados en PostgreSQL.

El extractor permite procesar actividades específicas u operadores determinados mediante filtros de ejecución.

---

## 7. Frontend

Ingresar a:

```bash
cd frontend
```

Instalar dependencias:

```bash
npm install
```

Ejecutar:

```bash
npm run dev
```

Vite utilizará normalmente:

```text
http://localhost:5173
```

Si el puerto 5173 se encuentra ocupado, utilizará automáticamente otro puerto disponible, por ejemplo:

```text
http://localhost:5174
```

---

## 8. Funcionalidades de la plataforma

La interfaz permite actualmente:

- Iniciar sesión en la plataforma
- Consultar actividades turísticas
- Buscar actividades
- Visualizar fichas detalladas
- Consultar operadores turísticos
- Consultar países
- Administrar actividades
- Administrar operadores
- Administrar países
- Administrar usuarios
- Consultar registros de extracción
- Editar información almacenada
- Desactivar registros
- Eliminar registros según las funciones disponibles

Las fichas pueden mostrar, dependiendo de la información disponible:

- Descripción
- Duración
- Destino
- Ubicación
- Idiomas
- Edad
- Highlights
- Itinerario
- Horarios
- Restricciones
- Fuente de información

Las actividades importadas desde documentos locales son identificadas como:

```text
Documento importado localmente
```

---

## 9. Autenticación y seguridad

El backend incorpora autenticación y autorización mediante JWT.

La clave JWT debe configurarse mediante una variable de entorno y no debe almacenarse directamente en el repositorio.

Ejemplo en PowerShell:

```powershell
$env:JWT_SECRET="TU_CLAVE_CONFIGURADA_LOCALMENTE"
```

> No subir contraseñas, claves JWT, tokens ni otras credenciales al repositorio.

El sistema también incorpora funcionalidades relacionadas con:

- Inicio de sesión
- Usuarios
- Roles
- Recuperación de contraseña
- Control de acceso a funciones administrativas

---

## 10. Consideraciones sobre la extracción

El scraping no se ejecuta directamente por cada búsqueda realizada por el usuario.

El flujo recomendado es:

```text
Fuente externa
      ↓
Scraper / Extractor
      ↓
Validación
      ↓
Backend
      ↓
PostgreSQL
      ↓
Consulta desde Frontend
```

De esta forma, la plataforma consulta principalmente información previamente almacenada y evita depender de una extracción web en tiempo real para cada búsqueda.

---

## 11. Alcance actual

El objetivo principal de Tour Search Platform es apoyar el proceso de revisión y gestión de fichas turísticas, reduciendo el trabajo manual necesario para recopilar y validar información proveniente de operadores turísticos.

La versión actual se concentra principalmente en:

- Extracción automática de información turística
- Importación desde documentos
- Almacenamiento estructurado
- Gestión de operadores y países
- Consulta y búsqueda de actividades
- Administración de la información
- Validación de campos relevantes

### Mejoras futuras

Se consideran como evoluciones futuras del proyecto:

- Gestión y validación automática de imágenes
- Ampliación de las reglas de extracción
- Nuevas integraciones con fuentes externas
- Mejoras adicionales de automatización y validación
- Ampliación de los mecanismos de monitoreo de información desactualizada

---

## Estado del proyecto

El proyecto se encuentra en desarrollo y validación.

Los componentes principales de backend, frontend, PostgreSQL, scraper web y extractor de documentos se encuentran integrados y funcionales.