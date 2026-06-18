# System Requirements Specification

## 1. System Overview

### 1.1 Product Name
ZIC Core Life Insurance Platform.

### 1.2 Purpose
The system shall provide a unified web platform for life insurance operations covering Dashboard, Partner Onboarding, Ordinary Life, Group Life, Group Credit, Front Office, Reports, System Parameters, Reinsurance, User Management, and Approval workflows.

### 1.3 Scope
The system shall support the full module structure shown in the supplied attachment:

- Dashboard
- Partner Onboarding
- Ordinary Life
- Group Life
- Group Credit
- Front Office
- Reports
- System Parameters
- User Management
- Approval

The application shall be implemented as a Django platform backed by PostgreSQL. It shall provide secure transactional processing, setup maintenance, reporting, approval routing, audit history, and integration-ready APIs.

### 1.4 Intended Users
- Life operations officers
- Underwriters
- Claims officers
- Front office and finance staff
- Partner onboarding teams
- Reinsurance officers
- Approval managers
- System administrators
- Auditors and reporting users

## 2. Functional Requirements

### 2.1 Dashboard
The system shall provide role-based dashboards showing operational summaries, pending approvals, quotations, proposals, policies, schemes, claims, renewals, commissions, payments, reinsurance processing, and onboarding tasks. Users shall be able to configure visible dashboard widgets where permitted.

### 2.2 Partner Onboarding
The system shall allow users to onboard partners, including clients, brokers, agents, lenders, reinsurers, banks, medical facilities, and other service providers.

The system shall:
- Capture partner applications, registration details, contacts, bank accounts, documents, and onboarding tasks.
- Validate mandatory onboarding documents by partner type.
- Route onboarding applications through approval.
- Convert approved onboarding applications into active partner records.
- Maintain onboarding status history and audit trail.

### 2.3 Ordinary Life

#### 2.3.1 Core Transactions
The system shall support:
- Ordinary Life Quotations
- Ordinary Life Commitments
- Ordinary Life Proposals
- Ordinary Life Policies
- Ordinary Life Loans
- Ordinary Life Withdrawals
- Ordinary Life Claims
- Mutual Installments
- Ordinary Life Parameters

Functional requirements:
- Users shall create quotations and convert approved quotations into proposals.
- Users shall create policies from approved proposals.
- Policies shall maintain policyholder, life assured, beneficiaries, product, sum assured, premium, commencement date, maturity date, status, agent, and currency.
- Commitments shall track due premium or benefit commitments and settlement status.
- Loans shall be assessed against policy value, surrender value, loan rules, and interest controls.
- Withdrawals shall validate policy eligibility, available value, approval status, and payment status.
- Claims shall support death, maturity, surrender, disability, and other claim types.
- Mutual installments shall schedule periodic amounts linked to policies or claims.

#### 2.3.2 OL Default Setups
The system shall maintain:
- OL Default System Parameters
- Override Commission Setup
- Computation Approach
- Maturity Claims Setup

#### 2.3.3 OL Policy Setup
The system shall maintain:
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

#### 2.3.4 OL Product Setup
The system shall maintain:
- OL Plan Types
- OL Products
- Plan Tax Configurations
- Plan Target Markets
- Plan Risk Categories
- Plan Occupational Risk Limits
- Investment Fund Types
- Investment Funds

#### 2.3.5 OL Product Rating
The system shall maintain:
- OL Premium Rates
- OL Mortality Rates
- OL Joint Life Setup
- Reinstatement Interest Rates
- OL Bonus Rates
- OL Mortgage Interest Factor
- Installment Charge Rates
- OL Cash Surrender Value
- OL Reserve Loadings

#### 2.3.6 OL Rider Setup
The system shall maintain OL Riders and OL Rider Rates.

#### 2.3.7 OL Agent Management
The system shall maintain agent commission rates, agent assignment, and commission overrides.

#### 2.3.8 OL Loan Setup
The system shall maintain OL Loan System Setup and OL Loan Interest Control.

#### 2.3.9 OL Medical Underwriting
The system shall maintain:
- OL Medical Codes
- OL Medical Limits
- OL Personal Habits
- OL Medical History
- OL Medical Facilities
- OL Medical Practitioners

#### 2.3.10 OL Claim Setup
The system shall maintain:
- OL Claim Types
- OL Claim Reasons
- OL Claim Statuses
- OL Discharge Types
- OL Correspondent Types

### 2.4 Group Life

The system shall support:
- Group Life Quotations
- Group Life Schemes
- GL Schemes Due For Renewal
- Group Life Claims
- GL Claim Installments
- Group Life Parameters

The Group Life parameter area shall include:
- GL Scheme Setup: scheme types, premium rates, member statuses, scheme statuses, renewal statuses, health questions, health questionnaires.
- GL Product Setup: GL products and GL sub-products.
- GL Rider Setup: GL riders and GL rider rates.
- GL Medical U/W: medical codes, limits, underwriting decisions, personal habits, medical history, facilities, and practitioners.
- GL Claim Setup: claim types, reasons, statuses, discharge types, and correspondent types.
- GL Medical Invoice.

Functional requirements:
- Users shall create quotations and convert approved quotations into group life schemes.
- Schemes shall maintain policyholder, product, sub-product, members, premium, sum assured, status, and renewal period.
- The system shall identify schemes due for renewal.
- Claims shall validate member eligibility and route through approvals.
- Claim installments shall prevent payment above approved claim amounts.
- Medical invoices shall be linked to schemes, members, claims, facilities, or practitioners.

