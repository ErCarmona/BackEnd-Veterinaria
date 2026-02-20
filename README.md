# Clínica Veterinaria

Aplicación sencilla para gestionar mascotas, dueños y citas veterinarias.

---

## ¿Qué hay en cada carpeta?

```
vetclinic/
│
├── backend/
│   ├── main.py          ← El servidor (FastAPI). Aquí están todos los endpoints.
│   ├── requirements.txt ← Las librerías que necesita el servidor.
│   └── Dockerfile       ← Cómo construir el contenedor del servidor.
│
├── frontend/
│   └── index.html       ← La interfaz visual. Un solo archivo HTML/CSS/JS.
│
├── docker-compose.yml   ← Levanta todo con un solo comando.
└── README.md            ← Este archivo.
```

---

## Cómo arrancarlo

### Opción 1: Con Docker (la más fácil)

Solo necesitas tener Docker instalado. Luego ejecuta:

```bash
docker compose up --build
```

Espera unos segundos y abre tu navegador:

| Qué            | URL                          |
|----------------|------------------------------|
| **Frontend**   | http://localhost:3000        |
| **API Docs**   | http://localhost:8000/docs   |
| **Backend**    | http://localhost:8000        |

---

### Opción 2: Sin Docker (manual)

**Paso 1: Arrancar PostgreSQL**
```bash
docker run -d \
  --name vet-db \
  -e POSTGRES_DB=vetclinic \
  -e POSTGRES_USER=vetuser \
  -e POSTGRES_PASSWORD=vetpass \
  -p 5432:5432 \
  postgres:16-alpine
```

**Paso 2: Instalar dependencias del backend**
```bash
cd backend
pip install -r requirements.txt
```

**Paso 3: Arrancar el servidor**
```bash
uvicorn main:app --reload --port 8000
```

---

## ¿Qué es JSONB y para qué sirve aquí?

JSONB es un tipo de campo de PostgreSQL que guarda datos en formato JSON.
A diferencia de una columna normal (que solo guarda un dato), JSONB puede guardar
cualquier estructura de datos.

**En esta app se usa en 3 sitios:**

### 1. `duenos.info_contacto`
Guarda datos de contacto extra del dueño:
```json
{
  "contacto_preferido": "whatsapp",
  "telefono_emergencia": "600 999 888",
  "notas": "Llamar solo por la mañana"
}
```

### 2. `mascotas.info_medica`
Guarda la información médica de la mascota:
```json
{
  "alergias": ["penicilina", "ácaros"],
  "condiciones": ["diabetes tipo 1"],
  "microchip": "985112345678901",
  "esterilizado": true
}
```

### 3. `citas.datos_cita`
Guarda los detalles de cada consulta:
```json
{
  "sintomas": ["fiebre", "vómitos"],
  "veterinario": "Dr. López",
  "coste": 45.00,
  "pago": "pagado",
  "requiere_seguimiento": true
}
```

**¿Por qué es útil?**
- No necesitas crear una columna nueva por cada dato extra.
- Puedes buscar dentro del JSON con SQL.
- La estructura puede variar entre registros.

---

## Endpoints de la API

Una vez arrancado el servidor, puedes ver toda la documentación interactiva en:
**http://localhost:8000/docs**

### Resumen rápido:

| Método | URL                        | ¿Qué hace?                        |
|--------|----------------------------|-----------------------------------|
| GET    | /duenos                    | Ver todos los dueños              |
| POST   | /duenos                    | Crear un dueño                    |
| GET    | /duenos/{id}               | Ver un dueño con sus mascotas     |
| DELETE | /duenos/{id}               | Borrar un dueño                   |
| GET    | /mascotas                  | Ver todas las mascotas            |
| POST   | /mascotas                  | Registrar una mascota             |
| GET    | /mascotas/{id}             | Ver una mascota con sus citas     |
| PATCH  | /mascotas/{id}             | Actualizar datos de una mascota   |
| DELETE | /mascotas/{id}             | Borrar una mascota                |
| GET    | /citas                     | Ver todas las citas               |
| GET    | /citas/hoy                 | Ver las citas de hoy              |
| POST   | /citas                     | Crear una cita                    |
| PATCH  | /citas/{id}/estado         | Cambiar el estado de una cita     |
| DELETE | /citas/{id}                | Borrar una cita                   |
| GET    | /estadisticas              | Números para el dashboard         |

---

## Ejemplos de consultas JSONB en PostgreSQL

Si quieres consultar los datos JSONB directamente en la base de datos:

```sql
-- Mascotas que tienen alergia a la penicilina
SELECT nombre FROM mascotas
WHERE info_medica->'alergias' ? 'penicilina';

-- Mascotas con microchip
SELECT nombre FROM mascotas
WHERE info_medica->>'microchip' IS NOT NULL;

-- Citas pagadas
SELECT * FROM citas
WHERE datos_cita->>'pago' = 'pagado';

-- Citas con coste mayor de 50€
SELECT * FROM citas
WHERE (datos_cita->>'coste')::numeric > 50;
```
