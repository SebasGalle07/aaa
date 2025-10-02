-- 004_create_payments.sql
-- Crea la tabla de pagos asociados a las reservas.

create table if not exists public.payments (
    id uuid primary key default gen_random_uuid(),
    reservation_id uuid not null references public.reservations(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete set null,
    amount numeric(12,2) not null,
    currency text not null,
    status text not null default 'pagado',
    provider text not null,
    reference text not null,
    card_last4 text,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists payments_reservation_idx on public.payments (reservation_id);
create index if not exists payments_user_idx on public.payments (user_id);

comment on table public.payments is 'Pagos registrados para cada reserva.';
comment on column public.payments.status is 'Estado del pago: pagado, reembolsado, fallido, etc.';
comment on column public.payments.provider is 'Metodo o pasarela utilizada (tarjeta, pse, etc.).';
comment on column public.payments.reference is 'Identificador de la transaccion en la pasarela simulada.';

-- Datos de ejemplo opcionales
insert into public.payments (id, reservation_id, user_id, amount, currency, status, provider, reference, card_last4)
values
    ('dddd1111-eeee-2222-ffff-666666666666', 'aaaa1111-bbbb-2222-cccc-333333333333', '16347695-1452-407d-9a8d-0ba0a44a8bd9', 360.00, 'USD', 'pagado', 'tarjeta', 'PAY-EXAMPLE1', '4242'),
    ('eeee2222-ffff-3333-aaaa-777777777777', 'bbbb2222-cccc-3333-dddd-444444444444', 'f799e528-c155-4c18-9515-e7749fc0a136', 110.00, 'USD', 'pagado', 'tarjeta', 'PAY-EXAMPLE2', '9999')
on conflict (id) do nothing;