### 2.5 Group Credit

The system shall support:
- Group Credit Quotations
- Group Credit Schemes
- GC Schemes Due For Renewal
- Group Credit Claims
- GC Claim Installments
- Group Credit Parameters

The Group Credit parameter area shall include:
- GC Scheme Setup: scheme types, premium rates, member statuses, scheme statuses, renewal statuses, health questions, health questionnaires.
- GC Product Setup: GC products and GC sub-products.
- GC Rider Setup: GC riders and GC rider rates.
- GC Medical U/W: medical codes, limits, underwriting decisions, personal habits, medical history, facilities, and practitioners.
- GC Claim Setup: claim types, reasons, statuses, discharge types, and correspondent types.
- GC Medical Invoice.

Functional requirements:
- Users shall create quotations and convert approved quotations into group credit schemes.
- Schemes shall capture lender, borrower/member, outstanding loan balance, loan amount, premium, and sum assured.
- Claims shall validate cover eligibility and outstanding loan balance.
- Claim installments and medical invoices shall support approval and payment processing.

### 2.6 Front Office

The system shall support:
- Receipts
- Commissions
- Commission Statement
- Requisitions
- Payments
- Front Office Parameters

Functional requirements:
- Receipts shall record incoming funds and allocate them to policies, schemes, invoices, claims, or partner accounts.
- Commissions shall be calculated and paid to eligible partners.
- Commission statements shall summarize earned, paid, reversed, withheld, and outstanding commissions.
- Requisitions shall request outgoing payment approval.
- Payments shall record outgoing settlements and bank references.
- Reversals shall require approval and audit history.

### 2.7 Reports
The system shall provide role-based reports for all modules, including quotations, proposals, policies, schemes, renewals, members, claims, installments, receipts, payments, commissions, onboarding, approvals, audit trail, and reinsurance. Reports shall support filters, pagination, export, and run history.

### 2.8 System Parameters

The system shall maintain:
- General Parameters
- Partner Parameters
- User Parameters
- Reinsurance Parameters

General parameters include company, branches, currency, tax, numbering, documents, and notification templates.

Partner parameters include partner types, partners, contacts, and bank accounts.

User parameters include user preferences, departments, staff profiles, and role-related configuration.

Reinsurance parameters include:
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

### 2.9 User Management

The system shall maintain:
- Permission Groups
- Permissions
- User Groups
- Users

Functional requirements:
- Users shall authenticate before accessing the system.
- Administrators shall assign users to groups and permission groups.
- Permissions shall control menu access, create, read, update, delete, approve, reverse, export, and admin operations.
- User access changes shall be auditable.

### 2.10 Approval

The system shall maintain:
- Approvals
- Approval Types
- Approval Process Types
- Approval Rules
- Approval Processes
- Approver Roles
- Approvers
- Approval Status

Functional requirements:
- Any configured business process may create approval requests.
- Rules shall route approvals by module, process type, amount, branch, product, and role.
- Approvers shall approve, reject, return, delegate, and comment.
- Approval history shall be immutable.
- Approved requests shall trigger downstream status changes.

## 3. Non-Functional Requirements

### 3.1 Security
- The system shall enforce authenticated access.
- Role-based and permission-based access shall protect all screens and APIs.
- Passwords shall be securely hashed.
- Sensitive records shall be auditable.

### 3.2 Auditability
- Core setup and transaction records shall store created and updated metadata.
- Approval decisions, reversals, status changes, and financial operations shall maintain immutable history.

### 3.3 Data Integrity
- Codes and business reference numbers shall be unique where applicable.
- Monetary fields shall use fixed precision decimals.
- Date ranges shall be validated.
- Financial and approval actions shall use database transactions.

### 3.4 Performance
- Register screens shall support filtering, search, and pagination.
- Common lookup fields, dates, statuses, and foreign keys shall be indexed.
- Large reports may run asynchronously.

### 3.5 Availability
- The system shall support backup, restore, health checks, and operational monitoring.

### 3.6 Usability
- Navigation shall follow the module hierarchy in the attachment.
- Setup screens shall allow active/inactive status rather than physical deletion.
- Users shall be able to find records by reference number, partner, status, date, and module-specific fields.

## 4. Business Rules

- A quotation can become a proposal, policy, or scheme only after required validation and approval.
- A policy or scheme must reference active products and valid setup records.
- A loan or withdrawal cannot exceed configured policy eligibility limits.
- Claims cannot be paid above approved amounts.
- Receipts and payments must balance to their allocations or requisitions.
- Commission payment cannot exceed approved commission.
- Medical invoices must reference valid medical providers where applicable.
- Reinsurance cessions must reference active treaties and underwriting years.
- Partner onboarding must be approved before creating an active partner.

## 5. Database and Architecture Requirements

- PostgreSQL shall be the primary database.
- The schema shall separate major domains using PostgreSQL schemas.
- Django apps shall align with business modules.
- APIs shall expose module operations using consistent authentication, authorization, validation, pagination, and audit behavior.

## 6. Acceptance Criteria

- Every module in the supplied attachment is represented in the SRS.
- Django app structure maps every module to an implementation area.
- PostgreSQL schema includes tables or views for every module and parameter group.
- Core modules support setup, transaction, approval, reporting, audit, and security requirements.
