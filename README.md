# AutoShare Backend

Backend de alquiler de vehiculos estilo Airbnb construido con Flask y Supabase.

## Requisitos

- Python 3.11 o superior
- Cuenta y proyecto configurado en Supabase
- pip (o pipenv/poetry si prefieres otro gestor)

## Configuracion

1. Crea y activa un entorno virtual de Python.
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Crea un archivo `.env` en la raiz copiando `.env.example` y completa las variables (usa la Service Role Key para operaciones de escritura si la necesitas).
   - `SUPABASE_DB_URL` ya apunta a la base academica compartida.
   - Define `JWT_SECRET` para firmar los tokens (en desarrollo puedes dejar el valor por defecto, pero en produccion debe ser un secreto robusto y solo conocido por el backend).
4. Ejecuta los scripts de `migrations/` en tu instancia de Supabase (puedes usar la consola SQL o `psql`).
   - `001_create_users.sql`: crea la tabla `public.users`.
   - `002_add_role_to_users.sql`: agrega la columna `rol` y valida los roles permitidos.
   - `003_create_vehicles_and_reservations.sql`: crea `public.vehicles` y `public.reservations`, indices y datos de ejemplo.
   - `004_create_payments.sql`: crea `public.payments` y deja dos pagos de ejemplo enlazados a las reservas seed.

## Ejecucion de la app

```bash
flask --app wsgi --debug run
```

El blueprint principal expone los endpoints bajo `/api`.

## Endpoints disponibles

- `GET /api/health`: verifica el estado general del servicio y la configuracion de Supabase.
- `POST /api/auth/register`: registra un nuevo usuario (`nombre`, `email`, `password`, `rol` opcional) y devuelve la informacion del usuario junto con un `access_token` JWT.
- `POST /api/auth/login`: autentica a un usuario (email/contrasena) y entrega `access_token` + datos basicos.
- `GET /api/vehicles`: busca vehiculos con filtros opcionales (`ciudad`, `tipo`, `precio_min`, `precio_max`, `fecha_inicio`, `fecha_fin`, `limit`, `offset`). La respuesta incluye metadata `{items, total, limit, offset}`.
- `GET /api/vehicles/<vehicle_id>`: devuelve el detalle de un vehiculo especifico.
- `GET /api/reservations`: **requiere `Authorization: Bearer <token>`**. Devuelve las reservas del usuario autenticado con metadata de paginacion.
- `POST /api/reservations`: **requiere `Authorization: Bearer <token>`**. Crea una reserva (`vehicle_id`, `start_date`, `end_date`, `comentarios` opcional, `metodo_pago`, `card_last4`) y genera un pago asociado. Devuelve `{reserva, pago}`.
- `POST /api/reservations/<reserva_id>/cancel`: **requiere `Authorization: Bearer <token>`**. Cancela una reserva confirmada del usuario autenticado (o cualquiera si el rol es `administrador`) y marca el pago como reembolsado.

## Autenticacion con JWT

1. Registra o inicia sesion para obtener el `access_token`.
2. Incluye el token en los endpoints protegidos:
   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:5000/api/reservations
   ```
3. La firma usa HS256 con el secreto definido en `JWT_SECRET`. Los tokens expiran despues de `JWT_ACCESS_TOKEN_EXPIRES_MIN` minutos (60 por defecto).

## Roles soportados

- `cliente`: usuarios que reservan vehiculos.
- `anfitrion`: propietarios que publican vehiculos (por ahora comparten los mismos permisos que `cliente`).
- `administrador`: acceso completo, puede cancelar cualquier reserva.

## Datos de ejemplo

Usuarios:
```sql
insert into public.users (id, email, password_hash, nombre, rol) values
    ('16347695-1452-407d-9a8d-0ba0a44a8bd9', 'laura@example.com', 'scrypt:32768:8:1$Tj873LouzIVSy0Vn$4cab5a3163e69fedc74a162a171c698ebf428e59874e8544582bc300bdd29bd7540d083d74a88115afc4c90b28d5a1d0857406a812fd831da1dab7464597e6df', 'Laura Gomez', 'cliente'),
    ('f799e528-c155-4c18-9515-e7749fc0a136', 'carlos@example.com', 'scrypt:32768:8:1$ljbDIILfH8gusZnP$40d27995ee5058af99c2763605b2bc7b86abfbdfdad3ae832ffeb2e3f051b1426b5ed337f393e07bd5bdf10b8591707645bae20bb3f755c8613d2a1668732e57', 'Carlos Ruiz', 'anfitrion'),
    ('058b432a-9b65-4dfd-bda0-aa3cc9fc81da', 'mariana@example.com', 'scrypt:32768:8:1$7ZCoI7kGXJfPfXPb$1c2ed3844340ef459f40b9e63c1e6126b98a9e6098f77704db1dcd907e56f3d3cbe25897d0b18d97434bc43007011107d4711e20e17b0c643c2303e9a1467ae1', 'Mariana Torres', 'cliente')
on conflict (email) do nothing;
```

Vehiculos, reservas y pagos de ejemplo (ver migraciones 003 y 004) para contar con datos consistentes en todas las tablas.

Las contrasenas plano asociadas a los usuarios de ejemplo son `ContrasenaSegura1`, `ContrasenaSegura2` y `ContrasenaSegura3` respectivamente.

## Tests

```bash
pytest
```

## Estructura

- `app/`: codigo de la aplicacion y blueprints.
- `app/security.py`: utilidades para firmar/verificar tokens JWT.
- `app/api/`: endpoints HTTP (auth, vehicles, reservations).
- `app/services/` y `app/repositories/`: capas de dominio listas para implementar historias.
- `tests/`: pruebas unitarias y de integracion.
- `migrations/`: scripts SQL para crear y actualizar el esquema en Supabase.

## Proximos pasos

- Implementar autorizacion granular por rol (endpoints exclusivos para anfitriones/administradores).
- Añadir el flujo de publicacion/edicion de vehiculos por anfitriones.
- Extender el ciclo de vida de reservas (completada, evaluacion, pagos reales, etc.).
- Configurar politicas RLS en Supabase y pipeline de despliegue.
