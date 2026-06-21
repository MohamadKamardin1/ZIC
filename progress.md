# ZIC Core Life Insurance Platform — Progress & Project Map

## Project Identity

| Field | Value |
|---|---|
| **Product** | ZIC Core Life Insurance Platform |
| **Client** | Zanzibar Insurance Corporation |
| **Stack** | Django 5+ / DRF / PostgreSQL / Celery / Redis |
| **API Style** | REST (JWT + OAuth2) |
| **Deployment** | Docker + Nginx |
| **Root** | `/Users/phantomx/Desktop/ZIC` |

---

## Full Module Map (from SRS)

The system shall cover **10 business modules**. Each maps to a planned Django app:

| # | Business Module | Django App | Status |
|---|---|---|---|
| 1 | Dashboard | `dashboard` | **Stub** (views.py empty) |
| 2 | Partner Onboarding | `partner_onboarding` | **Not created** |
| 3 | Partners | `partners` | **Stub** (model has only `name`, views empty) |
| 4 | Ordinary Life | `ordinary_life` | **Not created** |
| 5 | Group Life | `group_life` | **Not created** |
| 6 | Group Credit | `group_credit` | **Not created** |
| 7 | Front Office | `front_office` | **Not created** |
| 8 | Reports | `reports` | **Not created** |
| 9 | System Parameters | `parameters` | **Not created** |
| 10 | Approval | `approvals` | **Not created** |

**Supporting cross-cutting apps:**

| App | Purpose | Status |
|---|---|---|
| `users` | User model, groups, permissions, sessions, 2FA, OTP, activity logs | **Complete** |
| `authentication` | Login/logout/register, JWT refresh, password reset, 2FA, OTP verify | **Complete** |
| `core` | Exceptions, middleware, pagination, permissions, logging, health check | **Complete** |
| `security_management` | Proxy models for admin UI (sessions, OTP, 2FA) | **Complete** |
| `user_management` | Proxy models for admin UI (users, groups, permissions) | **Complete** |
| `audit_management` | Proxy model for admin UI (activity logs) | **Complete** |
| `common` | Shared app config placeholder | **Complete** |
| `config` | Project settings (base/dev/staging/prod), Celery, URL routing | **Complete** |

---

## Detailed Implementation Status

### 1. Infrastructure — COMPLETE

| Layer | Files | Notes |
|---|---|---|
| Settings | `config/settings/base.py`, `development.py`, `staging.py`, `production.py` | 12-factor env-based config |
| Routing | `config/urls.py` | API v1 with health, auth, users, partners, dashboard; Swagger/Redoc |
| ASGI/WSGI | `config/asgi.py`, `config/wsgi.py` | Ready for async + sync deployment |
| Celery | `config/celery.py` | Auto-discovers tasks; Redis broker |
| Docker | `Dockerfile`, `docker-compose.yml`, `nginx.conf` | Production-ready containerization |
| Requirements | `requirements/base.txt`, `development.txt`, `staging.txt`, `production.txt`, `requirements.lock.txt` | Split by environment |
| Static | `static/admin/css/material3.css` | Material 3 theme for Django admin |
| Tests | `pytest.ini` | Configured for pytest |

### 2. Core Framework — COMPLETE

| Component | File | Lines |
|---|---|---|
| Exception handler | `apps/core/exceptions.py` | 79 |
| Custom exception class | `ZICAPIException` | — |
| Middleware (request ID) | `apps/core/middleware.py` | 58 |
| Middleware (request logging) | `apps/core/middleware.py` | — |
| Middleware (user activity) | `apps/core/middleware.py` | — |
| Permissions | `apps/core/permissions.py` | 38 |
| Pagination | `apps/core/pagination.py` | 28 |
| Health check | `apps/core/views.py` | 42 |
| Log formatter | `apps/core/logging.py` | 55 |

**Key conventions enforced across all endpoints:**
- Standard response envelope: `{success, status_code, message, data, meta}`
- Paginated responses include `{page, per_page, total, pages}`
- Error responses use `{success, status_code, error: {code, message, details}, meta}`
- CamelCase JSON renderer/parser (via `djangorestframework_camel_case`)

### 3. Users & Authentication — COMPLETE

#### Models (apps/users/models.py — 470 lines)

