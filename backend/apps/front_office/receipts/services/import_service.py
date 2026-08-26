"""Front Office Receipts — bulk import service (prompt 9).

Two-phase import: ``dry_run`` validates every CSV row and records per-row
outcomes without touching ``Receipt``; ``commit_batch`` replays the VALID (and
any FAILED) rows into receipts, idempotently, and records each row's outcome so
failed rows stay reprocessable — re-committing the batch retries only them.
"""

import csv
import hashlib
import io
import json
import uuid
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.front_office.receipts.config_models import ReceiptPaymentModeRule
from apps.front_office.receipts.errors import ReceiptError, import_row_invalid
from apps.front_office.receipts.models import (
    ReceiptAllocationTargetType,
    ReceiptImportBatch,
    ReceiptImportBatchStatus,
    ReceiptImportMode,
    ReceiptImportRow,
    ReceiptImportRowStatus,
    ReceiptPaymentMode,
    ReceiptSourceModule,
    ReceiptStatus,
)
from apps.front_office.receipts.services.allocation_service import _terminal_codes, allocate
from apps.front_office.receipts.services.parameter_resolver import (
    configured_currencies,
    default_currency,
)
from apps.front_office.receipts.services.receipt_service import create_draft, post_receipt
from apps.governance.services.audit_service import AuditService
from apps.ol_commitments.models import OLCommitment
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner

IMPORT_COLUMNS = [
    "receipt_date",
    "branch_code",
    "payer_partner_number",
    "currency_code",
    "payment_mode_code",
    "amount",
    "payment_reference",
    "source_module",
    "target_commitment_number",
    "narration",
]

REQUIRED_HEADERS = {
    "receipt_date",
    "branch_code",
    "payer_partner_number",
    "currency_code",
    "payment_mode_code",
    "amount",
}

_PAYMENT_MODE_CODES = {code for code, _ in ReceiptPaymentMode.choices}


def import_csv_template():
    """Header row for the downloadable CSV template (10 columns)."""
    writer = io.StringIO()
    csv.writer(writer).writerow(IMPORT_COLUMNS)
    return writer.getvalue()


def next_batch_number():
    return f"IMP-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


def normalize_import_mode(mode):
    code = (mode or "").strip().upper() or ReceiptImportMode.DRAFT
    if code not in {c for c, _ in ReceiptImportMode.choices}:
        raise import_row_invalid(
            message=f"Import mode '{mode}' is not valid.",
            field_errors={"import_mode": ["Import mode must be DRAFT, POST or ALLOCATE."]},
        )
    return code


def parse_csv(file):
    """Read and decode a CSV upload into a list of canonical row dicts."""
    raw_bytes = file.read()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise import_row_invalid(
            message="The CSV file must be UTF-8 encoded.",
            field_errors={"file": ["The CSV file must be UTF-8 encoded."]},
        ) from None
    reader = csv.DictReader(io.StringIO(text))
    raw_headers = [(h or "") for h in (reader.fieldnames or [])]
    header_map = {h.strip().lower(): h for h in raw_headers if h.strip()}
    missing = [col for col in REQUIRED_HEADERS if col not in header_map]
    if missing:
        raise import_row_invalid(
            message="The CSV is missing required columns.",
            field_errors={"file": [f"Missing required column(s): {', '.join(missing)}."]},
        )
    rows = []
    for raw in reader:
        if not any((raw.get(h) or "").strip() for h in raw_headers):
            continue
        canonical = {
            col: (raw.get(header_map[col]) or "").strip() for col in IMPORT_COLUMNS if col in header_map
        }
        rows.append(canonical)
    if not rows:
        raise import_row_invalid(
            message="The CSV file contains no data rows.",
            field_errors={"file": ["No data rows found in the uploaded CSV."]},
        )
    return rows


