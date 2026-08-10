--
-- automation_central: create an empty database with the current schema shape.
--
-- Generated from the live automation_central schema (PostgreSQL 16.2).
-- This script creates structure only (tables, identities/sequences, indexes,
-- foreign keys) plus the run_type lookup rows the framework expects. No test
-- result data is included.
--
-- Usage:
--   createdb -O automation_user automation_central
--   psql -v ON_ERROR_STOP=1 -d automation_central -f create_automation_central_schema.sql
--
-- Notes:
--   * Run as a superuser (or as automation_user with rights to create the
--     uuid-ossp extension).
--   * Every object is owned by automation_user; adjust the role name at the
--     bottom of this file if your deployment uses a different one.
--

SET client_encoding = 'UTF8';
SET standard_conforming_strings = 'on';
SET search_path = public, pg_catalog;

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------

-- Required by test_session.id DEFAULT uuid_generate_v4().
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;

-- ---------------------------------------------------------------------------
-- Sequences for the serial-style columns
-- (identity columns declare their own sequences inline, further down)
-- ---------------------------------------------------------------------------

CREATE SEQUENCE public.django_migrations_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

CREATE SEQUENCE public.kpi_id_seq
    AS bigint START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

CREATE SEQUENCE public.kpi_measure_id_seq
    AS bigint START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

CREATE SEQUENCE public.tempest_run_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

CREATE SEQUENCE public.tempest_test_result_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- ---------------------------------------------------------------------------
-- Reference / lookup tables
-- ---------------------------------------------------------------------------

CREATE TABLE public.capability (
    capability_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.capability_capability_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    capability_name character varying,
    capability_marker character varying,
    CONSTRAINT capability_pkey PRIMARY KEY (capability_id)
);

CREATE TABLE public.failure_type (
    failure_type_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.failure_type_failure_type_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    failure_type_name character varying,
    CONSTRAINT failure_type_pkey PRIMARY KEY (failure_type_id)
);

CREATE TABLE public.lab_info (
    lab_info_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.lab_info_lab_info_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    lab_name character varying,
    CONSTRAINT lab_info_pkey PRIMARY KEY (lab_info_id)
);

CREATE TABLE public.release (
    release_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.release_release_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    release_name character varying,
    CONSTRAINT release_pkey PRIMARY KEY (release_id)
);

CREATE TABLE public.run_type (
    run_type_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.run_type_run_type_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    run_type_name character varying,
    CONSTRAINT run_type_pkey PRIMARY KEY (run_type_id)
);

CREATE TABLE public.test_case_group (
    test_case_group_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.test_case_group_test_case_group_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    test_case_group_name character varying,
    CONSTRAINT test_case_group_pkey PRIMARY KEY (test_case_group_id)
);

-- ---------------------------------------------------------------------------
-- Test inventory and planning
-- ---------------------------------------------------------------------------

CREATE TABLE public.test_info (
    test_info_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.test_info_test_info_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    test_name character varying,
    test_suite character varying,
    priority character varying,
    test_path character varying,
    pytest_node_id character varying,
    test_case_group_id integer DEFAULT '-1'::integer,
    is_active boolean DEFAULT true,
    CONSTRAINT test_info_pkey PRIMARY KEY (test_info_id)
);

CREATE TABLE public.test_plan (
    test_plan_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.test_plan_test_plan_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    test_plan_name character varying,
    description character varying,
    run_type_id integer,
    locked boolean DEFAULT false,
    CONSTRAINT test_plan_pkey PRIMARY KEY (test_plan_id)
);

CREATE TABLE public.session_info (
    session_info_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.session_info_session_info_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    session_name character varying,
    test_plan_id integer DEFAULT '-1'::integer,
    enabled boolean DEFAULT false,
    CONSTRAINT session_info_pkey PRIMARY KEY (session_info_id)
);

CREATE TABLE public.session_info_content (
    session_info_content_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.session_info_content_session_info_content_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    session_info_id integer,
    test_info_id integer,
    enabled boolean DEFAULT true,
    CONSTRAINT session_info_content_pkey PRIMARY KEY (session_info_content_id)
);

-- ---------------------------------------------------------------------------
-- Capability mappings
-- ---------------------------------------------------------------------------

