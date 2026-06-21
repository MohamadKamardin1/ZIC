---
name: phase-gated-django-module
description: Build Django/DRF modules through strict phase-gated development (models → serializers → services → views → tasks → admin) with gate checks between each phase
source: auto-skill
extracted_at: '2026-06-20T18:13:17.140Z'
---

# Phase-Gated Django Module Build

## When to use
When building a new Django module from scratch in the ZIC project, or when rebuilding a stub module into a full implementation. The strict phase ordering prevents cascading errors — each phase must pass its gate before the next begins.

## Phase Order (Strict — No Skipping)

### Phase 0: Foundation
1. Create/rebuild models with full field definitions (UUID PKs, indexes, `db_table`, `Meta`, `__str__`, `display_name` property)
2. Create the new app via `startapp` or manual scaffolding (`__init__.py`, `apps.py`, `models.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`, `tests/`)
3. Register in `INSTALLED_APPS`
4. Create custom exceptions inheriting from `apps.core.exceptions.ZICAPIException`
5. Write model tests
6. **GATE**: `makemigrations`, `migrate`, `manage.py check`, model imports, all model tests pass

### Phase 1: Serializers
1. Create all serializer classes (List, Detail, Create, Update, Submit, Review, etc.)
2. Partner-type routing validation (INDIVIDUAL vs CORPORATE required fields)
3. Email uniqueness validation across both `Partner` and active `PartnerApplication`
4. Age validation using exact birthday comparison (not `days/365.25`)
5. Document upload validation (10 MB limit, MIME type whitelist)
6. Write serializer tests
7. **GATE**: All serializer tests pass

### Phase 2: Services
1. Create `services/` directory with `__init__.py` exporting all services
2. Implement state machine service with `STATE_MACHINE` dict and `_validate_transition`
3. Sequential number generation (`XX-YYYY-NNNNNN` format using `Max()` aggregate)
4. All transition methods (submit, review, approve, reject, etc.)
5. Conversion service with `@transaction.atomic`
6. Compliance/risk scoring service
7. Write service tests covering all transitions + edge cases
8. **GATE**: All service tests pass

### Phase 3: Views & URLs
1. Create filters with `django_filters`
2. Create ViewSets with `get_serializer_class`, `get_permissions`, `get_queryset`
3. Implement all `@action` methods calling service layer
4. Create nested ViewSets for documents/tasks
5. Create URL routing and wire into `config/urls.py`
6. Write view tests
7. **GATE**: All view tests pass

### Phase 4: Tasks & Signals
1. Create Celery tasks for notifications and periodic jobs
2. Create Django signals for activity logging and triggers
3. Connect signals in `apps.py ready()`
4. Write task and signal tests
5. **GATE**: All task/signal tests pass

### Phase 5: Admin & Integration
1. Complete Django admin with fieldsets, inlines, filters, search, actions
2. Write end-to-end integration tests (full workflow DRAFT→CONVERTED)
3. **FINAL GATE**: Full test suite, `migrate --check`, `check --deploy`, flake8, coverage ≥80%

## Project Conventions