def row_hash(canonical):
    """Stable content hash across the ten import columns."""
    payload = {key: canonical.get(key, "") for key in IMPORT_COLUMNS}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resolve_branch(code):
    if not (code or "").strip():
        return None
    return Branch.objects.filter(code__iexact=(code or "").strip(), is_active=True).first()


def _resolve_partner(partner_number):
    if not (partner_number or "").strip():
        return None
    return Partner.objects.filter(partner_number__iexact=(partner_number or "").strip(), is_active=True).first()


def _resolve_commitment(commitment_number):
    if not (commitment_number or "").strip():
        return None
    return OLCommitment.objects.filter(commitment_number__iexact=(commitment_number or "").strip()).first()


def validate_row(canonical, *, import_mode, seen=None):
    """Validate one canonical row; returns a result dict with errors and the hash."""
    errors = {}
    partner = None

    def value(key):
        return str(canonical.get(key) or "").strip()

    # receipt_date
    raw_date = value("receipt_date")
    if not raw_date:
        errors["receipt_date"] = ["Receipt date is required (use YYYY-MM-DD)."]
    else:
        try:
            parsed_date = timezone.datetime.fromisoformat(raw_date).date()
            canonical["receipt_date"] = parsed_date.isoformat()
        except ValueError:
            errors["receipt_date"] = [f"'{raw_date}' is not a valid date. Use YYYY-MM-DD."]

    # branch_code (optional — a branch is not mandatory for a draft)
    branch = _resolve_branch(value("branch_code"))
    canonical["branch_code"] = value("branch_code").upper() if value("branch_code") else ""
    if value("branch_code") and branch is None:
        errors["branch_code"] = [f"Branch '{value('branch_code')}' was not found or is inactive."]

    # payer_partner_number
    canonical["payer_partner_number"] = value("payer_partner_number").upper() if value("payer_partner_number") else ""
    if not value("payer_partner_number"):
        errors["payer_partner_number"] = ["Payer partner number is required."]
    else:
        partner = _resolve_partner(value("payer_partner_number"))
        if partner is None:
            errors["payer_partner_number"] = [f"Partner '{value('payer_partner_number')}' was not found or is inactive."]

    # currency_code (defaults to the configured default currency)
    currency = value("currency_code").upper() or default_currency()
    if len(currency) != 3 or not currency.isalpha() or currency not in configured_currencies():
        errors["currency_code"] = [f"Currency '{currency}' is not a configured currency."]
    canonical["currency_code"] = currency

    # payment_mode_code
    payment_mode = value("payment_mode_code").upper()
    canonical["payment_mode_code"] = payment_mode
    rule = None
    if not payment_mode:
        errors["payment_mode_code"] = ["Payment mode is required."]
    elif payment_mode not in _PAYMENT_MODE_CODES:
        errors["payment_mode_code"] = [
            f"Payment mode '{payment_mode}' is not valid. Use one of: {', '.join(sorted(_PAYMENT_MODE_CODES))}."
        ]
    else:
        rule = ReceiptPaymentModeRule.objects.filter(payment_mode=payment_mode, is_active=True).first()

    # amount
    amount = None
    raw_amount = value("amount")
    canonical["amount"] = raw_amount
    if not raw_amount:
        errors["amount"] = ["Amount is required."]
    else:
        try:
            amount = Decimal(str(raw_amount))
            if amount <= 0:
                errors["amount"] = ["Amount must be greater than zero."]
            else:
                canonical["amount"] = f"{amount:.2f}"
        except (InvalidOperation, ValueError, TypeError):
            errors["amount"] = [f"'{raw_amount}' is not a valid amount."]

    # payment_reference (optional for draft; rule-dependent once posted)
    canonical["payment_reference"] = value("payment_reference")

    # source_module (bulk import only supports MANUAL)
    source_module = value("source_module").upper() or ReceiptSourceModule.MANUAL
    canonical["source_module"] = source_module
    if source_module not in {code for code, _ in ReceiptSourceModule.choices}:
        errors["source_module"] = [f"Source module '{source_module}' is not valid."]
    elif source_module != ReceiptSourceModule.MANUAL:
        errors["source_module"] = [
            "Bulk import supports source_module MANUAL only; allocate manual-source receipts instead."
        ]

    # target_commitment_number (optional)
    commitment = None
    target = value("target_commitment_number")
    canonical["target_commitment_number"] = target
    if target:
        commitment = _resolve_commitment(target)
        if commitment is None:
            errors["target_commitment_number"] = [f"Commitment '{target}' was not found."]
        else:
            terminal = set(_terminal_codes())
            if Decimal(commitment.balance or 0) <= 0 or ((commitment.status or "") in terminal):
                errors["target_commitment_number"] = [f"Commitment '{target}' is not open for allocation."]
            elif partner and commitment.partner_id and partner.pk != commitment.partner_id:
                errors["target_commitment_number"] = ["The commitment belongs to a different partner."]
            if (
                import_mode == ReceiptImportMode.ALLOCATE
                and amount is not None
                and Decimal(commitment.balance or 0) > 0
                and amount > Decimal(commitment.balance or 0)
            ):
                errors["target_commitment_number"] = [
                    "Amount exceeds the commitment's outstanding balance."
                ]
            if (
                import_mode == ReceiptImportMode.ALLOCATE
                and commitment is not None
                and (commitment.currency or "").strip().upper() != currency
            ):
                errors["target_commitment_number"] = [
                    "Cross-currency allocation is not supported by bulk import; allocate this receipt manually."
                ]

    # Payment-mode rule requirements apply once a receipt is posted.
    if rule is not None and import_mode in (ReceiptImportMode.POST, ReceiptImportMode.ALLOCATE):
        if rule.requires_reference and not canonical["payment_reference"]:
            errors["payment_reference"] = ["A payment reference is required for this payment mode."]
        if rule.requires_bank_account:
            errors["payment_mode_code"] = [
                f"Payment mode '{payment_mode}' requires a bank account, which bulk import does not support."
            ]
        if amount is not None:
            if rule.min_amount is not None and amount < rule.min_amount:
                errors.setdefault("amount", []).append(
                    f"Amount must be at least {rule.min_amount} for {payment_mode}."
                )
            if rule.max_amount is not None and amount > rule.max_amount:
                errors.setdefault("amount", []).append(
                    f"Amount cannot exceed {rule.max_amount} for {payment_mode}."
                )
    elif import_mode in (ReceiptImportMode.POST, ReceiptImportMode.ALLOCATE) and rule is None:
        errors["payment_mode_code"] = [
            f"Payment mode '{payment_mode}' has no active rule; it cannot be posted."
        ]

    # narration (free text)
    canonical["narration"] = value("narration")

    # Intra-file duplicate detection by content hash.
    hash_value = row_hash(canonical)
    error_code = None
    if seen is not None:
        if hash_value in seen:
            errors["__row__"] = ["Duplicate row: identical values appear more than once in the file."]
            error_code = "RECEIPT_IMPORT_DUPLICATE"
        else:
            seen.add(hash_value)

    return {
        "errors": errors,
        "error_code": error_code or ("RECEIPT_IMPORT_ROW_INVALID" if errors else None),
        "hash": hash_value,
        "canonical": canonical,
    }