CREATE TABLE public.capability_lab (
    capability_lab_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.capabilities_lab_capability_lab_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    lab_info_id integer,
    capability_id integer,
    CONSTRAINT capability_lab_pkey PRIMARY KEY (capability_lab_id)
);

CREATE TABLE public.capability_session (
    capability_session_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.capability_session_capability_session_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    session_info_id integer,
    capability_id integer,
    CONSTRAINT capability_session_pkey PRIMARY KEY (capability_session_id)
);

CREATE TABLE public.capability_test (
    capability_test_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.capability_test_capability_test_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    test_info_id integer,
    capability_id integer,
    CONSTRAINT capability_test_pkey PRIMARY KEY (capability_test_id)
);

-- ---------------------------------------------------------------------------
-- Runs, dispatching and results
-- ---------------------------------------------------------------------------

CREATE TABLE public.run (
    run_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.run_run_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    run_name character varying,
    run_type_id integer,
    release character varying,
    run_created_at timestamp without time zone,
    CONSTRAINT run_pkey PRIMARY KEY (run_id)
);

CREATE TABLE public.run_content (
    run_content_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.run_content_run_content_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    run_id integer,
    session_info_id integer,
    test_info_id integer,
    run_content_execution_status character varying,
    execution_fail_count integer,
    test_case_group_id integer,
    CONSTRAINT run_content_pkey PRIMARY KEY (run_content_id)
);

CREATE TABLE public.test_run_execution (
    test_run_execution_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.test_run_execution_test_run_execution_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    lab_info_id integer,
    run_id integer,
    dispatching_status character varying,
    run_content_id integer,
    test_case_group_id integer,
    CONSTRAINT test_run_execution_pkey PRIMARY KEY (test_run_execution_id)
);

