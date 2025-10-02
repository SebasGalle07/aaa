-- 003_create_vehicles_and_reservations.sql
-- Crea las tablas de vehiculos y reservas con datos de ejemplo.

create table if not exists public.vehicles (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid references public.users(id) on delete set null,
    make text not null,
    model text not null,
    year integer not null,
    vehicle_type text not null,
    price_per_day numeric(10,2) not null,
    currency text not null default 'USD',
    description text,
    location text,
    capacity integer,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists vehicles_location_idx on public.vehicles using gin (to_tsvector('spanish', coalesce(location, '')));
create index if not exists vehicles_vehicle_type_idx on public.vehicles (vehicle_type);
create index if not exists vehicles_price_idx on public.vehicles (price_per_day);

create table if not exists public.reservations (
    id uuid primary key default gen_random_uuid(),
    vehicle_id uuid not null references public.vehicles(id) on delete cascade,
    user_id uuid references public.users(id) on delete set null,
    start_date date not null,
    end_date date not null,
    status text not null default 'confirmada',
    comentarios text,
    created_at timestamptz not null default timezone('utc', now()),
    constraint reservations_date_check check (end_date >= start_date)
);

alter table public.reservations
    add column if not exists comentarios text;

comment on table public.vehicles is 'Vehiculos disponibles para alquiler en AutoShare.';
comment on column public.vehicles.vehicle_type is 'Categoria del vehiculo (sedan, suv, pickup, etc.).';
comment on column public.vehicles.location is 'Ciudad o zona donde se encuentra el vehiculo.';
comment on table public.reservations is 'Reservas de vehiculos efectuadas por los usuarios.';
comment on column public.reservations.comentarios is 'Notas opcionales agregadas por el usuario al crear la reserva.';

-- Datos de ejemplo (asegurate de que los usuarios de referencia existan)
insert into public.vehicles (id, owner_id, make, model, year, vehicle_type, price_per_day, currency, description, location, capacity)
values
    ('11111111-2222-4333-8444-555555555555', 'f799e528-c155-4c18-9515-e7749fc0a136', 'Toyota', 'RAV4', 2022, 'suv', 120.00, 'USD', 'SUV espaciosa con transmision automatica.', 'Bogota', 5),
    ('22222222-3333-4444-8555-666666666666', '058b432a-9b65-4dfd-bda0-aa3cc9fc81da', 'Chevrolet', 'Onix', 2021, 'sedan', 55.00, 'USD', 'Sedan compacto ideal para ciudad.', 'Medellin', 5),
    ('33333333-4444-5555-8666-777777777777', '16347695-1452-407d-9a8d-0ba0a44a8bd9', 'Ford', 'Ranger', 2023, 'pickup', 150.00, 'USD', 'Pickup 4x4 perfecta para viajes largos.', 'Cartagena', 5)
on conflict (id) do nothing;

insert into public.reservations (id, vehicle_id, user_id, start_date, end_date, status, comentarios)
values
    ('aaaa1111-bbbb-2222-cccc-333333333333', '11111111-2222-4333-8444-555555555555', '16347695-1452-407d-9a8d-0ba0a44a8bd9', date '2025-10-12', date '2025-10-15', 'confirmada', 'Retiro en el aeropuerto.'),
    ('bbbb2222-cccc-3333-dddd-444444444444', '22222222-3333-4444-8555-666666666666', 'f799e528-c155-4c18-9515-e7749fc0a136', date '2025-10-20', date '2025-10-22', 'confirmada', null)
on conflict (id) do nothing;

create index if not exists reservations_user_idx on public.reservations (user_id);
create index if not exists reservations_vehicle_idx on public.reservations (vehicle_id);
create index if not exists reservations_vehicle_dates_idx on public.reservations (vehicle_id, start_date, end_date);

-- Datos adicionales de ejemplo
a
insert into public.reservations (id, vehicle_id, user_id, start_date, end_date, status, comentarios)
values
    ('cccc3333-dddd-4444-eeee-555555555555', '33333333-4444-5555-8666-777777777777', 'f799e528-c155-4c18-9515-e7749fc0a136', date '2025-11-01', date '2025-11-05', 'confirmada', 'Visita familiar')
on conflict (id) do nothing;
