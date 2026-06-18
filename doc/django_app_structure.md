# Django App Structure

## 1. Recommended Project Layout

```text
zic_core_life/
  manage.py
  config/
    settings/
      base.py
      local.py
      production.py
    urls.py
    asgi.py
    wsgi.py
  apps/
    common/
    dashboard/
    users/
    approvals/
    partners/
    partner_onboarding/
    ordinary_life/
      models/
        default_setup.py
        policy_setup.py
        product_setup.py
        product_rating.py
        riders.py
        agents.py
        loans.py
        medical.py
        claims.py
        transactions.py
      services/
        pricing.py
        underwriting.py
        policy_issue.py
        loans.py
        withdrawals.py
        claims.py
    group_life/
      models/
        setup.py
        products.py
        riders.py
        medical.py
        quotations.py
        schemes.py
        claims.py
        invoices.py
      services/
        pricing.py
        underwriting.py
        renewal.py
        claims.py
    group_credit/
      models/
        setup.py
        products.py
        riders.py
        medical.py
        quotations.py
        schemes.py
        claims.py
        invoices.py
      services/
        pricing.py
        underwriting.py
        renewal.py
        claims.py
    front_office/
      services/
        receipts.py
        commissions.py
        requisitions.py
        payments.py
    reinsurance/
      services/
        cessioning.py
        dashboard.py
    reports/
    parameters/
  templates/
  static/
  media/
  docs/
  database/
```

Each app should include `admin.py`, `serializers.py`, `views.py`, `urls.py`, and `tests/` as needed. Large domains should keep models, serializers, views, and services split by submodule.

## 2. App Responsibilities

### common
Shared base models, audit utilities, validators, permissions, pagination, money helpers, effective-date helpers, and soft-delete conventions.

### dashboard
Role-based dashboard widgets, user dashboard layouts, pending task summaries, and cross-module metrics.

### users
Users, user groups, permissions, permission groups, staff profiles, user preferences, and authentication support.

### approvals
Approval types, process types, rules, processes, roles, approvers, approval requests, and approval action history.

### partners
Partner types, partner master records, contacts, bank accounts, and reusable party records for clients, agents, brokers, lenders, reinsurers, banks, and medical providers.

### partner_onboarding
Partner onboarding applications, document collection, verification, tasks, review, approval, and conversion to active partner records.

### ordinary_life
Owns Ordinary Life quotations, commitments, proposals, policies, loans, withdrawals, claims, mutual installments, and all OL parameter groups:

- Default setup
- Policy setup
- Product setup
- Product rating
- Rider setup
- Agent management
- Loan setup
- Medical underwriting
- Claim setup

### group_life
Owns Group Life quotations, schemes, renewals, claims, claim installments, medical invoices, and all GL parameter groups.

### group_credit
Owns Group Credit quotations, schemes, renewals, claims, claim installments, medical invoices, and all GC parameter groups.

### front_office
Owns receipts, receipt allocations, commissions, commission statements, requisitions, payments, reversals, and front office parameters.

### reinsurance
Owns reinsurance departments, classes, treaty types, treaty codes, underwriting years, ceded premium rates, business types, branches, participants, proportional treaties, non-proportional treaties, cessions, and processing dashboards.

### reports
Report definitions, report run history, export services, scheduled reports, and role-based report registry.

### parameters
General system parameters such as company, branches, currencies, tax, numbering, document types, and notification templates.

## 3. Module-to-App Mapping

| Business Module | Django App |
| --- | --- |
| Dashboard | `dashboard` |
| Partner Onboarding | `partner_onboarding`, `partners` |
| Partners | `partners` |
| Ordinary Life Quotations | `ordinary_life` |
| Ordinary Life Commitments | `ordinary_life` |
| Ordinary Life Proposals | `ordinary_life` |
| Ordinary Life Policies | `ordinary_life` |
| Ordinary Life Loans | `ordinary_life` |
| Ordinary Life Withdrawals | `ordinary_life` |
| Ordinary Life Claims | `ordinary_life` |
| Mutual Installments | `ordinary_life` |
| Ordinary Life Parameters | `ordinary_life` |
| OL Default Setups | `ordinary_life` |
| OL Policy Setup | `ordinary_life` |
| OL Product Setup | `ordinary_life` |
| OL Product Rating | `ordinary_life` |
| OL Rider Setup | `ordinary_life` |
| OL Agent Management | `ordinary_life`, `front_office` |
| OL Loan Setup | `ordinary_life` |
| OL Medical U/W | `ordinary_life` |
| OL Claim Setup | `ordinary_life` |
| Group Life Quotations | `group_life` |
| Group Life Schemes | `group_life` |
| GL Schemes Due For Renewal | `group_life` |
| Group Life Claims | `group_life` |
| GL Claim Installments | `group_life` |
| Group Life Parameters | `group_life` |
| GL Scheme/Product/Rider/Medical/Claim Setup | `group_life` |
| GL Medical Invoice | `group_life` |
| Group Credit Quotations | `group_credit` |
| Group Credit Schemes | `group_credit` |
| GC Schemes Due For Renewal | `group_credit` |
| Group Credit Claims | `group_credit` |
| GC Claim Installments | `group_credit` |
| Group Credit Parameters | `group_credit` |
| GC Scheme/Product/Rider/Medical/Claim Setup | `group_credit` |
| GC Medical Invoice | `group_credit` |
| Receipts | `front_office` |
| Commissions | `front_office` |
| Commission Statement | `front_office` |
| Requisitions | `front_office` |
| Payments | `front_office` |
| Front Office Parameters | `front_office` |
| Reports | `reports` |
| General Parameters | `parameters` |
| Partner Parameters | `partners` |
| User Parameters | `users`, `parameters` |
| Reinsurance Parameters | `reinsurance` |
| User Management | `users` |
| Approval | `approvals` |

## 4. API Structure

```text
/api/dashboard/
/api/partner-onboarding/
/api/partners/
/api/ordinary-life/quotations/
/api/ordinary-life/commitments/
/api/ordinary-life/proposals/
/api/ordinary-life/policies/
/api/ordinary-life/loans/
/api/ordinary-life/withdrawals/
/api/ordinary-life/claims/
/api/ordinary-life/parameters/
/api/group-life/quotations/
/api/group-life/schemes/
/api/group-life/renewals/
/api/group-life/claims/
/api/group-life/medical-invoices/
/api/group-life/parameters/
/api/group-credit/quotations/
/api/group-credit/schemes/
/api/group-credit/renewals/
/api/group-credit/claims/
/api/group-credit/medical-invoices/
/api/group-credit/parameters/
/api/front-office/receipts/
/api/front-office/commissions/
/api/front-office/requisitions/
/api/front-office/payments/
/api/reinsurance/
/api/reports/
/api/parameters/
/api/users/
/api/approvals/
```

## 5. Engineering Notes

- Use Django REST Framework for APIs.
- Use PostgreSQL schemas to keep domain ownership clear.
- Use service classes for business operations such as policy issue, scheme conversion, claim approval, payment posting, commission calculation, and reinsurance cessioning.
- Use transactions for all financial, approval, and status-changing operations.
- Use Django admin for early setup maintenance, then add dedicated UI screens for high-volume operations.
- Keep master/setup records active/inactive rather than physically deleting them.
- Use shared approval, audit, document, and notification services across all modules.