def dry_run(*, file, import_mode="DRAFT", actor=None):
    """Validate a CSV upload and record per-row outcomes without creating receipts."""
    import_mode = normalize_import_mode(import_mode)
    rows = parse_csv(file)
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    batch = ReceiptImportBatch.objects.create(
        batch_number=next_batch_number(),
        import_mode=import_mode,
        status=ReceiptImportBatchStatus.PENDING,
        file_name=(getattr(file, "name", "") or "receipts.csv")[:255],
        total_rows=len(rows),
        created_by=actor_instance,
    )
    seen = set()
    valid = invalid = 0
    for index, canonical in enumerate(rows, start=1):
        result = validate_row(canonical, import_mode=import_mode, seen=seen)
        if result["errors"]:
            invalid += 1
            status = (
                ReceiptImportRowStatus.DUPLICATE
                if result["error_code"] == "RECEIPT_IMPORT_DUPLICATE"
                else ReceiptImportRowStatus.INVALID
            )
        else:
            valid += 1
            status = ReceiptImportRowStatus.VALID
        ReceiptImportRow.objects.create(
            batch=batch,
            row_number=index,
            row_hash=result["hash"],
            data=result["canonical"],
            status=status,
            validation_errors=result["errors"],
            error_code=result["error_code"] or "",
            error_message=(
                "; ".join(msg for messages in result["errors"].values() for msg in messages)
                if result["errors"]
                else ""
            ),
            created_by=actor_instance,
        )
    batch.valid_rows = valid
    batch.invalid_rows = invalid
    batch.status = ReceiptImportBatchStatus.VALIDATED
    batch.summary = {"total": len(rows), "valid": valid, "invalid": invalid, "import_mode": import_mode}
    batch.save(update_fields=["valid_rows", "invalid_rows", "status", "summary", "updated_at"])
    AuditService.log_action(
        "IMPORT_DRY_RUN",
        batch,
        actor=actor,
        after_state={"total": len(rows), "valid": valid, "invalid": invalid, "import_mode": import_mode},
        reason="Receipt bulk import dry-run.",
        changed_fields=[],
    )
    return batch


