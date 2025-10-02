-- 001_create_users.sql
-- Script inicial para crear la tabla de usuarios del sistema de alquiler.

create extension if not exists pgcrypto;

create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    password_hash text not null,
    nombre text,
    created_at timestamptz not null default timezone('utc', now())
);

comment on table public.users is 'Usuarios registrados en la plataforma AutoShare.';
comment on column public.users.email is 'Correo electronico unico utilizado para autenticacion.';
comment on column public.users.password_hash is 'Hash de la contrasena utilizando werkzeug.security.';
comment on column public.users.nombre is 'Nombre mostrado para el usuario.';
comment on column public.users.created_at is 'Fecha de creacion del registro (UTC).';