### Models
- UUID primary keys: `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- Explicit `db_table` in Meta (e.g., `partner_partner`, `onboarding_partner_application`)
- Ordering: `ordering = ["-created_at"]`
- Indexes on frequently queried fields (status, partner_type, email)
- `__str__` returns human-readable identifier
- `display_name` property for UI-friendly name

### Serializers
- camelCase JSON via `djangorestframework-camel-case` middleware
- Standard response envelope (handled by core pagination/exception handler)
- Import choices from model files, don't redefine

### Services
- Static methods (no `__init__` needed)
- All state changes go through `_validate_transition` first
- Use `update_fields` on `save()` for targeted updates
- `logger.info()` for all state changes with application number and user email

### Views
- Every ViewSet must override `retrieve()` and `list()` to wrap output in the project's `_response()` envelope — DRF's default views bypass the envelope
- Paginated `list()` calls `self.get_paginated_response(serializer.data)` (pagination class provides its own envelope); non-paginated falls through to `_response()`
- Helper function `_response(data, message, status_code)` standardizes all responses: `{"success", "status_code", "message", "data", "meta"}`
- Action methods call service-layer methods and catch domain exceptions (`ApplicationTransitionError`, etc.), returning `_response(message=str(e), status_code=e.status_code)`
- Nested resources (documents, tasks) use explicit URL path entries pointing at `.as_view()` mappings — not `@action` on the parent

### Serializers
- **DRAFT relaxation**: `CreateSerializer.validate()` must NOT enforce all required fields — DRAFT allows partial data. Full field validation happens at submit time via `SubmitSerializer` and `ApplicationService.submit()`
- Partial update (`PATCH`) serializers must handle `self.partial` in `validate()` — fall back to `self.instance` for fields not in the patch (e.g., `partner_type`)

### Models
- `_previous_status` tracking pattern: `__init__` sets `self._previous_status = self.status`; `save()` updates it after `super().save()` — enables signals to detect status changes
- Import choices from the source model file rather than redefining (e.g., `from apps.partners.models import IDENTIFICATION_TYPE_CHOICES`)

### Exceptions
- Inherit from `ZICAPIException` with `message`, `code`, `status_code`, `details`
- Three categories: `TransitionError`, `ValidationError`, `ConversionError`

### Permissions
- Create granular permission classes for each action type: `CanSubmitApplication`, `CanReviewApplication`, `CanRejectApplication`, `CanPerformComplianceAction`, `CanConvertApplication`
- `CanReviewApplication`: allows actions when `status in ("SUBMITTED", "UNDER_REVIEW", "PENDING_DOCUMENTS")`
- `CanPerformComplianceAction`: allows approve/suspend/resume when `status in ("COMPLIANCE_CHECK", "SUSPENDED")`
- `CanRejectApplication`: allows rejection from review stages when `status in ("UNDER_REVIEW", "COMPLIANCE_CHECK", "PENDING_DOCUMENTS")`
- `CanConvertApplication`: only when `status == "APPROVED"`
- Wire permissions in ViewSet's `get_permissions()` method based on `self.action`

### Views - Actions
- **resume action**: For SUSPENDED → COMPLIANCE_CHECK transition (requires `CanPerformComplianceAction`)
- Implement as `@action(detail=True, methods=["post"], url_path="resume")`
- Check status before allowing: `if application.status != "SUSPENDED": return _response(message="...", status_code=400)`
- Update status and save: `application.status = "COMPLIANCE_CHECK"; application.save(update_fields=["status", "updated_at"])`

### Admin
- Field references in `admin.py` MUST exist in the model — non-existent fields cause `SystemCheckError` at startup
- Common field mappings: use `other_name` (not `middle_name`), `industry` (not `business_nature`)
- Partner model has no `company_registration_number` field — use `tin_number` for corporate identification
- Verify all fieldset fields exist by running `python manage.py check` before running tests

### Integration Tests
- Use `v1:` namespace prefix for all URL reverses: `reverse('v1:partner-applications-list')`, `reverse('v1:application-documents', kwargs={'application_pk': app_id})`
- Full workflow tests should traverse entire state machine: DRAFT → SUBMITTED → UNDER_REVIEW → COMPLIANCE_CHECK → APPROVED → CONVERTED
- Test rejection paths: rejection can happen from UNDER_REVIEW (reviewer) or COMPLIANCE_CHECK (compliance officer)
- Test suspension/resume: SUSPENDED → COMPLIANCE_CHECK requires `CanPerformComplianceAction` permission
- Use `APIClient()` with `force_authenticate()` for authenticated requests
- Upload documents via multipart: `client.post(url, data={'file': SimpleUploadedFile(...)}, format='multipart')`
- Verify state transitions by checking `response.status_code == 200` and `application.refresh_from_db()`

### Tests
- Use `django.test.TestCase` (not pytest classes)
- Helper functions: `create_test_user()`, `create_individual_app()`, etc.
- Each test class targets one specific concern
- Run with: `python3 manage.py test apps.<app>.tests.<module> -v 2`
- Test fixtures creating multiple records of a unique-field model MUST supply distinct values for that field (e.g., unique `email` per `Partner`)
- Integration test helpers should accept flexible data via `**overrides` to allow customization per test

## Common Pitfalls
- **Dual-auth login**: Frontend login forms often send email addresses in the `username` field. Update `LoginSerializer.validate()` to try username first, then email as fallback:
  ```python
  try:
      user = User.objects.get(username=username_or_email)
  except User.DoesNotExist:
      try:
          user = User.objects.get(email=username_or_email)
      except User.DoesNotExist:
          raise serializers.ValidationError('Invalid credentials.')
  auth_user = authenticate(request=request, username=user.username, password=password)
  ```
- **Age validation**: Use exact birthday comparison (`dob.replace(year=dob.year + 18)`) not `days/365.25` — the latter fails on edge cases
- **Dependencies**: Always `pip3 install --break-system-packages -r requirements.lock.txt` before running Django commands
- **Migration conflicts**: If rebuilding a stub model, delete old migration and reset SQLite DB (`rm db.sqlite3 && migrate`)
- **Admin references**: After rebuilding models, update `admin.py` — old `list_display` fields will break
- **Signal imports**: `apps.py ready()` must import signals module with `# noqa: F401`
- **startapp failures**: `manage.py startapp` fails if settings depend on uninstalled packages (e.g., `environ`). Manual scaffolding (create dirs + write `__init__.py`, `apps.py`, etc.) is the reliable fallback
- **django_filters Q import**: Must use `from django.db.models import Q` directly — `django_filters.db.models.Q` does not exist and causes `AttributeError` at runtime
- **Unique email constraint**: `Partner.email` is unique at the model level — test helpers creating multiple partners MUST pass distinct emails, or `IntegrityError` occurs
- **Admin field validation**: Non-existent fields in `admin.py` fieldsets cause `SystemCheckError` — always verify with `python manage.py check` before running tests
- **URL namespace in tests**: Integration tests must use `v1:` namespace prefix (e.g., `reverse('v1:partner-applications-list')`) — missing prefix causes `NoReverseMatch`
- **Field name mismatches**: Partner model uses `other_name` (not `middle_name`), `industry` (not `business_nature`), and has no `company_registration_number` — check actual model fields
- **Permission granularity**: Don't use `IsAdminUser()` for review actions — it requires superuser. Use custom permissions like `CanReviewApplication` that check application status instead
- **Resume action**: SUSPENDED → COMPLIANCE_CHECK transition needs `CanPerformComplianceAction` permission (allows `status in ("COMPLIANCE_CHECK", "SUSPENDED")`)
- **Compliance serializer**: Must allow rejection from UNDER_REVIEW/PENDING_DOCUMENTS, not just COMPLIANCE_CHECK — update `validate()` to check `status in ("UNDER_REVIEW", "PENDING_DOCUMENTS", "COMPLIANCE_CHECK", "SUSPENDED")`
- **Test discovery conflicts**: Running `python manage.py test apps.partner_onboarding` fails with `ImportError` due to duplicate `test_models.py` — use explicit module paths: `python manage.py test apps.partner_onboarding.tests.test_models apps.partner_onboarding.tests.test_serializers ...`