| Model | Purpose |
|---|---|
| `User` | Custom user with UUID PK, 7 user types, 2FA fields, password expiry, account lockout |
| `UserGroup` | Named groups (PORTAL_USER, MANAGER, etc.) with permissions M2M |
| `UserPermission` | Granular CRUD+APPROVE+EXPORT per module/resource |
| `PermissionGroup` | Named permission bundles per module |
| `UserSession` | Device-aware session tracking (WEB/MOBILE/TABLET/API) |
| `UserActivityLog` | Immutable audit trail (login, logout, password change, 2FA, etc.) |
| `UserOTP` | OTP with expiry, type (LOGIN, PASSWORD_RESET, EMAIL_VERIFICATION, PHONE_VERIFICATION) |
| `TwoFactorAuth` | TOTP secret storage + backup codes |
| `NotificationPreference` | Per-user email/SMS/push notification toggles |

#### API Endpoints — Authentication (apps/authentication/)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/auth/login/` | POST | None | Login with optional 2FA OTP |
| `/api/v1/auth/logout/` | POST | JWT | Blacklist token + invalidate sessions |
| `/api/v1/auth/refresh/` | POST | None | Refresh JWT |
| `/api/v1/auth/register/` | POST | None | Self-registration (requires approval) |
| `/api/v1/auth/verify-email/` | POST | None | Verify email via OTP |
| `/api/v1/auth/reset-password/` | POST | None | Request password reset OTP |
| `/api/v1/auth/confirm-reset-password/` | POST | None | Confirm reset with OTP |
| `/api/v1/auth/change-password/` | POST | JWT | Authenticated password change |
| `/api/v1/auth/setup-2fa/` | POST | JWT | Generate TOTP secret + QR code |
| `/api/v1/auth/verify-2fa/` | POST | JWT | Verify TOTP to enable 2FA |
| `/api/v1/auth/disable-2fa/` | POST | JWT | Disable 2FA (password required) |
| `/api/v1/auth/request-otp/` | POST | None | Request login OTP |
| `/api/v1/auth/verify-otp/` | POST | None | Verify login OTP |

#### API Endpoints — Users (apps/users/)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/users/users/` | GET/POST | JWT | List/create users |
| `/api/v1/users/users/{id}/` | GET/PUT/PATCH/DELETE | JWT | Retrieve/update/deactivate user |
| `/api/v1/users/users/me/` | GET | JWT | Current user profile |
| `/api/v1/users/users/update_profile/` | PUT/PATCH | JWT | Update own profile |
| `/api/v1/users/users/change_password/` | POST | JWT | Change password |
| `/api/v1/users/users/{id}/deactivate/` | POST | JWT+Admin | Deactivate user |
| `/api/v1/users/users/{id}/activate/` | POST | JWT+Admin | Activate user |
| `/api/v1/users/groups/` | GET/POST | JWT+Admin | List/create groups |
| `/api/v1/users/groups/{id}/assign_permissions/` | POST | JWT+Admin | Assign permissions |
| `/api/v1/users/groups/{id}/remove_permissions/` | POST | JWT+Admin | Remove permissions |
| `/api/v1/users/permissions/` | GET | JWT | List permissions |
| `/api/v1/users/permissions/modules/` | GET | JWT | List unique modules |
| `/api/v1/users/permission-groups/` | GET/POST | JWT+Admin | List/create permission groups |
| `/api/v1/users/sessions/` | GET | JWT | List own sessions (admin: all) |
| `/api/v1/users/sessions/revoke/` | POST | JWT | Revoke a session |
| `/api/v1/users/audit-logs/` | GET | JWT+Admin | List activity logs |

#### Signals (apps/users/signals.py)
- Auto-create `NotificationPreference` on User creation
- Auto-create `TwoFactorAuth` when `is_2fa_enabled` flips to True
- Log user creation in activity log

#### Tasks (apps/users/tasks.py)
- `send_otp_email` — Celery task (stub, logs only)
- `send_otp_sms` — Celery task (stub, logs only)
- `cleanup_expired_sessions` — Celery periodic task
- `cleanup_expired_otps` — Celery periodic task
- `password_expiry_reminder` — Celery periodic task
- `send_welcome_email` — Celery task (stub, logs only)

#### Validators (apps/users/validators.py)
- `ComplexPasswordValidator` — enforces uppercase, lowercase, digit, special char
- `PasswordHistoryValidator` — prevents reuse of last N passwords

#### Tests (apps/users/tests.py — 510 lines)
- User model tests
- Authentication flow tests
- Permission tests
- Session management tests
- 2FA tests

### 4. Partners — STUB

