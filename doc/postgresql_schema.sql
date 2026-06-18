-- ZIC Core Life PostgreSQL schema
-- Target: PostgreSQL 14+

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS security;
CREATE SCHEMA IF NOT EXISTS approval;
CREATE SCHEMA IF NOT EXISTS partner;
CREATE SCHEMA IF NOT EXISTS onboarding;
CREATE SCHEMA IF NOT EXISTS dashboard;
CREATE SCHEMA IF NOT EXISTS ol;
CREATE SCHEMA IF NOT EXISTS gl;
CREATE SCHEMA IF NOT EXISTS gc;
CREATE SCHEMA IF NOT EXISTS front_office;
CREATE SCHEMA IF NOT EXISTS reinsurance;
CREATE SCHEMA IF NOT EXISTS reporting;

CREATE OR REPLACE FUNCTION core.set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE core.currency (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(3) NOT NULL UNIQUE,
  name varchar(100) NOT NULL,
  symbol varchar(10),
  decimal_places smallint NOT NULL DEFAULT 2,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.branch (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(30) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.company_parameter (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name varchar(200) NOT NULL,
  registration_number varchar(80),
  tax_number varchar(80),
  default_currency_id uuid REFERENCES core.currency(id),
  base_branch_id uuid REFERENCES core.branch(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.tax_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(30) NOT NULL UNIQUE,
  name varchar(120) NOT NULL,
  rate numeric(9,6) NOT NULL DEFAULT 0,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE core.number_sequence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  description varchar(200),
  prefix varchar(30),
  next_number bigint NOT NULL DEFAULT 1,
  padding smallint NOT NULL DEFAULT 6,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.document_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  module_code varchar(50) NOT NULL,
  is_mandatory boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.notification_template (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  channel varchar(30) NOT NULL,
  subject varchar(200),
  body text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Security and user management

CREATE TABLE security.user_account (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username varchar(150) NOT NULL UNIQUE,
  email varchar(254) UNIQUE,
  password_hash varchar(256) NOT NULL,
  first_name varchar(100),
  last_name varchar(100),
  staff_number varchar(50) UNIQUE,
  branch_id uuid REFERENCES core.branch(id),
  department varchar(120),
  job_title varchar(120),
  is_staff boolean NOT NULL DEFAULT false,
  is_superuser boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE security.permission (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(120) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  module_code varchar(80) NOT NULL,
  action_code varchar(50) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE security.permission_group (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(80) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE security.permission_group_permission (
  permission_group_id uuid NOT NULL REFERENCES security.permission_group(id) ON DELETE CASCADE,
  permission_id uuid NOT NULL REFERENCES security.permission(id) ON DELETE CASCADE,
  PRIMARY KEY (permission_group_id, permission_id)
);

CREATE TABLE security.user_group (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(80) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE security.user_group_permission_group (
  user_group_id uuid NOT NULL REFERENCES security.user_group(id) ON DELETE CASCADE,
  permission_group_id uuid NOT NULL REFERENCES security.permission_group(id) ON DELETE CASCADE,
  PRIMARY KEY (user_group_id, permission_group_id)
);

CREATE TABLE security.user_group_member (
  user_group_id uuid NOT NULL REFERENCES security.user_group(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES security.user_account(id) ON DELETE CASCADE,
  assigned_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_group_id, user_id)
);

CREATE TABLE security.user_preference (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES security.user_account(id) ON DELETE CASCADE,
  preference_key varchar(100) NOT NULL,
  preference_value jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, preference_key)
);

-- Partner parameters

CREATE TABLE partner.partner_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE partner.partner (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_type_id uuid NOT NULL REFERENCES partner.partner_type(id),
  code varchar(50) NOT NULL UNIQUE,
  legal_name varchar(200) NOT NULL,
  display_name varchar(200),
  registration_number varchar(80),
  tax_number varchar(80),
  email varchar(254),
  phone varchar(50),
  address text,
  branch_id uuid REFERENCES core.branch(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE partner.partner_contact (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id uuid NOT NULL REFERENCES partner.partner(id) ON DELETE CASCADE,
  full_name varchar(200) NOT NULL,
  job_title varchar(120),
  email varchar(254),
  phone varchar(50),
  is_primary boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE partner.partner_bank_account (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id uuid NOT NULL REFERENCES partner.partner(id) ON DELETE CASCADE,
  bank_name varchar(150) NOT NULL,
  branch_name varchar(150),
  account_name varchar(200) NOT NULL,
  account_number varchar(80) NOT NULL,
  iban varchar(80),
  swift_code varchar(30),
  currency_id uuid REFERENCES core.currency(id),
  is_primary boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Approval module

CREATE TABLE approval.approval_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approval.approval_process_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  module_code varchar(80) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approval.approval_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_success boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approval.approval_role (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approval.approver (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  approval_role_id uuid NOT NULL REFERENCES approval.approval_role(id),
  user_id uuid NOT NULL REFERENCES security.user_account(id),
  branch_id uuid REFERENCES core.branch(id),
  limit_amount numeric(18,2),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (approval_role_id, user_id, branch_id)
);

CREATE TABLE approval.approval_rule (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(80) NOT NULL UNIQUE,
  approval_type_id uuid NOT NULL REFERENCES approval.approval_type(id),
  process_type_id uuid NOT NULL REFERENCES approval.approval_process_type(id),
  approval_role_id uuid NOT NULL REFERENCES approval.approval_role(id),
  branch_id uuid REFERENCES core.branch(id),
  min_amount numeric(18,2) NOT NULL DEFAULT 0,
  max_amount numeric(18,2),
  sequence_no integer NOT NULL DEFAULT 1,
  is_required boolean NOT NULL DEFAULT true,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (max_amount IS NULL OR max_amount >= min_amount)
);

CREATE TABLE approval.approval_process (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  process_type_id uuid NOT NULL REFERENCES approval.approval_process_type(id),
  code varchar(80) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approval.approval (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  approval_process_id uuid NOT NULL REFERENCES approval.approval_process(id),
  approval_status_id uuid NOT NULL REFERENCES approval.approval_status(id),
  requested_by_id uuid NOT NULL REFERENCES security.user_account(id),
  current_approver_id uuid REFERENCES security.user_account(id),
  module_code varchar(80) NOT NULL,
  entity_table varchar(120) NOT NULL,
  entity_id uuid NOT NULL,
  reference_no varchar(80) NOT NULL,
  amount numeric(18,2),
  currency_id uuid REFERENCES core.currency(id),
  submitted_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  comments text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approval.approval_action (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  approval_id uuid NOT NULL REFERENCES approval.approval(id) ON DELETE CASCADE,
  action_by_id uuid NOT NULL REFERENCES security.user_account(id),
  from_status_id uuid REFERENCES approval.approval_status(id),
  to_status_id uuid NOT NULL REFERENCES approval.approval_status(id),
  action_code varchar(50) NOT NULL,
  comments text,
  action_at timestamptz NOT NULL DEFAULT now()
);

-- Group Credit setup

CREATE TABLE gc.scheme_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.scheme_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.scheme_member_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_covered boolean NOT NULL DEFAULT true,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.scheme_renewal_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.product (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  premium_basis varchar(50) NOT NULL DEFAULT 'SUM_ASSURED',
  min_term_months integer,
  max_term_months integer,
  min_entry_age integer,
  max_entry_age integer,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.sub_product (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES gc.product(id),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  benefit_description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.scheme_premium_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_type_id uuid REFERENCES gc.scheme_type(id),
  product_id uuid NOT NULL REFERENCES gc.product(id),
  sub_product_id uuid REFERENCES gc.sub_product(id),
  age_from integer,
  age_to integer,
  term_from_months integer,
  term_to_months integer,
  sum_assured_from numeric(18,2),
  sum_assured_to numeric(18,2),
  rate numeric(18,8) NOT NULL,
  rate_basis varchar(50) NOT NULL DEFAULT 'PER_1000',
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE gc.health_question (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  question_text text NOT NULL,
  answer_type varchar(30) NOT NULL DEFAULT 'BOOLEAN',
  requires_details boolean NOT NULL DEFAULT false,
  referral_answer varchar(100),
  score integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.health_questionnaire (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  product_id uuid REFERENCES gc.product(id),
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.health_questionnaire_question (
  questionnaire_id uuid NOT NULL REFERENCES gc.health_questionnaire(id) ON DELETE CASCADE,
  question_id uuid NOT NULL REFERENCES gc.health_question(id),
  sequence_no integer NOT NULL,
  is_mandatory boolean NOT NULL DEFAULT true,
  PRIMARY KEY (questionnaire_id, question_id)
);

CREATE TABLE gc.rider (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_mandatory boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.rider_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rider_id uuid NOT NULL REFERENCES gc.rider(id),
  product_id uuid REFERENCES gc.product(id),
  age_from integer,
  age_to integer,
  term_from_months integer,
  term_to_months integer,
  sum_assured_from numeric(18,2),
  sum_assured_to numeric(18,2),
  rate numeric(18,8) NOT NULL,
  rate_basis varchar(50) NOT NULL DEFAULT 'PER_1000',
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Group Credit medical underwriting

CREATE TABLE gc.medical_code (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  category varchar(80),
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.underwriting_decision (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_acceptance boolean NOT NULL DEFAULT false,
  is_decline boolean NOT NULL DEFAULT false,
  is_referral boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.medical_limit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES gc.product(id),
  sub_product_id uuid REFERENCES gc.sub_product(id),
  age_from integer,
  age_to integer,
  sum_assured_from numeric(18,2),
  sum_assured_to numeric(18,2),
  required_action varchar(80) NOT NULL,
  medical_code_id uuid REFERENCES gc.medical_code(id),
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.personal_habit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  risk_score integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.medical_facility (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id uuid REFERENCES partner.partner(id),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(200) NOT NULL,
  license_no varchar(80),
  address text,
  phone varchar(50),
  email varchar(254),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.medical_practitioner (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id uuid REFERENCES gc.medical_facility(id),
  code varchar(50) NOT NULL UNIQUE,
  full_name varchar(200) NOT NULL,
  license_no varchar(80),
  specialty varchar(120),
  phone varchar(50),
  email varchar(254),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Group Credit quotations and schemes

CREATE TABLE gc.quotation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  quotation_no varchar(80) NOT NULL UNIQUE,
  quotation_version integer NOT NULL DEFAULT 1,
  policyholder_id uuid NOT NULL REFERENCES partner.partner(id),
  broker_id uuid REFERENCES partner.partner(id),
  lender_id uuid REFERENCES partner.partner(id),
  product_id uuid NOT NULL REFERENCES gc.product(id),
  sub_product_id uuid REFERENCES gc.sub_product(id),
  scheme_type_id uuid REFERENCES gc.scheme_type(id),
  branch_id uuid REFERENCES core.branch(id),
  currency_id uuid REFERENCES core.currency(id),
  quotation_date date NOT NULL DEFAULT CURRENT_DATE,
  effective_from date,
  effective_to date,
  member_count integer NOT NULL DEFAULT 0,
  loan_amount numeric(18,2) NOT NULL DEFAULT 0,
  sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  commission_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  underwriting_decision_id uuid REFERENCES gc.underwriting_decision(id),
  created_by_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.quotation_rider (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  quotation_id uuid NOT NULL REFERENCES gc.quotation(id) ON DELETE CASCADE,
  rider_id uuid NOT NULL REFERENCES gc.rider(id),
  sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  UNIQUE (quotation_id, rider_id)
);

CREATE TABLE gc.quotation_questionnaire_response (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  quotation_id uuid NOT NULL REFERENCES gc.quotation(id) ON DELETE CASCADE,
  questionnaire_id uuid REFERENCES gc.health_questionnaire(id),
  question_id uuid NOT NULL REFERENCES gc.health_question(id),
  answer_text text,
  answer_bool boolean,
  details text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.scheme (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_no varchar(80) NOT NULL UNIQUE,
  quotation_id uuid REFERENCES gc.quotation(id),
  policyholder_id uuid NOT NULL REFERENCES partner.partner(id),
  broker_id uuid REFERENCES partner.partner(id),
  lender_id uuid REFERENCES partner.partner(id),
  product_id uuid NOT NULL REFERENCES gc.product(id),
  sub_product_id uuid REFERENCES gc.sub_product(id),
  scheme_type_id uuid NOT NULL REFERENCES gc.scheme_type(id),
  scheme_status_id uuid NOT NULL REFERENCES gc.scheme_status(id),
  branch_id uuid REFERENCES core.branch(id),
  currency_id uuid REFERENCES core.currency(id),
  start_date date NOT NULL,
  end_date date NOT NULL,
  renewal_day smallint,
  member_count integer NOT NULL DEFAULT 0,
  total_sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  annual_premium numeric(18,2) NOT NULL DEFAULT 0,
  commission_rate numeric(9,6) NOT NULL DEFAULT 0,
  created_by_id uuid REFERENCES security.user_account(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (end_date >= start_date)
);

CREATE TABLE gc.scheme_member (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_id uuid NOT NULL REFERENCES gc.scheme(id) ON DELETE CASCADE,
  member_no varchar(80) NOT NULL,
  member_status_id uuid NOT NULL REFERENCES gc.scheme_member_status(id),
  full_name varchar(200) NOT NULL,
  national_id varchar(80),
  date_of_birth date,
  gender varchar(20),
  loan_reference varchar(80),
  loan_amount numeric(18,2) NOT NULL DEFAULT 0,
  outstanding_balance numeric(18,2) NOT NULL DEFAULT 0,
  sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  cover_start_date date NOT NULL,
  cover_end_date date NOT NULL,
  underwriting_decision_id uuid REFERENCES gc.underwriting_decision(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scheme_id, member_no),
  CHECK (cover_end_date >= cover_start_date)
);

CREATE TABLE gc.member_medical_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_member_id uuid NOT NULL REFERENCES gc.scheme_member(id) ON DELETE CASCADE,
  medical_code_id uuid REFERENCES gc.medical_code(id),
  personal_habit_id uuid REFERENCES gc.personal_habit(id),
  description text,
  diagnosis_date date,
  decision_id uuid REFERENCES gc.underwriting_decision(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.scheme_renewal (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_id uuid NOT NULL REFERENCES gc.scheme(id) ON DELETE CASCADE,
  renewal_status_id uuid NOT NULL REFERENCES gc.scheme_renewal_status(id),
  renewal_no varchar(80) NOT NULL UNIQUE,
  due_date date NOT NULL,
  renewal_from date,
  renewal_to date,
  quoted_premium numeric(18,2) NOT NULL DEFAULT 0,
  renewed_premium numeric(18,2) NOT NULL DEFAULT 0,
  assigned_to_id uuid REFERENCES security.user_account(id),
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Group Credit claims

CREATE TABLE gc.claim_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.claim_reason (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  claim_type_id uuid REFERENCES gc.claim_type(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.claim_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_payable boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.discharge_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.correspondent_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.claim (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_no varchar(80) NOT NULL UNIQUE,
  scheme_id uuid NOT NULL REFERENCES gc.scheme(id),
  scheme_member_id uuid REFERENCES gc.scheme_member(id),
  claim_type_id uuid NOT NULL REFERENCES gc.claim_type(id),
  claim_reason_id uuid REFERENCES gc.claim_reason(id),
  claim_status_id uuid NOT NULL REFERENCES gc.claim_status(id),
  discharge_type_id uuid REFERENCES gc.discharge_type(id),
  event_date date NOT NULL,
  notification_date date NOT NULL,
  reported_by varchar(200),
  claimant_partner_id uuid REFERENCES partner.partner(id),
  cause_description text,
  reserve_amount numeric(18,2) NOT NULL DEFAULT 0,
  claimed_amount numeric(18,2) NOT NULL DEFAULT 0,
  approved_amount numeric(18,2) NOT NULL DEFAULT 0,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  currency_id uuid REFERENCES core.currency(id),
  assigned_to_id uuid REFERENCES security.user_account(id),
  created_by_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  closed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.claim_installment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id uuid NOT NULL REFERENCES gc.claim(id) ON DELETE CASCADE,
  installment_no integer NOT NULL,
  due_date date NOT NULL,
  amount numeric(18,2) NOT NULL,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  payment_status varchar(50) NOT NULL DEFAULT 'PENDING',
  payment_reference varchar(120),
  paid_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (claim_id, installment_no)
);

CREATE TABLE gc.claim_correspondence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id uuid NOT NULL REFERENCES gc.claim(id) ON DELETE CASCADE,
  correspondent_type_id uuid NOT NULL REFERENCES gc.correspondent_type(id),
  correspondent_name varchar(200) NOT NULL,
  subject varchar(200),
  message text,
  sent_at timestamptz,
  received_at timestamptz,
  created_by_id uuid REFERENCES security.user_account(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Group Credit medical invoices

CREATE TABLE gc.medical_invoice (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_no varchar(80) NOT NULL UNIQUE,
  facility_id uuid REFERENCES gc.medical_facility(id),
  practitioner_id uuid REFERENCES gc.medical_practitioner(id),
  scheme_id uuid REFERENCES gc.scheme(id),
  scheme_member_id uuid REFERENCES gc.scheme_member(id),
  claim_id uuid REFERENCES gc.claim(id),
  invoice_date date NOT NULL,
  due_date date,
  invoice_amount numeric(18,2) NOT NULL DEFAULT 0,
  tax_amount numeric(18,2) NOT NULL DEFAULT 0,
  discount_amount numeric(18,2) NOT NULL DEFAULT 0,
  payable_amount numeric(18,2) NOT NULL DEFAULT 0,
  currency_id uuid REFERENCES core.currency(id),
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  created_by_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gc.medical_invoice_line (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  medical_invoice_id uuid NOT NULL REFERENCES gc.medical_invoice(id) ON DELETE CASCADE,
  medical_code_id uuid REFERENCES gc.medical_code(id),
  description varchar(250) NOT NULL,
  quantity numeric(12,2) NOT NULL DEFAULT 1,
  unit_price numeric(18,2) NOT NULL DEFAULT 0,
  line_amount numeric(18,2) NOT NULL DEFAULT 0
);

-- Front Office

CREATE TABLE front_office.receipt_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.payment_method (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.transaction_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.requisition_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.commission_rule (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  partner_type_id uuid REFERENCES partner.partner_type(id),
  product_id uuid REFERENCES gc.product(id),
  rate numeric(9,6) NOT NULL DEFAULT 0,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.receipt (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  receipt_no varchar(80) NOT NULL UNIQUE,
  receipt_type_id uuid NOT NULL REFERENCES front_office.receipt_type(id),
  payment_method_id uuid REFERENCES front_office.payment_method(id),
  transaction_status_id uuid REFERENCES front_office.transaction_status(id),
  payer_partner_id uuid REFERENCES partner.partner(id),
  receipt_date date NOT NULL DEFAULT CURRENT_DATE,
  amount numeric(18,2) NOT NULL,
  currency_id uuid REFERENCES core.currency(id),
  reference_no varchar(120),
  narration text,
  created_by_id uuid REFERENCES security.user_account(id),
  reversed_by_id uuid REFERENCES security.user_account(id),
  reversed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.receipt_allocation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  receipt_id uuid NOT NULL REFERENCES front_office.receipt(id) ON DELETE CASCADE,
  module_code varchar(80) NOT NULL,
  entity_table varchar(120) NOT NULL,
  entity_id uuid NOT NULL,
  allocated_amount numeric(18,2) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.commission (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  commission_no varchar(80) NOT NULL UNIQUE,
  partner_id uuid NOT NULL REFERENCES partner.partner(id),
  scheme_id uuid REFERENCES gc.scheme(id),
  quotation_id uuid REFERENCES gc.quotation(id),
  commission_rule_id uuid REFERENCES front_office.commission_rule(id),
  commission_rate numeric(9,6) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  commission_amount numeric(18,2) NOT NULL DEFAULT 0,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'ACCRUED',
  currency_id uuid REFERENCES core.currency(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.commission_statement (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  statement_no varchar(80) NOT NULL UNIQUE,
  partner_id uuid NOT NULL REFERENCES partner.partner(id),
  period_from date NOT NULL,
  period_to date NOT NULL,
  earned_amount numeric(18,2) NOT NULL DEFAULT 0,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  outstanding_amount numeric(18,2) NOT NULL DEFAULT 0,
  currency_id uuid REFERENCES core.currency(id),
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  generated_by_id uuid REFERENCES security.user_account(id),
  generated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (period_to >= period_from)
);

CREATE TABLE front_office.commission_statement_line (
  statement_id uuid NOT NULL REFERENCES front_office.commission_statement(id) ON DELETE CASCADE,
  commission_id uuid NOT NULL REFERENCES front_office.commission(id),
  PRIMARY KEY (statement_id, commission_id)
);

CREATE TABLE front_office.requisition (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  requisition_no varchar(80) NOT NULL UNIQUE,
  requisition_type_id uuid NOT NULL REFERENCES front_office.requisition_type(id),
  transaction_status_id uuid REFERENCES front_office.transaction_status(id),
  beneficiary_partner_id uuid REFERENCES partner.partner(id),
  module_code varchar(80),
  entity_table varchar(120),
  entity_id uuid,
  requested_amount numeric(18,2) NOT NULL,
  approved_amount numeric(18,2) NOT NULL DEFAULT 0,
  currency_id uuid REFERENCES core.currency(id),
  reason text,
  requested_by_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE front_office.payment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_no varchar(80) NOT NULL UNIQUE,
  requisition_id uuid REFERENCES front_office.requisition(id),
  payment_method_id uuid REFERENCES front_office.payment_method(id),
  transaction_status_id uuid REFERENCES front_office.transaction_status(id),
  beneficiary_partner_id uuid REFERENCES partner.partner(id),
  payment_date date NOT NULL DEFAULT CURRENT_DATE,
  amount numeric(18,2) NOT NULL,
  currency_id uuid REFERENCES core.currency(id),
  bank_reference varchar(120),
  narration text,
  created_by_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Reinsurance parameters and processing

CREATE TABLE reinsurance.department (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.class (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.treaty_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  treaty_category varchar(50) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.treaty_code (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  treaty_type_id uuid NOT NULL REFERENCES reinsurance.treaty_type(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.underwriting_year (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  year_no integer NOT NULL UNIQUE,
  start_date date NOT NULL,
  end_date date NOT NULL,
  is_closed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (end_date >= start_date)
);

CREATE TABLE reinsurance.business_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.branch (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  core_branch_id uuid REFERENCES core.branch(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.ceded_premium_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id uuid NOT NULL REFERENCES reinsurance.class(id),
  business_type_id uuid REFERENCES reinsurance.business_type(id),
  product_id uuid REFERENCES gc.product(id),
  rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.treaty_participant (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  treaty_code_id uuid NOT NULL REFERENCES reinsurance.treaty_code(id),
  reinsurer_partner_id uuid NOT NULL REFERENCES partner.partner(id),
  share_percent numeric(9,6) NOT NULL,
  commission_percent numeric(9,6) NOT NULL DEFAULT 0,
  is_lead boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (share_percent >= 0 AND share_percent <= 100)
);

CREATE TABLE reinsurance.proportional_treaty (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  treaty_code_id uuid NOT NULL REFERENCES reinsurance.treaty_code(id),
  underwriting_year_id uuid NOT NULL REFERENCES reinsurance.underwriting_year(id),
  class_id uuid NOT NULL REFERENCES reinsurance.class(id),
  branch_id uuid REFERENCES reinsurance.branch(id),
  retention_amount numeric(18,2) NOT NULL DEFAULT 0,
  treaty_limit numeric(18,2) NOT NULL DEFAULT 0,
  cession_percent numeric(9,6) NOT NULL DEFAULT 0,
  effective_from date NOT NULL,
  effective_to date NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.proportional_class_cession (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  proportional_treaty_id uuid NOT NULL REFERENCES reinsurance.proportional_treaty(id) ON DELETE CASCADE,
  class_id uuid NOT NULL REFERENCES reinsurance.class(id),
  product_id uuid REFERENCES gc.product(id),
  retention_percent numeric(9,6) NOT NULL DEFAULT 0,
  cession_percent numeric(9,6) NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.non_proportional_treaty (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  treaty_code_id uuid NOT NULL REFERENCES reinsurance.treaty_code(id),
  underwriting_year_id uuid NOT NULL REFERENCES reinsurance.underwriting_year(id),
  class_id uuid NOT NULL REFERENCES reinsurance.class(id),
  branch_id uuid REFERENCES reinsurance.branch(id),
  priority_amount numeric(18,2) NOT NULL DEFAULT 0,
  cover_limit numeric(18,2) NOT NULL DEFAULT 0,
  reinstatement_count integer NOT NULL DEFAULT 0,
  effective_from date NOT NULL,
  effective_to date NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.non_proportional_class_cession (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  non_proportional_treaty_id uuid NOT NULL REFERENCES reinsurance.non_proportional_treaty(id) ON DELETE CASCADE,
  class_id uuid NOT NULL REFERENCES reinsurance.class(id),
  product_id uuid REFERENCES gc.product(id),
  layer_no integer NOT NULL DEFAULT 1,
  priority_amount numeric(18,2) NOT NULL DEFAULT 0,
  cover_limit numeric(18,2) NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reinsurance.processing_batch (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_no varchar(80) NOT NULL UNIQUE,
  underwriting_year_id uuid REFERENCES reinsurance.underwriting_year(id),
  period_from date NOT NULL,
  period_to date NOT NULL,
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  processed_by_id uuid REFERENCES security.user_account(id),
  processed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (period_to >= period_from)
);

CREATE TABLE reinsurance.cession (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  processing_batch_id uuid REFERENCES reinsurance.processing_batch(id),
  scheme_id uuid REFERENCES gc.scheme(id),
  claim_id uuid REFERENCES gc.claim(id),
  treaty_code_id uuid REFERENCES reinsurance.treaty_code(id),
  underwriting_year_id uuid REFERENCES reinsurance.underwriting_year(id),
  gross_amount numeric(18,2) NOT NULL DEFAULT 0,
  retained_amount numeric(18,2) NOT NULL DEFAULT 0,
  ceded_amount numeric(18,2) NOT NULL DEFAULT 0,
  ceded_premium numeric(18,2) NOT NULL DEFAULT 0,
  commission_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'PENDING',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE VIEW gc.v_schemes_due_for_renewal AS
SELECT
  s.id AS scheme_id,
  s.scheme_no,
  p.legal_name AS policyholder_name,
  st.name AS scheme_status,
  s.end_date AS renewal_due_date,
  s.annual_premium,
  s.member_count,
  COALESCE(r.renewal_no, '') AS latest_renewal_no,
  rs.name AS renewal_status,
  r.assigned_to_id
FROM gc.scheme s
JOIN partner.partner p ON p.id = s.policyholder_id
JOIN gc.scheme_status st ON st.id = s.scheme_status_id
LEFT JOIN LATERAL (
  SELECT sr.*
  FROM gc.scheme_renewal sr
  WHERE sr.scheme_id = s.id
  ORDER BY sr.due_date DESC, sr.created_at DESC
  LIMIT 1
) r ON true
LEFT JOIN gc.scheme_renewal_status rs ON rs.id = r.renewal_status_id
WHERE s.end_date >= CURRENT_DATE;

CREATE VIEW reinsurance.v_processing_dashboard AS
SELECT
  pb.id AS processing_batch_id,
  pb.batch_no,
  pb.period_from,
  pb.period_to,
  pb.status_code,
  uy.year_no AS underwriting_year,
  COUNT(c.id) AS cession_count,
  COALESCE(SUM(c.gross_amount), 0) AS gross_amount,
  COALESCE(SUM(c.retained_amount), 0) AS retained_amount,
  COALESCE(SUM(c.ceded_amount), 0) AS ceded_amount,
  COALESCE(SUM(c.ceded_premium), 0) AS ceded_premium,
  COALESCE(SUM(c.commission_amount), 0) AS commission_amount
FROM reinsurance.processing_batch pb
LEFT JOIN reinsurance.underwriting_year uy ON uy.id = pb.underwriting_year_id
LEFT JOIN reinsurance.cession c ON c.processing_batch_id = pb.id
GROUP BY pb.id, pb.batch_no, pb.period_from, pb.period_to, pb.status_code, uy.year_no;

-- Reports

CREATE TABLE reporting.report_definition (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(80) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  module_code varchar(80) NOT NULL,
  description text,
  query_name varchar(120),
  default_format varchar(20) NOT NULL DEFAULT 'XLSX',
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reporting.report_run (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_definition_id uuid NOT NULL REFERENCES reporting.report_definition(id),
  requested_by_id uuid REFERENCES security.user_account(id),
  parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
  status_code varchar(50) NOT NULL DEFAULT 'QUEUED',
  output_file varchar(500),
  started_at timestamptz,
  completed_at timestamptz,
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Audit trail

CREATE TABLE core.audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES security.user_account(id),
  module_code varchar(80) NOT NULL,
  entity_table varchar(120) NOT NULL,
  entity_id uuid,
  action_code varchar(50) NOT NULL,
  old_values jsonb,
  new_values jsonb,
  ip_address inet,
  user_agent text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Common indexes

CREATE INDEX idx_partner_partner_type ON partner.partner(partner_type_id);
CREATE INDEX idx_gc_quotation_policyholder ON gc.quotation(policyholder_id);
CREATE INDEX idx_gc_quotation_status ON gc.quotation(status_code);
CREATE INDEX idx_gc_scheme_policyholder ON gc.scheme(policyholder_id);
CREATE INDEX idx_gc_scheme_status ON gc.scheme(scheme_status_id);
CREATE INDEX idx_gc_scheme_member_scheme ON gc.scheme_member(scheme_id);
CREATE INDEX idx_gc_claim_scheme ON gc.claim(scheme_id);
CREATE INDEX idx_gc_claim_member ON gc.claim(scheme_member_id);
CREATE INDEX idx_gc_claim_status ON gc.claim(claim_status_id);
CREATE INDEX idx_front_receipt_date ON front_office.receipt(receipt_date);
CREATE INDEX idx_front_payment_date ON front_office.payment(payment_date);
CREATE INDEX idx_reinsurance_cession_scheme ON reinsurance.cession(scheme_id);
CREATE INDEX idx_reinsurance_cession_claim ON reinsurance.cession(claim_id);
CREATE INDEX idx_approval_entity ON approval.approval(entity_table, entity_id);
CREATE INDEX idx_audit_entity ON core.audit_log(entity_table, entity_id);

-- Updated-at triggers

CREATE TRIGGER trg_currency_updated_at BEFORE UPDATE ON core.currency FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_branch_updated_at BEFORE UPDATE ON core.branch FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_user_account_updated_at BEFORE UPDATE ON security.user_account FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_partner_updated_at BEFORE UPDATE ON partner.partner FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_gc_quotation_updated_at BEFORE UPDATE ON gc.quotation FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_gc_scheme_updated_at BEFORE UPDATE ON gc.scheme FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_gc_scheme_member_updated_at BEFORE UPDATE ON gc.scheme_member FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_gc_claim_updated_at BEFORE UPDATE ON gc.claim FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_medical_invoice_updated_at BEFORE UPDATE ON gc.medical_invoice FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_receipt_updated_at BEFORE UPDATE ON front_office.receipt FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_payment_updated_at BEFORE UPDATE ON front_office.payment FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_approval_updated_at BEFORE UPDATE ON approval.approval FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();
CREATE TRIGGER trg_reinsurance_cession_updated_at BEFORE UPDATE ON reinsurance.cession FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();

-- Dashboard and partner onboarding

CREATE TABLE dashboard.widget (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(80) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  module_code varchar(80) NOT NULL,
  widget_type varchar(50) NOT NULL,
  query_name varchar(150),
  refresh_seconds integer NOT NULL DEFAULT 300,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE dashboard.user_widget (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES security.user_account(id) ON DELETE CASCADE,
  widget_id uuid NOT NULL REFERENCES dashboard.widget(id) ON DELETE CASCADE,
  display_order integer NOT NULL DEFAULT 1,
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_visible boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, widget_id)
);

CREATE TABLE onboarding.partner_application (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_no varchar(80) NOT NULL UNIQUE,
  partner_type_id uuid NOT NULL REFERENCES partner.partner_type(id),
  proposed_legal_name varchar(200) NOT NULL,
  proposed_display_name varchar(200),
  registration_number varchar(80),
  tax_number varchar(80),
  email varchar(254),
  phone varchar(50),
  address text,
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  submitted_by_id uuid REFERENCES security.user_account(id),
  reviewed_by_id uuid REFERENCES security.user_account(id),
  approved_partner_id uuid REFERENCES partner.partner(id),
  submitted_at timestamptz,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE onboarding.partner_application_document (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_application_id uuid NOT NULL REFERENCES onboarding.partner_application(id) ON DELETE CASCADE,
  document_type_id uuid REFERENCES core.document_type(id),
  document_name varchar(200) NOT NULL,
  file_path varchar(500),
  verification_status varchar(50) NOT NULL DEFAULT 'PENDING',
  verified_by_id uuid REFERENCES security.user_account(id),
  verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE onboarding.partner_application_task (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_application_id uuid NOT NULL REFERENCES onboarding.partner_application(id) ON DELETE CASCADE,
  assigned_to_id uuid REFERENCES security.user_account(id),
  task_name varchar(180) NOT NULL,
  status_code varchar(50) NOT NULL DEFAULT 'OPEN',
  due_date date,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Ordinary Life setup

CREATE TABLE ol.default_system_parameter (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(80) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  parameter_value jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.computation_approach (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.override_commission_setup (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  agent_partner_id uuid REFERENCES partner.partner(id),
  product_id uuid,
  commission_rate numeric(9,6) NOT NULL DEFAULT 0,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.maturity_claim_setup (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  notification_days integer NOT NULL DEFAULT 30,
  auto_create_claim boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.plan_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.product (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  plan_type_id uuid REFERENCES ol.plan_type(id),
  description text,
  min_entry_age integer,
  max_entry_age integer,
  min_term_years integer,
  max_term_years integer,
  premium_frequency jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.tax_configuration (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  product_id uuid REFERENCES ol.product(id),
  tax_rate_id uuid REFERENCES core.tax_rate(id),
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.target_market (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.risk_category (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  risk_loading_percent numeric(9,6) NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.occupational_risk_limit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  risk_category_id uuid NOT NULL REFERENCES ol.risk_category(id),
  occupation_code varchar(80) NOT NULL,
  max_sum_assured numeric(18,2),
  referral_required boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (risk_category_id, occupation_code)
);

CREATE TABLE ol.investment_fund_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.investment_fund (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  fund_type_id uuid NOT NULL REFERENCES ol.investment_fund_type(id),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  currency_id uuid REFERENCES core.currency(id),
  unit_price numeric(18,6) NOT NULL DEFAULT 1,
  valuation_date date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.policy_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.policy_renewal_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.beneficiary_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.member_cover_configuration (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  cover_name varchar(150) NOT NULL,
  min_sum_assured numeric(18,2),
  max_sum_assured numeric(18,2),
  is_primary boolean NOT NULL DEFAULT true,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.surrender_setup (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  min_policy_months integer NOT NULL DEFAULT 0,
  surrender_charge_percent numeric(9,6) NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.surrender_value_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  policy_year integer NOT NULL,
  rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.paid_up_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  policy_year integer NOT NULL,
  rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.commitment_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.health_question (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  question_text text NOT NULL,
  answer_type varchar(30) NOT NULL DEFAULT 'BOOLEAN',
  referral_answer varchar(100),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.health_questionnaire (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  product_id uuid REFERENCES ol.product(id),
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.grace_period_notification_schedule (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  days_after_due integer NOT NULL,
  template_id uuid REFERENCES core.notification_template(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.reinstatement_window (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  max_lapse_months integer NOT NULL,
  requires_underwriting boolean NOT NULL DEFAULT true,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.premium_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES ol.product(id),
  age_from integer,
  age_to integer,
  term_from_years integer,
  term_to_years integer,
  sum_assured_from numeric(18,2),
  sum_assured_to numeric(18,2),
  rate numeric(18,8) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.mortality_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL,
  age integer NOT NULL,
  gender varchar(20),
  rate numeric(18,8) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (code, age, gender, effective_from)
);

CREATE TABLE ol.joint_life_setup (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  max_lives smallint NOT NULL DEFAULT 2,
  age_difference_limit integer,
  rate_factor numeric(9,6) NOT NULL DEFAULT 1,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.reinstatement_interest_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.bonus_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  rate numeric(9,6) NOT NULL,
  bonus_type varchar(50) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.mortgage_interest_factor (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  term_years integer NOT NULL,
  factor numeric(18,8) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.installment_charge_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  frequency varchar(30) NOT NULL,
  charge_rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.cash_surrender_value (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  policy_year integer NOT NULL,
  value_rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.reserve_loading (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  loading_rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.rider (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  is_mandatory boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.rider_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rider_id uuid NOT NULL REFERENCES ol.rider(id),
  product_id uuid REFERENCES ol.product(id),
  age_from integer,
  age_to integer,
  rate numeric(18,8) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.agent_commission_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  agent_partner_id uuid REFERENCES partner.partner(id),
  policy_year integer NOT NULL DEFAULT 1,
  rate numeric(9,6) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.loan_system_setup (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  max_loan_percent numeric(9,6) NOT NULL DEFAULT 0,
  min_policy_months integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.loan_interest_control (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  interest_rate numeric(9,6) NOT NULL,
  compounding_frequency varchar(30) NOT NULL DEFAULT 'MONTHLY',
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.medical_code (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  category varchar(80),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.medical_limit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES ol.product(id),
  age_from integer,
  age_to integer,
  sum_assured_from numeric(18,2),
  sum_assured_to numeric(18,2),
  required_action varchar(80) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.personal_habit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  risk_score integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.medical_facility (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id uuid REFERENCES partner.partner(id),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(200) NOT NULL,
  license_no varchar(80),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.medical_practitioner (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id uuid REFERENCES ol.medical_facility(id),
  code varchar(50) NOT NULL UNIQUE,
  full_name varchar(200) NOT NULL,
  license_no varchar(80),
  specialty varchar(120),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.claim_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.claim_reason (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  claim_type_id uuid REFERENCES ol.claim_type(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.claim_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_payable boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.discharge_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.correspondent_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Ordinary Life transactions

CREATE TABLE ol.quotation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  quotation_no varchar(80) NOT NULL UNIQUE,
  prospect_partner_id uuid REFERENCES partner.partner(id),
  agent_partner_id uuid REFERENCES partner.partner(id),
  product_id uuid NOT NULL REFERENCES ol.product(id),
  currency_id uuid REFERENCES core.currency(id),
  quotation_date date NOT NULL DEFAULT CURRENT_DATE,
  life_assured_name varchar(200) NOT NULL,
  date_of_birth date,
  gender varchar(20),
  term_years integer,
  sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  created_by_id uuid REFERENCES security.user_account(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.proposal (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_no varchar(80) NOT NULL UNIQUE,
  quotation_id uuid REFERENCES ol.quotation(id),
  proposer_partner_id uuid REFERENCES partner.partner(id),
  product_id uuid NOT NULL REFERENCES ol.product(id),
  proposal_date date NOT NULL DEFAULT CURRENT_DATE,
  sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  underwriting_status varchar(50) NOT NULL DEFAULT 'PENDING',
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  created_by_id uuid REFERENCES security.user_account(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.policy (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_no varchar(80) NOT NULL UNIQUE,
  proposal_id uuid REFERENCES ol.proposal(id),
  policyholder_id uuid NOT NULL REFERENCES partner.partner(id),
  product_id uuid NOT NULL REFERENCES ol.product(id),
  policy_status_id uuid NOT NULL REFERENCES ol.policy_status(id),
  currency_id uuid REFERENCES core.currency(id),
  commencement_date date NOT NULL,
  maturity_date date,
  premium_frequency varchar(30) NOT NULL,
  sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  modal_premium numeric(18,2) NOT NULL DEFAULT 0,
  annual_premium numeric(18,2) NOT NULL DEFAULT 0,
  agent_partner_id uuid REFERENCES partner.partner(id),
  created_by_id uuid REFERENCES security.user_account(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.policy_beneficiary (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id uuid NOT NULL REFERENCES ol.policy(id) ON DELETE CASCADE,
  beneficiary_type_id uuid REFERENCES ol.beneficiary_type(id),
  full_name varchar(200) NOT NULL,
  relationship varchar(80),
  share_percent numeric(9,6) NOT NULL DEFAULT 100,
  phone varchar(50),
  email varchar(254),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.commitment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  commitment_no varchar(80) NOT NULL UNIQUE,
  policy_id uuid REFERENCES ol.policy(id),
  commitment_status_id uuid REFERENCES ol.commitment_status(id),
  due_date date NOT NULL,
  amount numeric(18,2) NOT NULL,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.loan (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  loan_no varchar(80) NOT NULL UNIQUE,
  policy_id uuid NOT NULL REFERENCES ol.policy(id),
  loan_date date NOT NULL DEFAULT CURRENT_DATE,
  principal_amount numeric(18,2) NOT NULL,
  interest_rate numeric(9,6) NOT NULL,
  outstanding_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'ACTIVE',
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.withdrawal (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  withdrawal_no varchar(80) NOT NULL UNIQUE,
  policy_id uuid NOT NULL REFERENCES ol.policy(id),
  withdrawal_date date NOT NULL DEFAULT CURRENT_DATE,
  requested_amount numeric(18,2) NOT NULL,
  approved_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.claim (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_no varchar(80) NOT NULL UNIQUE,
  policy_id uuid NOT NULL REFERENCES ol.policy(id),
  claim_type_id uuid NOT NULL REFERENCES ol.claim_type(id),
  claim_reason_id uuid REFERENCES ol.claim_reason(id),
  claim_status_id uuid NOT NULL REFERENCES ol.claim_status(id),
  event_date date NOT NULL,
  notification_date date NOT NULL,
  claimed_amount numeric(18,2) NOT NULL DEFAULT 0,
  approved_amount numeric(18,2) NOT NULL DEFAULT 0,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  assigned_to_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ol.mutual_installment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  installment_no varchar(80) NOT NULL UNIQUE,
  policy_id uuid REFERENCES ol.policy(id),
  claim_id uuid REFERENCES ol.claim(id),
  due_date date NOT NULL,
  amount numeric(18,2) NOT NULL,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'PENDING',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Group Life setup and transactions

CREATE TABLE gl.scheme_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.scheme_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.scheme_member_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_covered boolean NOT NULL DEFAULT true,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.scheme_renewal_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.product (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  description text,
  min_entry_age integer,
  max_entry_age integer,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.sub_product (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES gl.product(id),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.scheme_premium_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_type_id uuid REFERENCES gl.scheme_type(id),
  product_id uuid NOT NULL REFERENCES gl.product(id),
  age_from integer,
  age_to integer,
  sum_assured_from numeric(18,2),
  sum_assured_to numeric(18,2),
  rate numeric(18,8) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.rider (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_mandatory boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.rider_rate (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rider_id uuid NOT NULL REFERENCES gl.rider(id),
  product_id uuid REFERENCES gl.product(id),
  rate numeric(18,8) NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.medical_code (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  category varchar(80),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.medical_limit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid REFERENCES gl.product(id),
  age_from integer,
  age_to integer,
  sum_assured_from numeric(18,2),
  sum_assured_to numeric(18,2),
  required_action varchar(80) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.underwriting_decision (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_acceptance boolean NOT NULL DEFAULT false,
  is_decline boolean NOT NULL DEFAULT false,
  is_referral boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.personal_habit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  risk_score integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.medical_facility (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id uuid REFERENCES partner.partner(id),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(200) NOT NULL,
  license_no varchar(80),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.medical_practitioner (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id uuid REFERENCES gl.medical_facility(id),
  code varchar(50) NOT NULL UNIQUE,
  full_name varchar(200) NOT NULL,
  license_no varchar(80),
  specialty varchar(120),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.claim_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.claim_reason (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  claim_type_id uuid REFERENCES gl.claim_type(id),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.claim_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_terminal boolean NOT NULL DEFAULT false,
  is_payable boolean NOT NULL DEFAULT false,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.discharge_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.correspondent_type (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.health_question (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  question_text text NOT NULL,
  answer_type varchar(30) NOT NULL DEFAULT 'BOOLEAN',
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.health_questionnaire (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(50) NOT NULL UNIQUE,
  name varchar(150) NOT NULL,
  product_id uuid REFERENCES gl.product(id),
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.quotation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  quotation_no varchar(80) NOT NULL UNIQUE,
  policyholder_id uuid NOT NULL REFERENCES partner.partner(id),
  broker_id uuid REFERENCES partner.partner(id),
  product_id uuid NOT NULL REFERENCES gl.product(id),
  sub_product_id uuid REFERENCES gl.sub_product(id),
  scheme_type_id uuid REFERENCES gl.scheme_type(id),
  currency_id uuid REFERENCES core.currency(id),
  quotation_date date NOT NULL DEFAULT CURRENT_DATE,
  effective_from date,
  effective_to date,
  member_count integer NOT NULL DEFAULT 0,
  total_sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  created_by_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.scheme (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_no varchar(80) NOT NULL UNIQUE,
  quotation_id uuid REFERENCES gl.quotation(id),
  policyholder_id uuid NOT NULL REFERENCES partner.partner(id),
  product_id uuid NOT NULL REFERENCES gl.product(id),
  sub_product_id uuid REFERENCES gl.sub_product(id),
  scheme_type_id uuid NOT NULL REFERENCES gl.scheme_type(id),
  scheme_status_id uuid NOT NULL REFERENCES gl.scheme_status(id),
  currency_id uuid REFERENCES core.currency(id),
  start_date date NOT NULL,
  end_date date NOT NULL,
  member_count integer NOT NULL DEFAULT 0,
  total_sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  annual_premium numeric(18,2) NOT NULL DEFAULT 0,
  created_by_id uuid REFERENCES security.user_account(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.scheme_member (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_id uuid NOT NULL REFERENCES gl.scheme(id) ON DELETE CASCADE,
  member_no varchar(80) NOT NULL,
  member_status_id uuid NOT NULL REFERENCES gl.scheme_member_status(id),
  full_name varchar(200) NOT NULL,
  national_id varchar(80),
  date_of_birth date,
  gender varchar(20),
  sum_assured numeric(18,2) NOT NULL DEFAULT 0,
  premium_amount numeric(18,2) NOT NULL DEFAULT 0,
  cover_start_date date NOT NULL,
  cover_end_date date NOT NULL,
  underwriting_decision_id uuid REFERENCES gl.underwriting_decision(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scheme_id, member_no)
);

CREATE TABLE gl.scheme_renewal (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_id uuid NOT NULL REFERENCES gl.scheme(id) ON DELETE CASCADE,
  renewal_status_id uuid NOT NULL REFERENCES gl.scheme_renewal_status(id),
  renewal_no varchar(80) NOT NULL UNIQUE,
  due_date date NOT NULL,
  renewal_from date,
  renewal_to date,
  quoted_premium numeric(18,2) NOT NULL DEFAULT 0,
  renewed_premium numeric(18,2) NOT NULL DEFAULT 0,
  assigned_to_id uuid REFERENCES security.user_account(id),
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.claim (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_no varchar(80) NOT NULL UNIQUE,
  scheme_id uuid NOT NULL REFERENCES gl.scheme(id),
  scheme_member_id uuid REFERENCES gl.scheme_member(id),
  claim_type_id uuid NOT NULL REFERENCES gl.claim_type(id),
  claim_reason_id uuid REFERENCES gl.claim_reason(id),
  claim_status_id uuid NOT NULL REFERENCES gl.claim_status(id),
  event_date date NOT NULL,
  notification_date date NOT NULL,
  claimed_amount numeric(18,2) NOT NULL DEFAULT 0,
  approved_amount numeric(18,2) NOT NULL DEFAULT 0,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  assigned_to_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gl.claim_installment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id uuid NOT NULL REFERENCES gl.claim(id) ON DELETE CASCADE,
  installment_no integer NOT NULL,
  due_date date NOT NULL,
  amount numeric(18,2) NOT NULL,
  paid_amount numeric(18,2) NOT NULL DEFAULT 0,
  payment_status varchar(50) NOT NULL DEFAULT 'PENDING',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (claim_id, installment_no)
);

CREATE TABLE gl.medical_invoice (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_no varchar(80) NOT NULL UNIQUE,
  facility_id uuid REFERENCES gl.medical_facility(id),
  practitioner_id uuid REFERENCES gl.medical_practitioner(id),
  scheme_id uuid REFERENCES gl.scheme(id),
  scheme_member_id uuid REFERENCES gl.scheme_member(id),
  claim_id uuid REFERENCES gl.claim(id),
  invoice_date date NOT NULL,
  invoice_amount numeric(18,2) NOT NULL DEFAULT 0,
  payable_amount numeric(18,2) NOT NULL DEFAULT 0,
  currency_id uuid REFERENCES core.currency(id),
  status_code varchar(50) NOT NULL DEFAULT 'DRAFT',
  created_by_id uuid REFERENCES security.user_account(id),
  approved_by_id uuid REFERENCES security.user_account(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE VIEW gl.v_schemes_due_for_renewal AS
SELECT
  s.id AS scheme_id,
  s.scheme_no,
  p.legal_name AS policyholder_name,
  st.name AS scheme_status,
  s.end_date AS renewal_due_date,
  s.annual_premium,
  s.member_count,
  COALESCE(r.renewal_no, '') AS latest_renewal_no,
  rs.name AS renewal_status,
  r.assigned_to_id
FROM gl.scheme s
JOIN partner.partner p ON p.id = s.policyholder_id
JOIN gl.scheme_status st ON st.id = s.scheme_status_id
LEFT JOIN LATERAL (
  SELECT sr.*
  FROM gl.scheme_renewal sr
  WHERE sr.scheme_id = s.id
  ORDER BY sr.due_date DESC, sr.created_at DESC
  LIMIT 1
) r ON true
LEFT JOIN gl.scheme_renewal_status rs ON rs.id = r.renewal_status_id
WHERE s.end_date >= CURRENT_DATE;
