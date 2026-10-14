-- Additive PostgreSQL foundation for Modules 1 and 5.
-- Run through the project's migration tool after DATABASE_URL and tenant auth
-- are configured. This file does not modify existing prototype tables.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS legaltech_precedent_documents (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    source_uri varchar(2048),
    title varchar(500) NOT NULL,
    citation varchar(500),
    court varchar(200),
    case_type varchar(100),
    decision_year integer,
    content_hash varchar(64) NOT NULL UNIQUE,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_legaltech_precedent_documents_org
    ON legaltech_precedent_documents (organization_id);

CREATE TABLE IF NOT EXISTS legaltech_precedent_chunks (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    document_id uuid NOT NULL REFERENCES legaltech_precedent_documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    page_number integer,
    paragraph_number integer,
    embedding vector(1536) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_legaltech_precedent_chunks_org_document
    ON legaltech_precedent_chunks (organization_id, document_id);

CREATE TABLE IF NOT EXISTS legaltech_time_entries (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    matter_id uuid NOT NULL,
    user_id uuid NOT NULL,
    work_date date NOT NULL,
    duration_minutes integer NOT NULL CHECK (duration_minutes >= 0),
    rate numeric(12,2) NOT NULL CHECK (rate >= 0),
    description text NOT NULL,
    billed_status varchar(30) NOT NULL DEFAULT 'unbilled',
    invoice_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_legaltech_time_entries_org_matter
    ON legaltech_time_entries (organization_id, matter_id, billed_status);

CREATE TABLE IF NOT EXISTS legaltech_invoices (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    matter_id uuid NOT NULL,
    created_by uuid NOT NULL,
    currency varchar(3) NOT NULL DEFAULT 'INR',
    status varchar(30) NOT NULL DEFAULT 'draft',
    subtotal numeric(12,2) NOT NULL DEFAULT 0,
    tax numeric(12,2) NOT NULL DEFAULT 0,
    total numeric(12,2) NOT NULL DEFAULT 0,
    provider varchar(30),
    provider_invoice_id varchar(200),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_legaltech_invoices_org_matter
    ON legaltech_invoices (organization_id, matter_id);

CREATE TABLE IF NOT EXISTS legaltech_invoice_lines (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    invoice_id uuid NOT NULL REFERENCES legaltech_invoices(id) ON DELETE CASCADE,
    time_entry_id uuid,
    description text NOT NULL,
    duration_minutes integer NOT NULL CHECK (duration_minutes >= 0),
    rate numeric(12,2) NOT NULL CHECK (rate >= 0),
    amount numeric(12,2) NOT NULL CHECK (amount >= 0)
);
