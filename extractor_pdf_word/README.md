# Extractor de actividades desde PDF/Word

Este módulo permite extraer información de actividades turísticas desde documentos PDF y Word y almacenarla en el backend de Tour Search Platform.

El extractor procesa las carpetas de los operadores turísticos, identifica información estructurada de las actividades y permite crear o actualizar los registros correspondientes en PostgreSQL mediante la API del backend.

## 1. Instalar dependencias

Desde la carpeta `extractor_pdf_word`:

```powershell
pip install pdfplumber python-docx requests
```

## 2. Configurar operadores

El archivo `operadores.json` relaciona el nombre de la carpeta de cada operador turístico con su ID correspondiente en el backend.

Ejemplo:

```json
{
  "Parque Tepuhueico": 1,
  "Gigi's Tours": 2
}
```

Los nombres deben coincidir con las carpetas utilizadas para almacenar la información de cada operador.

Los IDs deben corresponder a los operadores registrados en la plataforma.

## 3. Probar en modo simulación

Antes de modificar información en la base de datos se recomienda utilizar `--dry-run`.

```powershell
python extraer_actividades.py --raiz "C:\ruta\a\la\carpeta" --dry-run
```

Este modo permite revisar la información detectada sin crear ni actualizar registros en el backend.

## 4. Ejecutar la importación

Con el backend iniciado:

```powershell
python extraer_actividades.py --raiz "C:\ruta\a\la\carpeta" --backend "http://localhost:8080/api/actividades" --mapeo operadores.json
```

El backend utiliza normalmente:

```text
http://localhost:8080
```

## 5. Procesar una actividad específica

Para realizar pruebas sin procesar todas las actividades se puede utilizar:

```powershell
python extraer_actividades.py --raiz "C:\ruta\a\la\carpeta" --solo-actividad "Nombre de la actividad"
```

También puede combinarse con el modo de simulación:

```powershell
python extraer_actividades.py --raiz "C:\ruta\a\la\carpeta" --solo-actividad "Nombre de la actividad" --dry-run
```

## 6. Procesar un operador específico

También es posible limitar la ejecución a un operador turístico:

```powershell
python extraer_actividades.py --raiz "C:\ruta\a\la\carpeta" --solo-operador "Nombre del operador"
```

Esto permite realizar pruebas y actualizaciones de manera controlada sin procesar toda la información disponible.

## Información extraída

Dependiendo del contenido disponible en cada documento, el extractor puede identificar:

- Nombre de la actividad
- Descripción
- Destino
- Duración
- Edad mínima
- Edad máxima
- Idiomas
- Highlights
- Itinerario
- Horarios
- Restricciones

No todos los documentos contienen todos los campos, por lo que algunos pueden permanecer vacíos cuando la información no está disponible.

## Funcionamiento

El extractor:

1. Recorre las carpetas de operadores y actividades.
2. Busca documentos PDF y DOCX.
3. Extrae el contenido disponible.
4. Identifica las diferentes secciones del documento.
5. Convierte la información encontrada a la estructura utilizada por `Actividad`.
6. Comprueba los registros correspondientes en el backend.
7. Crea o actualiza las actividades según corresponda.
8. Mantiene la relación entre la actividad y su operador turístico.

El extractor utiliza encabezados y estructura textual para reconocer secciones como highlights, itinerarios, horarios y restricciones.

## Actualización de actividades

Cuando una actividad ya existe, el extractor puede actualizar su información conservando la relación con el operador turístico existente.

Esto permite volver a ejecutar el proceso sobre información previamente importada sin tener que crear manualmente una nueva actividad.

## Archivos soportados

Actualmente se procesan:

```text
.pdf
.docx
```

Los documentos antiguos `.doc` no se procesan directamente.

## Fuente de información

Cuando una actividad proviene de un documento local, el sistema mantiene una referencia de origen para poder identificar que la información fue importada desde archivos.

En el frontend estas actividades pueden visualizarse como:

```text
Documento importado localmente
```

## Campos fuera del alcance actual

En la versión actual no se consideran como requisitos de validación:

- Imágenes
- Precio o tarifa rack

Estos elementos pueden incorporarse como mejoras futuras del proyecto.

## Recomendaciones

Antes de una importación completa:

1. Iniciar PostgreSQL.
2. Iniciar el backend.
3. Ejecutar primero con `--dry-run`.
4. Revisar los resultados.
5. Probar una actividad u operador específico si es necesario.
6. Ejecutar finalmente la importación completa.

## Estado actual

El extractor se encuentra integrado con el backend de Tour Search Platform y ha sido utilizado para procesar y actualizar actividades provenientes de documentos PDF y Word.