-- 002_add_role_to_users.sql
-- Agrega la columna "rol" a la tabla de usuarios y asegura valores validos.

alter table public.users
    add column if not exists rol text;

update public.users
    set rol = coalesce(rol, 'cliente');

alter table public.users
    alter column rol set not null,
    alter column rol set default 'cliente';

-- Restringir los valores permitidos para el rol
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.users'::regclass
          AND conname = 'users_rol_check'
    ) THEN
        ALTER TABLE public.users
            ADD CONSTRAINT users_rol_check CHECK (rol IN ('cliente', 'anfitrion', 'administrador'));
    END IF;
END $$;

comment on column public.users.rol is 'Rol asignado al usuario: cliente, anfitrion o administrador.';