def _row_reference(row):
    """Resolve the reference records a committed row needs (branch, partner)."""
    branch = _resolve_branch(row.data.get("branch_code")) if row.data.get("branch_code") else None
    partner = _resolve_partner(row.data.get("payer_partner_number"))
    return branch, partner


def commit_batch(*, batch, actor=None):
    """Replay VALID/PENDING/FAILED rows into receipts; idempotent per row.

    Retried rows that already committed are skipped; FAILED rows are retried, so
    re-committing a batch after fixing the underlying cause completes the import.
    """
    eligible = list(
        batch.rows.filter(
            status__in=[
                ReceiptImportRowStatus.VALID,
                ReceiptImportRowStatus.FAILED,
                ReceiptImportRowStatus.PENDING,
            ]
        ).order_by("row_number")
    )
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None

    for row in eligible:
        try:
            with transaction.atomic():
                branch, partner = _row_reference(row)
                if row.data.get("branch_code") and branch is None:
                    raise import_row_invalid(
                        message="The branch could not be resolved.",
                        field_errors={"branch_code": ["Branch not found or inactive."]},
                    )
                if partner is None:
                    raise import_row_invalid(
                        message="The payer partner could not be resolved.",
                        field_errors={"payer_partner_number": ["Partner not found or inactive."]},
                    )
                receipt, _created = create_draft(
                    actor=actor_instance,
                    source_channel="IMPORT",
                    receipt_date=row.data.get("receipt_date") or timezone.localdate(),
                    branch_id=branch.pk if branch else None,
                    partner_id=partner.pk,
                    payer_name=partner.display_name or str(partner),
                    source_module=(row.data.get("source_module") or "MANUAL").upper(),
                    source_reference_type="IMPORT",
                    source_reference_id=f"{batch.batch_number}:{row.row_number}",
                    currency=(row.data.get("currency_code") or "").upper() or default_currency(),
                    receipt_amount=row.data.get("amount"),
                    payment_mode=(row.data.get("payment_mode_code") or "CASH").upper(),
                    payment_reference=row.data.get("payment_reference") or "",
                    narration=(row.data.get("narration") or "") or f"Bulk import {batch.batch_number}",
                    idempotency_key=f"IMP:{batch.batch_number}:{row.row_hash[:20]}",
                )
                if (
                    batch.import_mode in (ReceiptImportMode.POST, ReceiptImportMode.ALLOCATE)
                    and receipt.status == ReceiptStatus.DRAFT
                ):
                    post_receipt(
                        receipt,
                        actor=actor_instance,
                        reason=f"Bulk import posting (batch {batch.batch_number}).",
                        source_channel="IMPORT",
                    )
                target = (row.data.get("target_commitment_number") or "").strip()
                if batch.import_mode == ReceiptImportMode.ALLOCATE and target:
                    allocate(
                        receipt,
                        target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
                        target_id=target,
                        amount=Decimal(row.data.get("amount")),
                        narration=(row.data.get("narration") or "")
                        or f"Bulk import allocation (batch {batch.batch_number}).",
                        actor=actor_instance,
                        source_channel="IMPORT",
                    )
                row.receipt = receipt
                row.status = ReceiptImportRowStatus.COMMITTED
                row.error_code = ""
                row.error_message = ""
                row.committed_at = timezone.now()
                row.save(
                    update_fields=["receipt", "status", "error_code", "error_message", "committed_at", "updated_at"]
                )
        except ReceiptError as exc:
            row.status = ReceiptImportRowStatus.FAILED
            row.error_code = exc.error_code or "RECEIPT_IMPORT_ROW_INVALID"
            row.error_message = str(exc) or "The row could not be imported."
            row.validation_errors = exc.field_errors or {}
            row.save(update_fields=["status", "error_code", "error_message", "validation_errors", "updated_at"])
        except Exception:
            # An unexpected failure must not abort the whole batch; the row
            # stays reprocessable by re-committing the batch.
            row.status = ReceiptImportRowStatus.FAILED
            row.error_code = "RECEIPT_IMPORT_ROW_INVALID"
            row.error_message = "Unexpected import error; the row can be reprocessed."
            row.save(update_fields=["status", "error_code", "error_message", "updated_at"])

    committed = batch.rows.filter(status=ReceiptImportRowStatus.COMMITTED).count()
    failed = batch.rows.filter(status=ReceiptImportRowStatus.FAILED).count()
    if committed and failed:
        batch.status = ReceiptImportBatchStatus.PARTIAL
    elif failed and not committed:
        batch.status = ReceiptImportBatchStatus.FAILED
    else:
        batch.status = ReceiptImportBatchStatus.COMMITTED
    batch.committed_rows = committed
    batch.failed_rows = failed
    batch.summary = {
        "total": batch.total_rows,
        "valid": batch.valid_rows,
        "invalid": batch.invalid_rows,
        "committed": committed,
        "failed": failed,
        "import_mode": batch.import_mode,
    }
    batch.save(update_fields=["status", "committed_rows", "failed_rows", "summary", "updated_at"])
    AuditService.log_action(
        "IMPORT_COMMIT",
        batch,
        actor=actor,
        after_state={"status": batch.status, "committed": committed, "failed": failed},
        reason="Receipt bulk import commit.",
        changed_fields=[],
    )
    return batch


def _resolution_steps_for(error_code):
    from apps.front_office.receipts.errors import RECEIPT_ERROR_REGISTRY

    entry = RECEIPT_ERROR_REGISTRY.get((error_code or "").strip().upper())
    return list(entry[2]) if entry else []


def import_row_payload(row):
    """Structured per-row payload for the dry-run / commit / detail responses."""
    return {
        "row_number": row.row_number,
        "row": row.row_number,
        "status": row.status,
        "data": row.data,
        "error_code": row.error_code or None,
        "errors": row.validation_errors or {},
        "field_errors": row.validation_errors or {},
        "resolution_steps": _resolution_steps_for(row.error_code),
        "message": row.error_message or None,
        "receipt_id": str(row.receipt_id) if row.receipt_id else None,
        "receipt_number": row.receipt.receipt_number if row.receipt_id else None,
        "committed_at": row.committed_at.isoformat() if row.committed_at else None,
    }
