-- Run this in the Supabase SQL editor to set up the licensing schema.

create extension if not exists pgcrypto;

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    iq_email text unique not null,
    created_at timestamptz not null default now()
);

create table if not exists licenses (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    status text not null default 'inactive' check (status in ('active', 'inactive')),
    plan text,
    expires_at timestamptz,
    activated_at timestamptz,
    device_id text,
    last_seen_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists idx_licenses_user_id on licenses(user_id);

create table if not exists admins (
    id uuid primary key default gen_random_uuid(),
    email text unique not null,
    password_hash text not null,
    created_at timestamptz not null default now()
);
