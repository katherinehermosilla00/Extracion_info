# Tour Search Platform

Proyecto base:
- React
- Java 21 + Spring Boot
- PostgreSQL
- Python + FastAPI
- Búsqueda por texto, ubicación, categoría, fecha, edad y precio

## 1. PostgreSQL

```bash
docker compose up -d postgres
```

Base:docker compose ps
## 2. Backend Java

Requiere Java 21 y Maven.

```bash
cd backend
mvn spring-boot:run
```

API:
http://localhost:8080

Swagger:
http://localhost:8080/swagger-ui.html

## 3. Crear un tour

POST /api/tours

```json
{
  "name": "Trekking Parque Tayrona",
  "description": "Tour de trekking de día completo",
  "price": 45000,
  "currency": "COP",
  "duration": "8 horas",
  "minAge": 18,
  "maxAge": 60,
  "location": "Tayrona",
  "category": "Trekking",
  "sourceUrl": "https://ejemplo.com/tour"
}
```

## 4. Agregar disponibilidad

POST /api/tours/1/availability

```json
{
  "date": "2026-08-15",
  "available": true,
  "availableSlots": 10,
  "startTime": "08:00:00",
  "endTime": "16:00:00"
}
```

## 5. Buscar

GET /api/tours/search?query=trekking&location=Tayrona&age=25&dateFrom=2026-08-15&dateTo=2026-08-18

## 6. Scraper Python

```bash
cd scraper
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Luego:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Swagger de Python:
http://localhost:8000/docs

## 7. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:
http://localhost:5173

## Importante

El scraper incluido es genérico. Debes reemplazar esa lógica por el scraping real que ya tienes.

No se recomienda ejecutar scraping en cada búsqueda del usuario. La idea es que Python actualice datos y Java consulte PostgreSQL.