| File | Lines | Content |
|---|---|---|
| `apps/partners/models.py` | 15 | `Partner` model with only `id`, `name`, `created_at` |
| `apps/partners/views.py` | 0 | Empty |
| `apps/partners/urls.py` | 3 | Empty router registration |
| `apps/partners/admin.py` | 7 | Basic admin registration |

### 5. Dashboard — STUB

| File | Lines | Content |
|---|---|---|
| `apps/dashboard/views.py` | 0 | Empty |
| `apps/dashboard/urls.py` | 3 | Empty router registration |

### 6. Business Modules — NOT STARTED (9 apps missing)

The following apps do **not exist** in the codebase at all:

| Missing App | Must Contain (from SRS) |
|---|---|
| `ordinary_life` | Quotations, commitments, proposals, policies, loans, withdrawals, claims, mutual installments; 9 parameter groups (default setup, policy setup, product setup, product rating, riders, agents, loans, medical, claims) |
| `group_life` | Quotations, schemes, renewals, claims, claim installments, medical invoices; 6 parameter groups (scheme, product, rider, medical, claim, medical invoice) |
| `group_credit` | Quotations, schemes, renewals, claims, claim installments, medical invoices; 6 parameter groups (same structure as GL + lender/loan fields) |
| `front_office` | Receipts, commissions, commission statements, requisitions, payments, reversals; front office parameters |
| `reinsurance` | Departments, classes, treaties, treaty participants, cessions, processing dashboard |
| `reports` | Report definitions, report runs, export services |
| `parameters` | General parameters (company, branches, currency, tax, numbering, documents, notification templates) |
| `approvals` | Approval types, process types, rules, processes, roles, approvers, approval requests, actions |
| `partner_onboarding` | Applications, documents, verification tasks, review, approval, conversion to partner |

---

## Database Status

### PostgreSQL Schema (doc/postgresql_schema.sql — 2472 lines)
A complete DDL design exists covering **12 schemas** with ~150+ tables, indexes, triggers, and views:

