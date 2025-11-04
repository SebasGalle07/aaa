-- 005_update_vehicle_registration.sql
-- Ajustes para soportar el flujo de registro y validación de vehículos.

alter table if exists public.vehicles
    add column if not exists license_plate text,
    add column if not exists status text not null default 'inactivo',
    add column if not exists created_by uuid references public.users(id) on delete set null,
    add column if not exists validated_by uuid references public.users(id) on delete set null,
    add column if not exists validated_at timestamptz,
    add column if not exists images jsonb not null default '[]'::jsonb;

update public.vehicles
set license_plate = concat('TEMP-', substr(id::text, 1, 8))
where license_plate is null or trim(license_plate) = '';

update public.vehicles
set created_by = coalesce(created_by, owner_id);

update public.vehicles
set status = coalesce(nullif(trim(status), ''), 'inactivo');

-- Establecer datos conocidos para los vehículos de ejemplo.
update public.vehicles
set license_plate = 'ABC123',
    status = 'activo'
where id = '11111111-2222-4333-8444-555555555555';

update public.vehicles
set license_plate = 'XYZ987',
    status = 'activo'
where id = '22222222-3333-4444-8555-666666666666';

update public.vehicles
set license_plate = 'LMN456',
    status = 'activo'
where id = '33333333-4444-5555-8666-777777777777';

alter table public.vehicles
    alter column license_plate set not null;

create unique index if not exists vehicles_license_plate_uidx on public.vehicles (upper(license_plate));

alter table public.vehicles
    add constraint vehicles_status_check check (status in ('activo', 'inactivo'));

comment on column public.vehicles.license_plate is 'Placa única del vehículo.';
comment on column public.vehicles.status is 'Estado de publicación del vehículo (activo/inactivo).';
comment on column public.vehicles.created_by is 'Usuario que registró originalmente el vehículo.';
comment on column public.vehicles.validated_by is 'Administrador que validó el vehículo.';
comment on column public.vehicles.validated_at is 'Fecha de validación por parte del administrador.';
comment on column public.vehicles.images is 'Listado de recursos multimedia asociados al vehículo.';
