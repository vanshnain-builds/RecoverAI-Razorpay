-- ============================================================================
-- RecoverAI — Supabase / PostgreSQL schema
-- ============================================================================
-- The prototype runs fully IN-MEMORY (see backend/app/engine.py) so the demo is
-- reproducible with no external services. This file is for when you want to
-- PERSIST data. Run it in the Supabase SQL Editor (or `psql`) to create the
-- tables that mirror the shapes in backend/app/models.py and BLUEPRINT.md.
--
-- Safe to re-run: it drops and recreates the RecoverAI objects.
--
-- How the backend writes here: backend/app/store.py performs write-through via
-- the Supabase PostgREST REST API (POST /rest/v1/<table>) using the service-role
-- key — no native Postgres driver needed. `customers` and `payments` are UPSERTED
-- on their primary keys (on_conflict=customer_id / payment_id); the reasoning and
-- audit tables are inserted. Persistence turns on only when SUPABASE_URL and
-- SUPABASE_SERVICE_KEY are set in backend/.env — otherwise the app stays in-memory.
-- The service key bypasses RLS, so no policies are required for the backend to write.
-- ============================================================================

-- ---------- Enums -----------------------------------------------------------
drop type if exists payment_status      cascade;
drop type if exists failure_category    cascade;
drop type if exists action_type         cascade;

create type payment_status   as enum ('success','failed','recovered','escalated','abandoned','pending');
create type failure_category as enum ('temporary_failure','customer_action','payment_method_issue','subscription_failure','high_risk','unknown');
create type action_type      as enum ('retry_payment','send_payment_link','suggest_alternate_method','send_reminder','offer_incentive','escalate_to_human','stop_recovery');

-- ---------- Tables ----------------------------------------------------------
drop table if exists audit_log          cascade;
drop table if exists outcomes           cascade;
drop table if exists policy_evaluations cascade;
drop table if exists decisions          cascade;
drop table if exists diagnoses          cascade;
drop table if exists payments           cascade;
drop table if exists customers          cascade;

create table customers (
    customer_id         text primary key,
    previous_successes  int   not null default 0,
    previous_failures   int   not null default 0,
    preferred_method    text,
    base_risk           numeric(4,3) not null default 0,   -- 0..1
    created_at          timestamptz not null default now()
);

create table payments (
    payment_id                 text primary key,
    customer_id                text references customers(customer_id),
    amount                     numeric(12,2) not null,
    currency                   text not null default 'INR',
    ts                         timestamptz not null,          -- attempt time
    payment_method             text not null,                 -- upi/card/netbanking/wallet
    status                     payment_status not null,
    failure_code               text,
    device                     text,                          -- android/ios/web
    retry_count                int  not null default 0,
    reminder_count             int  not null default 0,
    first_failure_ts           timestamptz,
    hours_since_first_failure  numeric(8,2) not null default 0,
    subscription_id            text,
    days_overdue               int  not null default 0,
    risk_score                 numeric(4,3) not null default 0,  -- 0..1
    created_at                 timestamptz not null default now()
);

create table diagnoses (
    id            bigint generated always as identity primary key,
    payment_id    text not null references payments(payment_id) on delete cascade,
    category      failure_category not null,
    human_reason  text not null,
    confidence    numeric(4,3) not null,                       -- 0..1
    evidence      jsonb not null default '[]',                 -- [{text, supports_recovery}]
    source        text not null default 'simulated',           -- 'simulated' | 'llm'
    created_at    timestamptz not null default now()
);

create table decisions (
    id                       bigint generated always as identity primary key,
    payment_id               text not null references payments(payment_id) on delete cascade,
    action                   action_type not null,
    recovery_probability     numeric(4,3) not null,            -- 0..1
    expected_recovery_value  numeric(12,2) not null,
    recovery_priority        numeric(12,2) not null,
    rationale                jsonb not null default '[]',      -- [string]
    source                   text not null default 'simulated',
    created_at               timestamptz not null default now()
);

create table policy_evaluations (
    id                       bigint generated always as identity primary key,
    payment_id               text not null references payments(payment_id) on delete cascade,
    allowed                  boolean not null,
    requires_human_approval  boolean not null default false,
    terminal_action          action_type,                      -- null = none
    checks                   jsonb not null default '[]',      -- [{name, passed, detail}]
    created_at               timestamptz not null default now()
);

create table outcomes (
    id               bigint generated always as identity primary key,
    payment_id       text not null references payments(payment_id) on delete cascade,
    action           action_type not null,
    executed         boolean not null,
    success          boolean not null,
    recovered_amount numeric(12,2) not null default 0,
    message          text,
    failure_reason   text,
    created_at       timestamptz not null default now()
);

create table audit_log (
    id          bigint generated always as identity primary key,
    ts          timestamptz not null default now(),
    payment_id  text references payments(payment_id) on delete cascade,
    stage       text not null,        -- detect|diagnose|decide|policy|execute|recover_success|recover_fail
    message     text not null
);

-- ---------- Indexes ---------------------------------------------------------
create index idx_payments_status        on payments(status);
create index idx_payments_customer      on payments(customer_id);
create index idx_diagnoses_payment      on diagnoses(payment_id);
create index idx_decisions_payment      on decisions(payment_id);
create index idx_decisions_priority     on decisions(recovery_priority desc);
create index idx_outcomes_payment       on outcomes(payment_id);
create index idx_audit_payment          on audit_log(payment_id);
create index idx_audit_ts               on audit_log(ts desc);

-- ---------- Convenience view: latest state per payment ----------------------
create or replace view recovery_records as
select
    p.*,
    d.category      as diagnosis_category,
    d.confidence    as diagnosis_confidence,
    dec.action      as decided_action,
    dec.recovery_probability,
    dec.expected_recovery_value,
    dec.recovery_priority,
    o.success       as recovery_success,
    o.recovered_amount
from payments p
left join lateral (select * from diagnoses  x where x.payment_id = p.payment_id order by created_at desc limit 1) d   on true
left join lateral (select * from decisions  x where x.payment_id = p.payment_id order by created_at desc limit 1) dec on true
left join lateral (select * from outcomes   x where x.payment_id = p.payment_id order by created_at desc limit 1) o   on true;

-- ---------- Headline metrics (mirrors engine.metrics()) ---------------------
create or replace view recovery_metrics as
select
    coalesce(sum(amount) filter (where status in ('failed','recovered')), 0)            as revenue_at_risk,
    coalesce(sum(recovered_amount) filter (where recovery_success), 0)                  as recovered_amount,
    count(*)      filter (where status in ('failed','recovered'))                       as failed_count,
    count(*)      filter (where recovery_success)                                       as recovered_count
from recovery_records;

-- ---------------------------------------------------------------------------
-- Row Level Security (Supabase enables RLS via the dashboard for new tables).
-- These tables are created via SQL, so RLS is OFF by default. For a server-side
-- backend using the service_role key, that's fine. If you expose them to the
-- anon/public API, enable RLS and add policies, e.g.:
--
--   alter table payments enable row level security;
--   create policy "service role full access" on payments
--     for all to service_role using (true) with check (true);
-- ---------------------------------------------------------------------------