| Schema | Tables | Status in Django |
|---|---|---|
| `core` | currency, branch, company_parameter, tax_rate, number_sequence, document_type, notification_template, audit_log | **Not implemented** |
| `security` | user_account, permission, permission_group, user_group, user_preference | Partial (users app models exist but don't use this schema) |
| `approval` | approval_type, approval_process_type, approval_status, approval_role, approver, approval_rule, approval_process, approval, approval_action | **Not implemented** |
| `partner` | partner_type, partner, partner_contact, partner_bank_account | **Stub** (Partner model exists with only name) |
| `onboarding` | partner_application, partner_application_document, partner_application_task | **Not implemented** |
| `dashboard` | widget, user_widget | **Not implemented** |
| `ol` | 40+ tables (quotation, proposal, policy, policy_beneficiary, commitment, loan, withdrawal, claim, mutual_installment, product_setup, riders, rates, medical, etc.) | **Not implemented** |
| `gl` | scheme_type, scheme_status, product, sub_product, premium_rate, rider, medical, quotation, scheme, scheme_member, scheme_renewal, claim, claim_installment, medical_invoice + view | **Not implemented** |
| `gc` | Same structure as GL + lender_id, loan_reference, loan_amount, outstanding_balance | **Not implemented** |
| `front_office` | receipt_type, payment_method, transaction_status, requisition_type, commission_rule, receipt, receipt_allocation, commission, commission_statement, commission_statement_line, requisition, payment | **Not implemented** |
| `reinsurance` | department, class, treaty_type, treaty_code, underwriting_year, business_type, branch, ceded_premium_rate, treaty_participant, proportional_treaty, non_proportional_treaty, cession, processing_batch + view | **Not implemented** |
| `reporting` | report_definition, report_run | **Not implemented** |

**Current Django database**: SQLite (`db.sqlite3`) — only contains users app migrations.

---

## What AI Sessions Need to Know for Next Steps

### Architecture Decisions (already in place)
1. **Response format**: All API responses follow `{success, status_code, message, data, meta}` envelope
2. **Pagination**: `StandardPagination` returns `{page, per_page, total, pages}` in pagination key
3. **Auth**: JWT (15min access / 7d refresh) + OAuth2 + Session; 2FA via TOTP
4. **Permissions**: `IsAdminUser`, `IsOwnerOrAdmin`, `HasModulePermission(module_code, action)`
5. **Error handling**: `custom_exception_handler` wraps all errors in standard format
6. **Middleware stack**: Request ID → CORS → Security → WhiteNoise → Session → Auth → CSRF → Axes → CSP → RequestLogging → UserActivity
7. **Logging**: Structured JSON logs with rotation (info/error/debug files + console)
8. **Naming**: CamelCase JSON (via `djangorestframework_camel_case`)

### Priority Order for Building Remaining Apps
1. **`parameters`** — Foundational: company, branch, currency, tax, numbering sequences (used by everything)
2. **`partners`** — Expand stub: partner types, contacts, bank accounts (used by OL, GL, GC, FO)
3. **`partner_onboarding`** — Application workflow that feeds into partners
4. **`ordinary_life`** — Core business (largest module, 40+ tables)
5. **`group_life`** — Second core business
6. **`group_credit`** — Similar structure to GL
7. **`front_office`** — Receipts, commissions, payments
8. **`approvals`** — Cross-cutting approval engine
9. **`reinsurance`** — Treaty management and cessioning
10. **`reports`** — Report definitions and execution
11. **`dashboard`** — Widget aggregation (depends on everything else having data)

### Implementation Pattern to Follow
Each new app should follow the established pattern:
```
apps/{module}/
  __init__.py
  apps.py
  admin.py
  models.py          # Django models (reflect PostgreSQL schema)
  serializers.py     # DRF serializers
  views.py           # DRF viewsets
  urls.py            # Router registration
  filters.py         # (optional) django-filters
  services/          # Business logic (pricing, underwriting, claims, etc.)
  migrations/
  tests/
```

### Key Files Already Designed
- `doc/postgresql_schema.sql` — Complete DDL for all 12 schemas (convert to Django models)
- `doc/SRS.md` — Full functional requirements for all 10 modules
- `doc/django_app_structure.md` — Recommended app layout, module mapping, API structure
- `doc/*.xlsx` — Module menus and partner templates (binary, open with Excel)

### Environment Variables Required
See `backend/.env.example` for the full list (Django, DB, Redis, JWT, email, SMS, Sentry, CORS, logging).

---

## Complete Menu Hierarchy (from Core Life Modules Menus.xlsx)

### 1. Dashboard

### 2. Partner Onboarding
- Partners

### 3. Ordinary Life
- Ordinary Life Quotations
- Ordinary Life Commitments
- Ordinary Life Proposals
- Ordinary Life Policies
- Ordinary Life Loans
- Ordinary Life Withdrawals
- Ordinary Life Claims
- Maturity Installments
- **Ordinary Life Parameters**
  - **OL Default Setups**
    - OL Default System Parameters
    - Override Commission Setup
    - Computation Approach
    - Maturity Claims Setup
  - **OL Policy Setup**
    - Anticipated Endowment Installment Rates
    - OL Grace Period
    - OL Policy Statuses
    - OL Policy Renewal Status
    - OL Beneficiary Types
    - OL Member Cover Configuration
    - OL Surrender Setup
    - OL Paid Up Setup
    - OL Surrender Value Rates
    - OL Paid Up Rates
    - OL Commitment Statuses
    - OL Health Questions
    - OL Health Questionnaire
    - Grace Period Notification Schedule
    - Reinstatement Window
  - **OL Product Setup**
    - OL Plan Types
    - OL Products
    - Plan Tax Configurations
    - Plan Target Markets
    - Plan Risk Categories
    - Plan Occupational Risk Limits
    - Investment Fund Types
    - Investment Funds
  - **OL Product Rating**
    - OL Premium Rates
    - OL Mortality Rates
    - OL Joint Life Setup
    - Reinstatement Interest Rates
    - OL Bonus Rates
    - OL Mortgage Interest Factor
    - Installment Charge Rates
    - OL Cash Surrender Value
    - OL Reserve Loadings
  - **OL Rider Setup**
    - OL Riders
    - OL Rider Rates
  - **OL Agent Management**
    - Agent Commission Rates
  - **OL Loan Setup**
    - OL Loan System Setup
    - OL Loan Interest Control
  - **OL Medical U/W**
    - OL Medical Codes
    - OL Medical Limits
    - OL Personal Habits
    - OL Medical History
    - OL Medical Facilities
    - OL Medical Practitioners
  - **OL Claim Setup**
    - OL Claim Types
    - OL Claim Reasons
    - OL Claim Statuses
    - OL Discharge Types
    - OL Correspondent Types

### 4. Group Life
- Group Life Quotations
- Group Life Schemes
- GL Schemes Due For Renewal
- Group Life Claims
- GL Claim Installments
- **Group Life Parameters**
  - **GL Scheme Setup**
    - GL Scheme Types
    - GL Scheme Premium Rates
    - GL Scheme Member Status
    - GL Scheme Status
    - GL Scheme Renewal Status
    - Health Questions
    - Health Questionnaire
  - **GL Product Setup**
    - GL Sub-Products
    - GL Products
  - **GL Rider Setup**
    - GL Riders
    - GL Rider Rates
  - **GL Medical U/W**
    - GL Medical Codes
    - GL Medical Limits
    - GL Underwriting Decision
    - GL Personal Habits
    - GL Medical History
    - GL Medical Facilities
    - GL Medical Practitioners
  - **GL Claim Setup**
    - GL Claim Types
    - GL Claim Reasons
    - GL Claim Statuses
    - GL Discharge Types
    - GL Correspondent Types
  - **GL Medical Invoice**

### 5. Group Credit
- Group Credit Quotations
- Group Credit Schemes
- GC Schemes Due For Renewal
- Group Credit Claims
- GC Claim Installments
- **Group Credit Parameters**
  - **GC Scheme Setup**
    - GC Scheme Types
    - GC Scheme Premium Rates
    - GC Scheme Member Status
    - GC Scheme Status
    - GC Scheme Renewal Status
    - Health Questions
    - Health Questionnaire
  - **GC Product Setup**
    - GC Sub-Products
    - GC Products
  - **GC Rider Setup**
    - GC Riders
    - GC Rider Rates
  - **GC Medical U/W**
    - GC Medical Codes
    - GC Medical Limits
    - GC Underwriting Decision
    - GC Personal Habits
    - GC Medical History
    - GC Medical Facilities
    - GC Medical Practitioners
  - **GC Claim Setup**
    - GC Claim Types
    - GC Claim Reasons
    - GC Claim Statuses
    - GC Discharge Types
    - GC Correspondent Types
  - **GC Medical Invoice**

### 6. Front Office
- Receipts
- Commissions
- Commission Statement
- Requisitions
- Payments
- Front Office Parameters

### 7. Reports

### 8. System Parameters
- General Parameters
- Partner Parameters
- User Parameters
- **Reinsurance Parameters**
  - Reinsurance Processing Dashboard
  - Reinsurance Departments
  - Reinsurance Classes
  - Treaty Types
  - Treaty Codes
  - Underwriting Years
  - Ceded Premium Rates
  - Reinsurance Business Types
  - Reinsurance Branches
  - Treaty Participants
  - Proportional Treaty Setup
  - Proportional Class-Wise Cessioning
  - Non-Proportional Treaty Setup
  - Non-Proportional Classwise Cession

### 9. User Management
- Permission Groups
- Permissions
- User Groups
- Users

### 10. Approval
- Approvals
- Approval Types
- Approval Process Types
- Approval Rules
- Approval Processes
- Approver Roles
- Approvers
- Approval Status

---

## Partners Portal Menu (from Partners Portal Modules Menus.xlsx)

The partners portal has a separate, simplified menu:

- Dashboard
- **Group Life**
  - Group Life Schemes
  - Group Life Quotations
- **Group Credit**
  - Group Credit Schemes
  - Group Credit Quotations
  - Group Credit Loans
- **Claims**
  - Claims List
- **Approvals**
  - Approvals
  - Approval Types
  - Approval Process Types
  - Approval Rules
  - Approval Processes
  - Approver Roles
  - Approvers
  - Approval Status
- **System Parameters**
  - General Parameters
  - **Integration Parameters**
    - Integrations
    - API Clients
  - **User Management**
    - User Groups
    - Users
    - Permissions
    - Permission Groups
    - Permission Access Types
    - Password Policy
  - Feedback Parameters
  - Styles
- Help and Support

---

## Partner Templates (from Individual_Partners_Template.xlsx & Corporate_Partners_Template.xlsx)

### Individual Partner Fields
- Partner Type, Identification Type, Identification Number, Gender, Title, First Name, Other Name, Surname, Email, Telephone Number, Mobile Number, Nationality, Date of Birth, Political Risk, Anti-Money Laundering, Marital Status, Occupation

**Lookup values for Individual Partners:**
- **Identification Types**: National Identification Number, ZAN ID, Passport Number, Driving License, TIN Number, Voter ID, Resident Permit, Military ID
- **Titles**: Mr, Mrs, Miss, Ms, Dr, Prof, Hon, Eng, Rev
- **Gender**: Male, Female
- **Marital Status**: Single, Married, Divorced, Widowed, Separated
- **Nationalities**: ~220 nationalities (Afghan to Zimbabwean)
- **Political Risk**: Low (Normal citizen), Medium (Public influence), High (Senior public official), PEP (Politically Exposed Person)
- **AML Risk**: Low, Medium, High

### Corporate Partner Fields
- Partner Type, Company Name, Email, Telephone Number, Mobile Number, TIN Number, Industry, Incorporation Date, Contact Person, Contact Person Phone, Contact Person Email, Physical Address, Postal Address, Political Risk, AML Risk

**Lookup values for Corporate Partners:**
- **Industries**: Technology, Healthcare & Pharmaceuticals, Financial Services & Banking, Consumer Goods & Retail, Energy & Utilities, Manufacturing & Industrial, Telecommunications, Transportation & Logistics, Real Estate & Construction, Media & Entertainment, Aerospace & Defense, Automotive, Agriculture & Food Production, Hospitality & Tourism, Education & Training, Professional Services & Consulting, Insurance, Mining & Metals, Chemicals, Textiles & Apparel, Environmental Services, Biotechnology, E-commerce, Renewable Energy, Cybersecurity, AI & ML, Fintech, Life Sciences, Oil & Gas, Consumer Electronics

---

---

## Frontend — zic-aims-dashboard (Lit + TypeScript + Vite)

### Project Overview

| Field | Value |
|---|---|
| **Location** | `/Users/phantomx/Desktop/ZIC/zic-aims-dashboard` |
| **Framework** | Lit 3.1 (Web Components, NOT React) |
| **Build** | Vite 5 + TypeScript (strict) |
| **Styling** | Tailwind CSS 3.4 + Material Design 3 tokens + Vintage theme |
| **State** | Custom reactive stores with subscriber pattern + Lit ReactiveControllers |
| **Router** | Custom client-side router (History API, auth/permission guards) |
| **API** | Class-based Axios layer with interceptors, auto token refresh |
| **Testing** | Vitest (configured) |
| **Total source files** | 67 (.ts + .css) |

### Source File Inventory (67 files)

```
src/
├── main.ts                          # Entry: init auth, notifications, mount app
├── app.ts                           # Root LitElement: layout, routing, sidebar, header
│
├── config/
│   ├── api.config.ts                # All microservice URLs and endpoint definitions
│   ├── auth.config.ts               # TokenManager, SessionManager
│   ├── microservices.config.ts      # Microservice registry
│   └── theme.config.ts              # Theme constants
│
├── constants/
│   ├── app.constants.ts             # App name, company, date/time formats, storage keys, icons
│   ├── messages.constants.ts        # UI messages
│   └── routes.constants.ts          # All route paths + permissions map + public route list
│
├── types/
│   ├── api.types.ts                 # API response envelope types
│   ├── auth.types.ts                # Auth request/response types
│   ├── common.types.ts              # Shared types (pagination, filters, etc.)
│   └── dashboard.types.ts           # Dashboard widget types
│
├── core/
│   ├── api/
│   │   ├── base.api.ts              # BaseAPI class with Axios, interceptors, token refresh
│   │   ├── auth.api.ts              # Auth endpoints (login, logout, 2FA, etc.)
│   │   ├── dashboard.api.ts         # Dashboard data endpoints
│   │   └── index.ts                 # API barrel exports
│   ├── router/
│   │   ├── router.ts                # Custom Router class + RouterController (Lit controller)
│   │   ├── routes.ts                # Route definitions array
│   │   └── guards/
│   │       └── index.ts             # Auth guards
│   ├── services/
│   │   ├── auth.service.ts          # AuthService: login, logout, refresh, 2FA, password
│   │   ├── dashboard.service.ts     # DashboardService: fetch overview, policies, claims
│   │   └── notification.service.ts  # NotificationService: SSE-based real-time
│   ├── store/
│   │   ├── auth.store.ts            # AuthStore (reactive) + AuthStoreController
│   │   ├── app.store.ts             # AppStore (sidebar, theme, breadcrumbs) + controller
│   │   └── dashboard.store.ts       # DashboardStore (overview, widgets) + controller
│   └── utils/
│       ├── currency.utils.ts        # TZS currency formatting
│       ├── date.utils.ts            # date-fns helpers
│       ├── format.utils.ts          # String/number formatting
│       └── validators.ts            # Zod-based form validators
│
├── components/
│   ├── common/
│   │   ├── zic-button.ts            # Reusable button component
│   │   ├── zic-card.ts              # Card container
│   │   ├── zic-input.ts             # Text input component
│   │   ├── zic-modal.ts             # Modal/dialog component
│   │   └── zic-toast.ts             # Toast notification component
│   ├── layout/
│   │   ├── zic-header.ts            # Header: breadcrumbs, search, notifications, user menu
│   │   └── zic-sidebar.ts           # Sidebar: collapsible nav with sections, icons, badges
│   └── icons/                       # SVG icon definitions
│
├── features/
│   ├── auth/
│   │   ├── login/login-page.ts      # Login page (719 lines, animated background, 2FA support)
│   │   ├── forgot-password/forgot-password-page.ts  # Forgot password page
│   │   └── reset-password-page.ts   # Reset password page
│   │
│   ├── dashboard/
│   │   ├── dashboard-page.ts        # Dashboard (stats grid, charts, recent lists)
│   │   ├── dashboard-header.ts      # Dashboard header component
│   │   ├── dashboard-data.ts        # Dashboard data models
│   │   └── dashboard-sidebar.ts     # Dashboard sidebar config
│   │
│   ├── partner-onboarding/
│   │   ├── partner-onboarding-page.ts       # Partner onboarding page
│   │   ├── partner-applications-list.ts     # Applications list with filters
│   │   ├── partner-application-detail.ts   # Application detail view
│   │   ├── partner-application-create.ts   # Create application form
│   │   ├── partners-list.ts                # Partners directory list
│   │   └── partner-detail.ts              # Partner detail view
│   │
│   ├── ordinary-life/
│   │   ├── ordinary-life-page.ts           # OL page (placeholder/stub)
│   │   ├── ordinary-policies-list.ts       # Policies list
│   │   ├── ordinary-quotations-list.ts     # Quotations list
│   │   └── ordinary-claims-list.ts         # Claims list
│   │
│   ├── group-life/
│   │   ├── group-life-page.ts              # GL page (placeholder/stub)
│   │   └── group-policies-list.ts          # Policies list
│   │
│   ├── group-credit/                       # Directory exists — EMPTY (no .ts files)
│   ├── front-office/                       # Directory exists — EMPTY (no .ts files)
│   │
│   ├── reports/
│   │   └── reports-page.ts                 # Reports page (placeholder)
│   ├── user-management/
│   │   └── user-management-page.ts         # User management page (placeholder)
│   ├── system-parameters/
│   │   └── system-parameters-page.ts       # System params page (placeholder)
│   ├── approvals/
│   │   └── approvals-page.ts               # Approvals page (placeholder)
│   ├── errors/
│   │   ├── not-found-page.ts               # 404 page
│   │   ├── forbidden-page.ts               # 403 page
│   │   └── server-error-page.ts            # 500 page
│
└── styles/
    ├── global.css                  # Global styles + Tailwind directives
    ├── material-3-tokens.css        # MD3 CSS custom properties (color, typography, elevation, shape, motion)
    ├── utilities.css                # Utility classes
    └── vintage-theme.css            # Vintage ZIC theme (gold, copper, teal, coral, sage accents)
```

### Frontend Architecture Summary

| Layer | Implementation | Status |
|---|---|---|
| **Routing** | Custom Router with History API, param extraction, auth guards, Lit ReactiveController | **Complete** |
| **State Management** | Custom reactive stores (pub/sub pattern) with Lit ReactiveControllers for auto re-render | **Complete** |
| **API Layer** | Axios-based BaseAPI with request/response interceptors, auto token refresh, error handling | **Complete** |
| **Auth Service** | Token management, login/logout/refresh/2FA flows, session management | **Complete** |
| **Design System** | Material Design 3 full token set + Vintage theme (gold/copper/teal/coral) + Tailwind | **Complete** |
| **Shared Components** | zic-button, zic-input, zic-card, zic-modal, zic-toast, zic-sidebar, zic-header | **Complete** |
| **Auth Pages** | Login (719 lines with animated background), forgot password, reset password | **Complete** |
| **Dashboard Page** | Stats grid, recent policies/claims/applications lists, Chart.js integration | **Complete** |
| **Partner Onboarding Pages** | Application list/detail/create, Partners list/detail (6 pages) | **Complete** |
| **Ordinary Life Pages** | Page + Policies list + Quotations list + Claims list (stubs) | **Scaffolded** |
| **Group Life Pages** | Page + Policies list (stubs) | **Scaffolded** |
| **Group Credit** | Directory exists, no files | **Empty** |
| **Front Office** | Directory exists, no files | **Empty** |
| **Reports Page** | Single placeholder page | **Scaffolded** |
| **User Management Page** | Single placeholder page | **Scaffolded** |
| **System Parameters Page** | Single placeholder page | **Scaffolded** |
| **Approvals Page** | Single placeholder page | **Scaffolded** |
| **Error Pages** | 404, 403, 500 | **Complete** |
| **Tests** | Vitest configured, no tests written yet | **Not started** |

### Frontend Routes (27 defined)

| Route | Component | Auth | Permissions |
|---|---|---|---|
| `/login` | login-page | No | — |
| `/forgot-password` | forgot-password-page | No | — |
| `/reset-password` | reset-password-page | No | — |
| `/` | dashboard-page | Yes | — |
| `/partner-onboarding` | partner-onboarding-page | Yes | — |
| `/partner-onboarding/applications` | partner-applications-list | Yes | — |
| `/partner-onboarding/applications/:id` | partner-application-detail | Yes | — |
| `/partner-onboarding/applications/new` | partner-application-create | Yes | — |
| `/partners` | partners-list | Yes | — |
| `/partners/:id` | partner-detail | Yes | — |
| `/ordinary-life` | ordinary-life-page | Yes | — |
| `/ordinary-life/policies` | ordinary-policies-list | Yes | — |
| `/ordinary-life/quotations` | ordinary-quotations-list | Yes | — |
| `/ordinary-life/claims` | ordinary-claims-list | Yes | — |
| `/group-life` | group-life-page | Yes | — |
| `/group-life/policies` | group-policies-list | Yes | — |
| `/reports` | reports-page | Yes | reports.view |
| `/users` | user-management-page | Yes | users.manage |
| `/system` | system-parameters-page | Yes | system.manage |
| `/approvals` | approvals-page | Yes | approvals.manage |
| `/404` | not-found-page | No | — |
| `/403` | forbidden-page | No | — |
| `/500` | server-error-page | No | — |

Additional routes defined in constants but NOT registered in router (future use):
- `/ordinary-life/policies/:id`, `/ordinary-life/policies/new`, `/ordinary-life/quotations/:id`, `/ordinary-life/quotations/new`, `/ordinary-life/claims/:id`, `/ordinary-life/claims/new`, `/ordinary-life/renewals`
- `/group-life/policies/:id`, `/group-life/policies/new`, `/group-life/quotations`, `/group-life/quotations/:id`, `/group-life/quotations/new`, `/group-life/claims`, `/group-life/claims/:id`, `/group-life/claims/new`, `/group-life/members`
- `/group-credit/*` (all 6 routes)
- `/front-office/*` (all 9 routes)
- `/reports/generate`, `/reports/:id`, `/reports/schedule`
- `/users/:id`, `/users/new`, `/users/permissions`, `/users/roles`
- `/system/parameters`, `/system/parameters/:id`, `/system/parameters/new`
- `/approvals/pending`, `/approvals/history`, `/approvals/:id`
- `/settings`, `/settings/profile`, `/settings/security`, `/settings/preferences`, `/settings/notifications`

### Frontend → Backend API Mapping

The frontend expects these API endpoints at `/api/v1/`:

| Frontend Config Key | Expected Backend Path | Backend Status |
|---|---|---|
| `auth/*` | `/api/v1/auth/` | **Complete** |
| `users/*` | `/api/v1/users/` | **Complete** |
| `dashboard/*` | `/api/v1/dashboard/` | **Stub** (views.py empty) |
| `onboarding/*` | `/api/v1/onboarding/` | **Complete** (in apps/partner_onboarding/) |
| `partners/*` | `/api/v1/partners/` | **Stub** |
| `ordinary-life/*` | `/api/v1/ordinary-life/` | **Not created** |
| `group-life/*` | `/api/v1/group-life/` | **Not created** |
| `group-credit/*` | `/api/v1/group-credit/` | **Not created** |
| `front-office/*` | `/api/v1/front-office/` | **Not created** |
| `reports/*` | `/api/v1/reports/` | **Not created** |
| `system/*` | `/api/v1/system/` | **Not created** |
| `approvals/*` | `/api/v1/approvals/` | **Not created** |

---

## Summary Statistics

| Category | Count |
|---|---|
| Total backend files | 88 |
| Django apps created | 11 (2 complete, 2 stubs, 7 proxy-only for admin) |
| Django apps not started | 9 |
| API endpoints implemented | ~30 |
| Database tables in SQL design | ~150+ |
| Database tables as Django models | ~12 |
| PostgreSQL schemas designed | 12 |
| Lines of Python code | ~3,500+ |
| Lines of SQL schema | 2,472 |
| Lines of documentation (SRS + app structure) | 584 |
| Test lines | 510 |