CREATE TABLE public.lab_runtime_config (
    lab_runtime_config_id integer GENERATED BY DEFAULT AS IDENTITY
        (SEQUENCE NAME public.lab_runtime_config_lab_runtime_config_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    kernel_type character varying(20),
    cstate_setting character varying(50),
    pstate_setting character varying(50),
    per_core_config boolean,
    hyperthreading_enabled boolean,
    cpu_platform_cores integer,
    cpu_application_cores integer,
    cpu_application_isolated_cores integer,
    hugepages_2m integer,
    hugepages_1g integer,
    network_latency_ms numeric(8,2),
    bandwidth_mbps numeric(10,2),
    host_labels jsonb DEFAULT '{}'::jsonb NOT NULL,
    installed_apps jsonb DEFAULT '{}'::jsonb NOT NULL,
    extra_config jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lab_runtime_config_pkey PRIMARY KEY (lab_runtime_config_id)
);

CREATE TABLE public.test_session (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tag character varying,
    lab_id integer NOT NULL,
    patch character varying,
    created_at timestamp without time zone
        DEFAULT timezone('EST'::text, ('now'::text)::timestamp(0) with time zone) NOT NULL,
    sys_type character varying(200),
    run_id integer,
    kubernetes_version character varying,
    ceph_version character varying,
    session_info_id integer DEFAULT '-1'::integer NOT NULL,
    lab_runtime_config_id integer,
    CONSTRAINT test_session_pkey PRIMARY KEY (id)
);

CREATE TABLE public.test_case_result (
    test_case_result_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.test_case_result_test_case_result_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    test_id integer NOT NULL,
    result character varying NOT NULL,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    duration integer GENERATED ALWAYS AS (EXTRACT(epoch FROM (end_time - start_time))) STORED,
    log_hostname character varying DEFAULT 'none'::character varying,
    log_location character varying,
    session_id uuid,
    jenkins_log_location character varying,
    failure_file_name character varying,
    failure_function_name character varying,
    failure_line_number character varying,
    created_at timestamp(0) without time zone
        DEFAULT timezone('EST'::text, ('now'::text)::timestamp(0) with time zone) NOT NULL,
    CONSTRAINT test_case_result_pkey PRIMARY KEY (test_case_result_id)
);

CREATE TABLE public.analysis (
    analysis_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.analysis_analysis_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    run_content_id integer,
    test_info_id integer,
    defect_id character varying,
    comment character varying,
    failure_type_id integer,
    CONSTRAINT analysis_pkey PRIMARY KEY (analysis_id)
);

CREATE TABLE public.upgrade_event (
    upgrade_event_id integer GENERATED ALWAYS AS IDENTITY
        (SEQUENCE NAME public.upgrade_event_upgrade_event_id_seq
         START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1)
        NOT NULL,
    test_case_result_id integer,
    event_name character varying,
    retry integer,
    operation character varying,
    entity character varying,
    "timestamp" timestamp without time zone,
    is_upgrade boolean,
    is_patch boolean,
    is_rollback boolean DEFAULT false,
    duration integer DEFAULT 0,
    from_version character varying DEFAULT ''::character varying,
    to_version character varying DEFAULT ''::character varying,
    snapshot boolean DEFAULT false,
    subcloud text,
    build_id text,
    CONSTRAINT upgrade_event_pkey PRIMARY KEY (upgrade_event_id)
);

-- ---------------------------------------------------------------------------
-- KPI catalogue and measurements
-- ---------------------------------------------------------------------------

CREATE TABLE public.kpi (
    kpi_id integer DEFAULT nextval('public.kpi_id_seq'::regclass) NOT NULL,
    kpi_name character varying(200) NOT NULL,
    product character varying NOT NULL,
    kpi_group character varying NOT NULL,
    kpi_unit character varying,
    kpi_description character varying,
    kpi_category character varying(50),
    kpi_node_role character varying(50),
    kpi_detail character varying(50) NOT NULL,
    kpi_owner_team character varying(100),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kpi_pkey PRIMARY KEY (kpi_id)
);

ALTER SEQUENCE public.kpi_id_seq OWNED BY public.kpi.kpi_id;

CREATE TABLE public.kpi_measure (
    kpi_measure_id integer DEFAULT nextval('public.kpi_measure_id_seq'::regclass) NOT NULL,
    kpi_id integer NOT NULL,
    kpi_baseline_id integer,
    kpi_value double precision NOT NULL,
    exec_id uuid,
    is_displayed boolean DEFAULT true NOT NULL,
    test_case_result_id integer,
    session_id uuid,
    kpi_measure_details jsonb DEFAULT '{}'::jsonb NOT NULL,
    collected_at timestamp with time zone,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kpi_measure_pkey PRIMARY KEY (kpi_measure_id)
);

ALTER SEQUENCE public.kpi_measure_id_seq OWNED BY public.kpi_measure.kpi_measure_id;

-- ---------------------------------------------------------------------------
-- Tempest results
-- ---------------------------------------------------------------------------

CREATE TABLE public.tempest_run (
    id integer DEFAULT nextval('public.tempest_run_id_seq'::regclass) NOT NULL,
    lab_name character varying(200) NOT NULL,
    build_id character varying(200) NOT NULL,
    sw_version character varying(200) NOT NULL,
    test_suite character varying(200) NOT NULL,
    total integer NOT NULL,
    passed integer NOT NULL,
    failed integer NOT NULL,
    skipped integer NOT NULL,
    errors integer NOT NULL,
    duration double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT tempest_run_pkey PRIMARY KEY (id)
);

ALTER SEQUENCE public.tempest_run_id_seq OWNED BY public.tempest_run.id;

CREATE TABLE public.tempest_test_result (
    id integer DEFAULT nextval('public.tempest_test_result_id_seq'::regclass) NOT NULL,
    test_name character varying(500) NOT NULL,
    classname character varying(500) NOT NULL,
    status character varying(50) NOT NULL,
    duration double precision NOT NULL,
    message text NOT NULL,
    run_id integer NOT NULL,
    CONSTRAINT tempest_test_result_pkey PRIMARY KEY (id)
);

ALTER SEQUENCE public.tempest_test_result_id_seq OWNED BY public.tempest_test_result.id;

-- ---------------------------------------------------------------------------
-- Django bookkeeping (used by the dashboard web application)
-- ---------------------------------------------------------------------------

CREATE TABLE public.django_migrations (
    id integer DEFAULT nextval('public.django_migrations_id_seq'::regclass) NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL,
    CONSTRAINT django_migrations_pkey PRIMARY KEY (id)
);

ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE UNIQUE INDEX kpi_uniq ON public.kpi USING btree (
    product,
    COALESCE(kpi_category, '*'::character varying),
    kpi_group,
    kpi_name,
    COALESCE(kpi_node_role, '*'::character varying),
    kpi_detail
);

CREATE INDEX idx_kpi_category ON public.kpi USING btree (kpi_category);
CREATE INDEX idx_kpi_group ON public.kpi USING btree (kpi_group);
CREATE INDEX idx_kpi_is_active ON public.kpi USING btree (is_active);
CREATE INDEX idx_kpi_owner_team ON public.kpi USING btree (kpi_owner_team);

CREATE INDEX idx_km_details_gin ON public.kpi_measure USING gin (kpi_measure_details);
CREATE INDEX idx_km_kpi_collected ON public.kpi_measure USING btree (kpi_id, collected_at DESC);
CREATE INDEX idx_km_session ON public.kpi_measure USING btree (session_id);
CREATE INDEX idx_km_test_case_result ON public.kpi_measure USING btree (test_case_result_id);

CREATE INDEX idx_lrc_cstate_pstate ON public.lab_runtime_config USING btree (cstate_setting, pstate_setting);
CREATE INDEX idx_lrc_extra_gin ON public.lab_runtime_config USING gin (extra_config);
CREATE INDEX idx_lrc_host_labels_gin ON public.lab_runtime_config USING gin (host_labels);
CREATE INDEX idx_lrc_installed_apps_gin ON public.lab_runtime_config USING gin (installed_apps);
CREATE INDEX idx_lrc_kernel ON public.lab_runtime_config USING btree (kernel_type);

CREATE INDEX tempest_test_result_run_id_94827ffe ON public.tempest_test_result USING btree (run_id);

-- ---------------------------------------------------------------------------
-- Foreign keys
--
-- Only these four relationships are enforced at the database level; the rest
-- of the *_id columns are joined by convention in application code.
-- ---------------------------------------------------------------------------

ALTER TABLE ONLY public.kpi_measure
    ADD CONSTRAINT kpi_measure_kpi_fkey
    FOREIGN KEY (kpi_id) REFERENCES public.kpi(kpi_id);

ALTER TABLE ONLY public.kpi_measure
    ADD CONSTRAINT kpi_measure_session_fkey
    FOREIGN KEY (session_id) REFERENCES public.test_session(id);

ALTER TABLE ONLY public.kpi_measure
    ADD CONSTRAINT kpi_measure_test_case_result_fkey
    FOREIGN KEY (test_case_result_id) REFERENCES public.test_case_result(test_case_result_id);

ALTER TABLE ONLY public.tempest_test_result
    ADD CONSTRAINT tempest_test_result_run_id_94827ffe_fk_tempest_run_id
    FOREIGN KEY (run_id) REFERENCES public.tempest_run(id) DEFERRABLE INITIALLY DEFERRED;

-- ---------------------------------------------------------------------------
-- Minimum lookup data
--
-- run_type is referenced by run.run_type_id and test_plan.run_type_id, and the
-- ids are hard-coded expectations in the framework, so the rows are recreated
-- with their original ids.
-- ---------------------------------------------------------------------------

ALTER TABLE public.run_type ALTER COLUMN run_type_id SET GENERATED BY DEFAULT;

INSERT INTO public.run_type (run_type_id, run_type_name) VALUES
    (1, 'Regression'),
    (2, 'Sanity'),
    (3, 'Custom'),
    (4, 'SanityRegression');

ALTER TABLE public.run_type ALTER COLUMN run_type_id SET GENERATED ALWAYS;

SELECT setval('public.run_type_run_type_id_seq',
              (SELECT max(run_type_id) FROM public.run_type), true);

-- ---------------------------------------------------------------------------
-- Ownership
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    obj record;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'automation_user') THEN
        RAISE NOTICE 'Role automation_user does not exist; skipping ownership changes.';
        RETURN;
    END IF;

    -- Every sequence in this schema is owned by (linked to) a table column, so
    -- reassigning the tables also reassigns the sequences.
    FOR obj IN
        SELECT relname
        FROM pg_class
        WHERE relnamespace = 'public'::regnamespace
          AND relkind = 'r'
    LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO automation_user', obj.relname);
    END LOOP;

    EXECUTE 'GRANT USAGE ON SCHEMA public TO automation_user';
END
$$;
