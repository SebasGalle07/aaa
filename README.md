# AutoShare

Aplicacion estilo Airbnb para alquiler de vehiculos. Incluye backend Flask + Supabase y frontend Angular.

## Requisitos

- Python 3.11+
- Node.js 18+
- Cuenta Supabase con el esquema de `migrations/`

## Backend

### Configuracion local

1. Crear y activar entorno virtual:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Copiar `.env.example` a `.env` y completar credenciales (`SUPABASE_*`, `JWT_SECRET`, etc.).
4. Ejecutar los scripts de `migrations/` en la base Supabase (`001` a `005`).
5. Iniciar la API:
   ```bash
   flask --app wsgi --debug run
   ```

### Endpoints principales

- `POST /api/auth/register` / `POST /api/auth/login`
- `GET /api/vehicles` y `GET /api/vehicles/<id>`
- `POST /api/vehicles` **(admin)**: alta de vehiculos con multipart/form-data.
- `GET /api/admin/vehicles` y `GET /api/admin/vehicles/<id>` **(admin)**.
- `PATCH /api/vehicles/<id>/status` **(admin)**: publica o pausa un vehiculo.
- `GET /api/reservations`
- `POST /api/reservations`
- `POST /api/reservations/<id>/cancel`

Todas las rutas protegidas requieren encabezado `Authorization: Bearer <token>`.

### Registro de vehiculos

- Obligatorios: `license_plate`, `make`, `model`, `vehicle_type`, `year >= VEHICLE_MIN_YEAR`, `price_per_day`, `location`, `images` (JPG/PNG <= 3MB).
- Estado inicial `INACTIVO` hasta validacion manual (`PATCH /api/vehicles/<id>/status`).
- Auditoria: `created_by`, `validated_by`, `validated_at`.
- Vehiculos inactivos no aparecen en el catalogo ni bloquean disponibilidad.

### Tests backend

```bash
pytest
```

## Frontend Angular

### Desarrollo

```bash
cd front
npm install
npm start
```

Rutas principales:

- `/home`, `/buscar`, `/reservar/:id` para clientes.
- `/admin/vehicles` y `/admin/vehicles/nuevo` para administradores (detectado por rol en el JWT).

El formulario de alta valida formato de placa, rango de ano, tipo/peso de imagenes y muestra previsualizaciones.

### Build de produccion

```bash
npm run build
```

Salida: `front/dist/frontend`.

## Datos seed

`migrations/003_create_vehicles_and_reservations.sql` y `004_create_payments.sql` incluyen vehiculos, reservas y pagos de ejemplo. Las contrasenas planas demo son `ContrasenaSegura1/2/3`.

## Despliegue en Render

`render.yaml` define dos servicios:

1. **autoshare-backend** (web Python)
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`
   - Completar en el panel las variables `SUPABASE_*`, `JWT_SECRET`, `VEHICLE_IMAGE_BUCKET`, etc.
2. **autoshare-frontend** (static)
   - Root: `front`
   - Build: `npm install && npm run build`
   - Publish: `dist/frontend`

Para que la SPA enrute `/api/*` hacia el backend se usa `front/static.json`. Sustituye `YOUR-BACKEND-SERVICE.onrender.com` por la URL real del servicio Flask tras el primer despliegue.

## Variables de entorno destacadas

- `VEHICLE_MIN_YEAR` (default 2015)
- `VEHICLE_IMAGE_MAX_MB` (default 3)
- `VEHICLE_IMAGE_BUCKET`
- `VEHICLE_DEFAULT_CURRENCY`

## Notas

- Las imagenes se almacenan en el bucket de Supabase Storage indicado.
- El servicio de reservas ignora reservas canceladas al validar disponibilidad.
- Hay pruebas unitarias para reservas y validaciones de vehiculos/imagenes.

