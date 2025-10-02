# Endpoints disponibles

| Metodo | Ruta | Autenticacion | Roles permitidos | Descripcion |
| --- | --- | --- | --- | --- |
| GET | /api/health | No | - | Estado general del servicio y Supabase |
| POST | /api/auth/register | No | - | Registra usuario y devuelve token de acceso |
| POST | /api/auth/login | No | - | Autentica usuario y devuelve token de acceso |
| GET | /api/vehicles | No | - | Busca vehiculos con filtros y paginacion |
| GET | /api/vehicles/{id} | No | - | Detalle de vehiculo |
| GET | /api/reservations | Si | cliente, anfitrion, administrador | Lista reservas del usuario autenticado |
| POST | /api/reservations | Si | cliente, administrador | Crea una nueva reserva y genera pago |
| POST | /api/reservations/{id}/cancel | Si | cliente (propia), administrador (cualquiera) | Cancela reserva confirmada y marca pago como reembolsado |

## Filtros y parametros

- **/api/vehicles** admite `ciudad`, `tipo`, `precio_min`, `precio_max`, `fecha_inicio`, `fecha_fin`, `limit`, `offset`.
- **/api/reservations** admite `limit` y `offset`.
- **POST /api/reservations** requiere JSON:
  ```json
  {
    "vehicle_id": "uuid",
    "start_date": "AAAA-MM-DD",
    "end_date": "AAAA-MM-DD",
    "comentarios": "opcional",
    "metodo_pago": "tarjeta",  
    "card_last4": "4242"
  }
  ```

## Respuestas principales

- **/api/vehicles**: 
  ```json
  {
    "items": [ {"id": "...", "make": "Toyota", ...} ],
    "total": 3,
    "limit": 20,
    "offset": 0
  }
  ```
- **POST /api/reservations**: 
  ```json
  {
    "reserva": {"id": "...", "status": "confirmada", ...},
    "pago": {"id": "...", "status": "pagado", "amount": "360.00", ...}
  }
  ```

Para ejemplos completos y secuencia de pruebas ver `postman_collection.json`.
