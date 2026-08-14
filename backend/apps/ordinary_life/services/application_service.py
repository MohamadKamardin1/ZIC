import hashlib
import json
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.governance.models import ApprovalRequest
from apps.governance.services.approval_service import ApprovalService
from apps.governance.services.audit_service import AuditContext, AuditService
from apps.ordinary_life.models import (
    OLApplication,
    OLClient,
    OLHealthDeclaration,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthResponse,
    OLMedicalRequirement,
    OLMedicalResult,
    OLPaymentObligation,
    OLPlan,
    OLProductVersion,
    OLProposal,
    OLQuotation,
    OLQuotationVersion,
    OLRateBand,
    OLUnderwritingCase,
    OLUnderwritingDecisionEvent,
    OLWorkflowEvent,
)
from apps.partners.models import Partner
from apps.system_parameters.services.config_service import ConfigurationService
from apps.system_parameters.services.numbering_service import NumberingEngine

MONEY_QUANTUM = Decimal("0.01")
FREQUENCY_DIVISORS = {
    "MONTHLY": Decimal("12"),
    "QUARTERLY": Decimal("4"),
    "SEMI_ANNUAL": Decimal("2"),
    "ANNUAL": Decimal("1"),
}


class OrdinaryLifeApplicationService:
    """Transaction-safe application, quotation, underwriting, and approval workflow."""

    @staticmethod
    def _actor(actor=None):
        actor = actor or AuditContext.get_context().get("user")
        return actor if actor and not getattr(actor, "is_anonymous", False) else None

    @staticmethod
    def _require_actor(actor):
        actor = OrdinaryLifeApplicationService._actor(actor)
        if actor is None:
            raise ValidationError({"actor": "An authenticated decision actor is required."})
        return actor

    @staticmethod
    def _reason(reason, required=False):
        value = str(reason or "").strip()
        if required and not value:
            raise ValidationError({"reason": "A business reason is required for this operation."})
        return value

    @staticmethod
    def _validate_partner(partner, field):
        if not isinstance(partner, Partner):
            raise ValidationError({field: "A canonical Partner is required."})
        if not partner.is_active or partner.status != "ACTIVE":
            raise ValidationError({field: "The selected partner is not active."})
        return partner

    @staticmethod
    def _partner_snapshot(partner):
        return {
            "partner_id": str(partner.pk),
            "partner_number": partner.partner_number,
            "party_type": partner.party_type,
            "display_name": getattr(partner, "display_name", "") or partner.legal_name or f"{partner.first_name} {partner.surname}".strip(),
            "identification_type": partner.identification_type,
            "identification_number": partner.identification_number or partner.national_id or partner.registration_number,
            "date_of_birth": str(partner.date_of_birth) if partner.date_of_birth else None,
        }

    @staticmethod
    def _client_projection(partner):
        """Keep the legacy required OLClient field populated while Partner is canonical."""
        snapshot = OrdinaryLifeApplicationService._partner_snapshot(partner)
        client = OLClient.objects.filter(partner=partner).order_by("created_at").first()
        if client:
            return client
        identification = snapshot["identification_number"] or f"PARTNER-{partner.partner_number}"
        return OLClient.objects.create(
            partner=partner,
            first_name=partner.first_name or partner.legal_name or partner.company_name or "Partner",
            last_name=partner.surname or "",
            date_of_birth=partner.date_of_birth or timezone.localdate(),
            gender=partner.gender or "",
            id_number=identification,
            phone=getattr(partner, "mobile_number", "") or "",
            email=getattr(partner, "email", "") or "",
        )

    @staticmethod
    def _event(entity, action, actor=None, previous_status="", new_status="", reason="", metadata=None, before_state=None, after_state=None):
        actor = OrdinaryLifeApplicationService._actor(actor)
        reason = str(reason or "").strip()
        metadata = metadata or {}
        OLWorkflowEvent.objects.create(
            entity_type=entity._meta.model_name,
            entity_id=entity.pk,
            action=action,
            previous_status=previous_status or "",
            new_status=new_status or "",
            reason=reason,
            actor=actor,
            metadata=metadata,
        )
        AuditService.log(
            action_type=action,
            entity_type=entity._meta.model_name,
            entity_id=entity.pk,
            entity_repr=str(entity),
            actor=actor,
            description=reason,
            reason=reason,
            before_state=before_state or ({"status": previous_status} if previous_status else None),
            after_state=after_state or ({"status": new_status} if new_status else metadata),
        )

    @staticmethod
    def _set_status(entity, new_status, action, actor=None, reason="", allowed=None, extra=None):
        previous = entity.status
        if allowed is not None and previous not in allowed:
            raise ValidationError({"status": f"Cannot {action.lower()} from status {previous}."})
        if previous == new_status:
            return entity
        entity.status = new_status
        update_fields = ["status"]
        for field, value in (extra or {}).items():
            setattr(entity, field, value)
            update_fields.append(field)
        if hasattr(entity, "updated_at"):
            update_fields.append("updated_at")
        entity.save(update_fields=list(dict.fromkeys(update_fields)))
        OrdinaryLifeApplicationService._event(entity, action, actor, previous, new_status, reason)
        return entity

    @staticmethod
    def _money(value, field, positive=True):
        try:
            amount = Decimal(str(value))
        except (TypeError, ValueError):
            raise ValidationError({field: "Enter a valid decimal amount."}) from None
        if positive and amount <= 0:
            raise ValidationError({field: "Value must be greater than zero."})
        return amount

    @staticmethod
    def _age(date_of_birth, as_of):
        if not date_of_birth:
            raise ValidationError({"date_of_birth": "Date of birth is required for quotation."})
        years = as_of.year - date_of_birth.year
        if (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day):
            years -= 1
        return years

    @staticmethod
    def _active_product_version(product_version, as_of):
        if not isinstance(product_version, OLProductVersion):
            raise ValidationError({"product_version": "A product version is required."})
        if not product_version.is_active or not product_version.product.is_active:
            raise ValidationError({"product_version": "The selected product version is inactive."})
        if product_version.effective_from > as_of or (
            product_version.effective_to and product_version.effective_to < as_of
        ):
            raise ValidationError({"product_version": "The product version is not effective on the quotation date."})
        return product_version

    @staticmethod
    def _product_snapshot(product_version):
        return {
            "product_id": str(product_version.product_id),
            "product_code": product_version.product.code,
            "version_id": str(product_version.pk),
            "version_number": product_version.version_number,
            "effective_from": str(product_version.effective_from),
            "effective_to": str(product_version.effective_to) if product_version.effective_to else None,
            "currency": product_version.currency,
            "min_entry_age": product_version.min_entry_age,
            "max_entry_age": product_version.max_entry_age,
            "min_term_years": product_version.min_term_years,
            "max_term_years": product_version.max_term_years,
            "payment_frequencies": list(product_version.payment_frequencies or []),
            "underwriting_rules": product_version.underwriting_rules or {},
            "servicing_rules": product_version.servicing_rules or {},
            "snapshot": product_version.snapshot or {},
        }

    @staticmethod
    def _normalise_inputs(inputs):
        return json.loads(json.dumps(inputs or {}, default=str, sort_keys=True))

    @staticmethod
    def _rate_band(product_version, plan, age, term_years):
        query = OLRateBand.objects.filter(
            product_version=product_version,
            is_active=True,
            min_age__lte=age,
            max_age__gte=age,
            min_term_years__lte=term_years,
            max_term_years__gte=term_years,
        )
        if plan:
            query = query.filter(plan=plan)
        else:
            query = query.filter(plan__isnull=True)
        band = query.order_by("min_age", "min_term_years", "pk").first()
        if not band:
            raise ValidationError({"product_version": "No active rate band covers the selected age and term."})
        return band

    @staticmethod
    def _medical_requirement_types(product_version, medical_required):
        rules = product_version.underwriting_rules or {}
        configured = rules.get("medical_requirements") or rules.get("required_medical_tests") or []
        if isinstance(configured, str):
            configured = [configured]
        values = [str(value).strip().upper() for value in configured if str(value).strip()]
        if medical_required and not values:
            values = ["GENERAL_MEDICAL_EXAM"]
        return list(dict.fromkeys(values))

    @classmethod
    @transaction.atomic
    def create_application(cls, partner, policyholder, life_assured, payer=None, declarations=None, actor=None):
        actor = cls._require_actor(actor)
        for value, field in ((partner, "partner"), (policyholder, "policyholder"), (life_assured, "life_assured")):
            cls._validate_partner(value, field)
        if payer is not None:
            cls._validate_partner(payer, "payer")
        application = OLApplication.objects.create(
            application_number=NumberingEngine.generate_number("OL_APPLICATION", OLApplication, field_name="application_number"),
            partner=partner,
            policyholder=policyholder,
            life_assured=life_assured,
            payer=payer,
            declarations=declarations or {},
            status="DRAFT",
        )
        cls._event(application, "CREATE_APPLICATION", actor=actor, new_status=application.status, reason="Application created")
        return application

    @classmethod
    @transaction.atomic
    def submit_application(cls, application, actor=None, reason=""):
        actor = cls._require_actor(actor)
        application = OLApplication.objects.select_for_update().select_related(
            "partner", "policyholder", "life_assured", "payer"
        ).get(pk=application.pk)
        if application.status != "DRAFT":
            raise ValidationError({"status": "Only draft applications can be submitted."})
        if not application.declarations:
            raise ValidationError({"declarations": "Declarations are required before submission."})
        for value, field in (
            (application.partner, "partner"),
            (application.policyholder, "policyholder"),
            (application.life_assured, "life_assured"),
        ):
            cls._validate_partner(value, field)
        if application.payer_id:
            cls._validate_partner(application.payer, "payer")
        now = timezone.now()
        old = application.status
        application.status = "SUBMITTED"
        application.submitted_at = now
        application.save(update_fields=["status", "submitted_at", "updated_at"])
        cls._event(application, "SUBMIT_APPLICATION", actor=actor, previous_status=old, new_status=application.status, reason=cls._reason(reason))
        return application

    @classmethod
    @transaction.atomic
    def create_quotation(cls, application, product_version, sum_assured, term_years, payment_frequency, plan=None, rider_codes=None, actor=None):
        actor = cls._require_actor(actor)
        if application.status not in {"DRAFT", "SUBMITTED"}:
            raise ValidationError({"application": "A quotation can only be created for a draft or submitted application."})
        cls._validate_partner(application.partner, "partner")
        as_of = timezone.localdate()
        cls._active_product_version(product_version, as_of)
        client = cls._client_projection(application.policyholder)
        quotation = OLQuotation.objects.create(
            quotation_number=NumberingEngine.generate_number("OL_QUOTATION", OLQuotation, field_name="quotation_number"),
            client=client,
            partner=application.partner,
            product=product_version.product,
            product_version=product_version,
            sum_assured=cls._money(sum_assured, "sum_assured"),
            premium_amount=Decimal("0.00"),
            currency=product_version.currency,
            payment_frequency=str(payment_frequency).upper(),
            status="DRAFT",
        )
        version = cls.calculate_quotation(
            quotation=quotation,
            product_version=product_version,
            sum_assured=sum_assured,
            term_years=term_years,
            payment_frequency=payment_frequency,
            plan=plan,
            rider_codes=rider_codes,
            actor=actor,
        )
        quotation.refresh_from_db()
        cls._event(quotation, "CREATE_QUOTATION", actor=actor, new_status=quotation.status, reason="Quotation created", metadata={"application_id": str(application.pk), "version_id": str(version.pk)})
        return quotation

    @classmethod
    @transaction.atomic
    def calculate_quotation(cls, quotation, product_version, sum_assured, term_years, payment_frequency, plan=None, rider_codes=None, actor=None):
        actor = cls._require_actor(actor)
        quotation = OLQuotation.objects.select_for_update().select_related("client", "product").get(pk=quotation.pk)
        if quotation.status != "DRAFT":
            raise ValidationError({"status": "Only draft quotations can be calculated or revised."})
        as_of = timezone.localdate()
        product_version = OLProductVersion.objects.select_for_update().select_related("product").get(pk=product_version.pk)
        cls._active_product_version(product_version, as_of)
        amount = cls._money(sum_assured, "sum_assured")
        try:
            term = int(term_years)
        except (TypeError, ValueError):
            raise ValidationError({"term_years": "Term must be a whole number of years."}) from None
        frequency = str(payment_frequency).upper()
        if frequency not in FREQUENCY_DIVISORS:
            raise ValidationError({"payment_frequency": f"Unsupported payment frequency: {frequency}."})
        if product_version.payment_frequencies and frequency not in product_version.payment_frequencies:
            raise ValidationError({"payment_frequency": "The selected frequency is not allowed by the product version."})
        age = cls._age(quotation.client.date_of_birth, as_of)
        if not product_version.min_entry_age <= age <= product_version.max_entry_age:
            raise ValidationError({"age": "The life assured is outside the product entry-age range."})
        if not product_version.min_term_years <= term <= product_version.max_term_years:
            raise ValidationError({"term_years": "The selected term is outside the product range."})
        selected_plan = plan
        if selected_plan is not None:
            if not isinstance(selected_plan, OLPlan) or selected_plan.product_version_id != product_version.pk or not selected_plan.is_active:
                raise ValidationError({"plan": "The selected plan does not belong to the active product version."})
            if selected_plan.minimum_sum_assured and amount < selected_plan.minimum_sum_assured:
                raise ValidationError({"sum_assured": "Sum assured is below the selected plan minimum."})
            if selected_plan.maximum_sum_assured and amount > selected_plan.maximum_sum_assured:
                raise ValidationError({"sum_assured": "Sum assured exceeds the selected plan maximum."})
        band = cls._rate_band(product_version, selected_plan, age, term)
        rider_codes = [str(code).upper() for code in (rider_codes or [])]
        riders = list(product_version.riders.select_related("rider").filter(is_active=True, rider__is_active=True, rider__code__in=rider_codes))
        found_codes = {item.rider.code for item in riders}
        unknown = sorted(set(rider_codes) - found_codes)
        if unknown:
            raise ValidationError({"riders": f"Unknown or ineligible riders: {', '.join(unknown)}."})
        annual_base = (amount * band.rate).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        annual_riders = sum((amount * (item.premium_rate or Decimal("0")) for item in riders), Decimal("0"))
        annual_premium = (annual_base + annual_riders).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        installment_premium = (annual_premium / FREQUENCY_DIVISORS[frequency]).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if annual_premium <= 0:
            raise ValidationError({"premium_amount": "The configured rate produced a non-positive premium."})
        inputs = cls._normalise_inputs({
            "as_of": as_of,
            "age": age,
            "sum_assured": amount,
            "term_years": term,
            "payment_frequency": frequency,
            "currency": product_version.currency,
            "plan_code": selected_plan.code if selected_plan else None,
            "rider_codes": sorted(rider_codes),
            "calculation_engine": "ordinary-life-v1",
        })
        outputs = {
            "annual_base_premium": str(annual_base),
            "annual_rider_premium": str(annual_riders.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)),
            "annual_premium": str(annual_premium),
            "installment_premium": str(installment_premium),
            "frequency_divisor": str(FREQUENCY_DIVISORS[frequency]),
            "rate": str(band.rate),
            "rate_band_id": str(band.pk),
            "currency": product_version.currency,
        }
        product_snapshot = cls._product_snapshot(product_version)
        canonical = json.dumps({"inputs": inputs, "outputs": outputs, "product": product_snapshot}, sort_keys=True, separators=(",", ":"))
        calculation_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = quotation.versions.filter(calculation_hash=calculation_hash).first()
        if existing:
            quotation.current_version = existing
            quotation.product_version = product_version
            quotation.sum_assured = amount
            quotation.premium_amount = installment_premium
            quotation.currency = product_version.currency
            quotation.payment_frequency = frequency
            quotation.save(update_fields=["current_version", "product_version", "sum_assured", "premium_amount", "currency", "payment_frequency", "updated_at"])
            return existing
        version_number = (quotation.versions.aggregate(max_version=Max("version_number"))["max_version"] or 0) + 1
        version = OLQuotationVersion.objects.create(
            quotation=quotation,
            version_number=version_number,
            product_version=product_version,
            inputs=inputs,
            calculated_outputs=outputs,
            product_version_snapshot=product_snapshot,
            calculation_hash=calculation_hash,
            created_by=actor,
        )
        quotation.current_version = version
        quotation.product_version = product_version
        quotation.sum_assured = amount
        quotation.premium_amount = installment_premium
        quotation.currency = product_version.currency
        quotation.payment_frequency = frequency
        quotation.save(update_fields=["current_version", "product_version", "sum_assured", "premium_amount", "currency", "payment_frequency", "updated_at"])
        cls._event(quotation, "CALCULATE_QUOTATION", actor=actor, reason="Immutable quotation version calculated", metadata={"version_id": str(version.pk), "calculation_hash": calculation_hash})
        return version

    @classmethod
    @transaction.atomic
    def submit_quotation(cls, quotation, actor=None, reason=""):
        actor = cls._require_actor(actor)
        quotation = OLQuotation.objects.select_for_update().select_related("product", "current_version").get(pk=quotation.pk)
        if quotation.status != "DRAFT":
            raise ValidationError({"status": "Only draft quotations can be submitted."})
        if not quotation.current_version_id:
            raise ValidationError({"current_version": "A calculated quotation version is required before submission."})
        if quotation.current_version.product_version_id != quotation.product_version_id:
            raise ValidationError({"current_version": "Quotation and current version product configuration do not match."})
        validity_days = ConfigurationService.get_int_parameter("OL_QUOTATION_VALID_DAYS", 30)
        if validity_days <= 0:
            validity_days = 30
        now = timezone.now()
        old = quotation.status
        quotation.status = "SUBMITTED"
        quotation.expires_at = now + timedelta(days=validity_days)
        quotation.save(update_fields=["status", "expires_at", "updated_at"])
        cls._event(quotation, "SUBMIT_QUOTATION", actor=actor, previous_status=old, new_status=quotation.status, reason=cls._reason(reason), metadata={"expires_at": quotation.expires_at.isoformat()})
        return quotation

    @classmethod
    @transaction.atomic
    def convert_quotation_to_proposal(cls, quotation, application=None, actor=None, reason=""):
        actor = cls._require_actor(actor)
        quotation = OLQuotation.objects.select_for_update().select_related("product", "current_version", "partner").get(pk=quotation.pk)
        if hasattr(quotation, "proposal"):
            return quotation.proposal
        if quotation.status != "SUBMITTED":
            raise ValidationError({"status": "Only submitted quotations can be converted to proposals."})
        if quotation.expires_at and quotation.expires_at <= timezone.now():
            cls._set_status(quotation, "EXPIRED", "EXPIRE_QUOTATION", actor=actor, reason="Quotation expired before conversion", allowed={"SUBMITTED"})
            raise ValidationError({"status": "The quotation has expired."})
        if not quotation.current_version_id:
            raise ValidationError({"current_version": "A current quotation version is required."})
        if application is not None:
            application = OLApplication.objects.select_for_update().get(pk=application.pk)
            if application.status not in {"DRAFT", "SUBMITTED"}:
                raise ValidationError({"application": "The application is not eligible for proposal conversion."})
            if application.partner_id != quotation.partner_id:
                raise ValidationError({"application": "Application and quotation partner do not match."})
        medical_required = bool((quotation.product_version.underwriting_rules or {}).get("medical_required", False))
        threshold = ConfigurationService.get_parameter("OL_MEDICAL_SUM_ASSURED_LIMIT", "100000000")
        try:
            medical_required = medical_required or quotation.sum_assured >= Decimal(str(threshold))
        except (TypeError, ValueError):
            medical_required = medical_required or quotation.sum_assured >= Decimal("100000000")
        proposal = OLProposal.objects.create(
            proposal_number=NumberingEngine.generate_number("OL_PROPOSAL", OLProposal, field_name="proposal_number"),
            quotation=quotation,
            quotation_version=quotation.current_version,
            medical_required=medical_required,
            underwriting_status="PENDING",
            status="PENDING",
            payment_required_amount=quotation.premium_amount,
            payment_currency=quotation.currency,
        )
        if application is not None:
            application.proposal = proposal
            application.save(update_fields=["proposal", "updated_at"])
        cls._set_status(quotation, "CONVERTED", "CONVERT_QUOTATION", actor=actor, reason=cls._reason(reason), allowed={"SUBMITTED"})
        cls._event(proposal, "CREATE_PROPOSAL", actor=actor, new_status=proposal.status, reason=cls._reason(reason), metadata={"quotation_id": str(quotation.pk), "quotation_version_id": str(quotation.current_version_id)})
        return proposal

    @classmethod
    @transaction.atomic
    def start_underwriting(cls, proposal, actor=None, reason=""):
        actor = cls._require_actor(actor)
        proposal = OLProposal.objects.select_for_update().select_related("quotation_version", "quotation_version__product_version").get(pk=proposal.pk)
        try:
            return proposal.underwriting_case
        except OLUnderwritingCase.DoesNotExist:
            pass
        if proposal.status not in {"PENDING", "REFERRED"}:
            raise ValidationError({"status": "Only pending or referred proposals can enter underwriting."})
        if not proposal.quotation_version_id:
            raise ValidationError({"quotation_version": "Proposal must reference an immutable quotation version."})
        previous_status = proposal.status
        case = OLUnderwritingCase.objects.create(
            proposal=proposal,
            decision="PENDING",
            risk_class="STANDARD",
            started_at=timezone.now(),
        )
        proposal.status = "UNDERWRITING"
        proposal.underwriting_status = "PENDING"
        proposal.save(update_fields=["status", "underwriting_status", "updated_at"])
        requirements = cls._medical_requirement_types(proposal.quotation_version.product_version, proposal.medical_required)
        for requirement_type in requirements:
            OLMedicalRequirement.objects.get_or_create(
                underwriting_case=case,
                requirement_type=requirement_type,
                defaults={"status": "PENDING", "reason": "Required by product underwriting rules."},
            )
        cls._event(proposal, "START_UNDERWRITING", actor=actor, previous_status=previous_status, new_status=proposal.status, reason=cls._reason(reason), metadata={"underwriting_case_id": str(case.pk), "medical_requirement_count": len(requirements)})
        cls._event(case, "CREATE_UNDERWRITING_CASE", actor=actor, new_status=case.decision, reason="Underwriting case opened", metadata={"proposal_id": str(proposal.pk)})
        return case

    @classmethod
    @transaction.atomic
    def record_health_declaration(cls, proposal, questionnaire=None, responses=None, actor=None, reason=""):
        actor = cls._require_actor(actor)
        proposal = OLProposal.objects.select_for_update().get(pk=proposal.pk)
        if proposal.status not in {"UNDERWRITING", "REFERRED"}:
            raise ValidationError({"status": "Health declarations can only be recorded during underwriting."})
        questionnaire = questionnaire or OLHealthQuestionnaire.objects.filter(is_active=True).order_by("-effective_date", "-version").first()
        if not questionnaire:
            raise ValidationError({"questionnaire": "An active health questionnaire is required."})
        responses = responses or []
        response_by_code = {str(item.get("question_code") or item.get("code") or "").upper(): item for item in responses if isinstance(item, dict)}
        required_questions = list(OLHealthQuestion.objects.filter(is_active=True).order_by("code"))
        missing = [question.code for question in required_questions if question.code not in response_by_code]
        version_number = (proposal.health_declarations.aggregate(max_version=Max("version_number"))["max_version"] or 0) + 1
        declaration = OLHealthDeclaration.objects.create(
            proposal=proposal,
            questionnaire=questionnaire,
            version_number=version_number,
            is_complete=not missing,
            submitted_at=timezone.now() if not missing else None,
        )
        questions = {question.code: question for question in required_questions}
        for code, payload in response_by_code.items():
            question = questions.get(code) or OLHealthQuestion.objects.filter(code=code, is_active=True).first()
            if not question:
                raise ValidationError({"responses": f"Unknown active health question: {code}."})
            OLHealthResponse.objects.create(
                declaration=declaration,
                question=question,
                answer=payload.get("answer", {}),
                detail=str(payload.get("detail", "")),
            )
        cls._event(declaration, "RECORD_HEALTH_DECLARATION", actor=actor, new_status="COMPLETE" if declaration.is_complete else "INCOMPLETE", reason=cls._reason(reason), metadata={"response_count": len(response_by_code), "missing_question_count": len(missing)})
        return declaration

    @classmethod
    @transaction.atomic
    def record_medical_result(cls, requirement, result, evidence_reference="", result_data=None, actor=None, reason=""):
        actor = cls._require_actor(actor)
        requirement = OLMedicalRequirement.objects.select_for_update().select_related("underwriting_case", "underwriting_case__proposal").get(pk=requirement.pk)
        if requirement.status in {"VERIFIED", "WAIVED"}:
            raise ValidationError({"status": "A resolved medical requirement cannot be changed without a controlled reopen."})
        result_value = str(result or "").strip().upper()
        if not result_value:
            raise ValidationError({"result": "A medical result is required."})
        medical_result, created = OLMedicalResult.objects.get_or_create(
            requirement=requirement,
            defaults={"result": result_value, "evidence_reference": str(evidence_reference or ""), "result_data": result_data or {}},
        )
        if not created:
            medical_result.result = result_value
            medical_result.evidence_reference = str(evidence_reference or "")
            medical_result.result_data = result_data or {}
            medical_result.verified_by = None
            medical_result.verified_at = None
            medical_result.save(update_fields=["result", "evidence_reference", "result_data", "verified_by", "verified_at"])
        previous = requirement.status
        requirement.status = "UPLOADED"
        requirement.reason = cls._reason(reason)
        requirement.save(update_fields=["status", "reason", "updated_at"])
        cls._event(requirement, "RECORD_MEDICAL_RESULT", actor=actor, previous_status=previous, new_status=requirement.status, reason=cls._reason(reason), metadata={"result_id": str(medical_result.pk), "evidence_reference": medical_result.evidence_reference})
        return medical_result

    @classmethod
    @transaction.atomic
    def verify_medical_requirement(cls, requirement, actor=None, reason=""):
        actor = cls._require_actor(actor)
        requirement = OLMedicalRequirement.objects.select_for_update().select_related("underwriting_case").get(pk=requirement.pk)
        if requirement.status != "UPLOADED":
            raise ValidationError({"status": "Only uploaded medical evidence can be verified."})
        medical_result = getattr(requirement, "result", None)
        if medical_result is None:
            raise ValidationError({"result": "A medical result must be recorded before verification."})
        now = timezone.now()
        medical_result.verified_by = actor
        medical_result.verified_at = now
        medical_result.save(update_fields=["verified_by", "verified_at"])
        previous = requirement.status
        requirement.status = "VERIFIED"
        requirement.reason = cls._reason(reason)
        requirement.save(update_fields=["status", "reason", "updated_at"])
        cls._event(requirement, "VERIFY_MEDICAL_REQUIREMENT", actor=actor, previous_status=previous, new_status=requirement.status, reason=cls._reason(reason), metadata={"medical_result_id": str(medical_result.pk)})
        return requirement

    @classmethod
    @transaction.atomic
    def assess_risk(cls, underwriting_case, decision, risk_class="STANDARD", actor=None, reason=""):
        actor = cls._require_actor(actor)
        underwriting_case = OLUnderwritingCase.objects.select_for_update().select_related("proposal", "proposal__quotation_version").get(pk=underwriting_case.pk)
        decision = str(decision or "").upper()
        if decision not in {"APPROVED", "REFERRED", "DECLINED", "POSTPONED"}:
            raise ValidationError({"decision": "Decision must be APPROVED, REFERRED, DECLINED, or POSTPONED."})
        reason = cls._reason(reason, required=True)
        if underwriting_case.decision not in {"PENDING", "REFERRED", "POSTPONED"}:
            raise ValidationError({"decision": "This underwriting case is already decided."})
        requirements = list(underwriting_case.medical_requirements.all())
        unresolved = [item.requirement_type for item in requirements if item.status not in {"VERIFIED", "WAIVED"}]
        if decision == "APPROVED" and unresolved:
            raise ValidationError({"medical_requirements": f"Resolve required medical evidence first: {', '.join(unresolved)}."})
        previous_decision = underwriting_case.decision
        now = timezone.now()
        underwriting_case.decision = decision
        underwriting_case.risk_class = str(risk_class or "STANDARD").upper()
        underwriting_case.decision_reason = reason
        underwriting_case.reviewer = actor
        underwriting_case.decided_at = now
        underwriting_case.save(update_fields=["decision", "risk_class", "decision_reason", "reviewer", "decided_at", "updated_at"])
        OLUnderwritingDecisionEvent.objects.create(
            underwriting_case=underwriting_case,
            previous_decision=previous_decision,
            decision=decision,
            risk_class=underwriting_case.risk_class,
            reason=reason,
            actor=actor,
            metadata={"unresolved_requirements": unresolved},
        )
        proposal = underwriting_case.proposal
        proposal.underwriting_status = decision
        proposal_status = {
            "APPROVED": "PENDING",
            "REFERRED": "REFERRED",
            "DECLINED": "DECLINED",
            "POSTPONED": "UNDERWRITING",
        }[decision]
        proposal.status = proposal_status
        update_fields = ["underwriting_status", "status", "updated_at"]
        if decision == "DECLINED":
            proposal.declined_at = now
            update_fields.append("declined_at")
        proposal.save(update_fields=update_fields)
        cls._event(underwriting_case, "ASSESS_RISK", actor=actor, previous_status=previous_decision, new_status=decision, reason=reason, metadata={"proposal_id": str(proposal.pk), "risk_class": underwriting_case.risk_class})
        cls._event(proposal, "UNDERWRITING_DECISION", actor=actor, previous_status="UNDERWRITING", new_status=proposal.status, reason=reason, metadata={"decision": decision, "underwriting_case_id": str(underwriting_case.pk)})
        return underwriting_case

    @classmethod
    @transaction.atomic
    def submit_proposal_for_approval(cls, proposal, actor=None, comments=""):
        actor = cls._require_actor(actor)
        proposal = OLProposal.objects.select_for_update().select_related("quotation", "quotation_version").get(pk=proposal.pk)
        if proposal.status != "PENDING" or proposal.underwriting_status != "APPROVED":
            raise ValidationError({"status": "Only proposals with approved underwriting are eligible for business approval."})
        pending = ApprovalRequest.objects.filter(
            module="ORDINARY_LIFE",
            entity_type="OLProposal",
            entity_id=proposal.pk,
            action="APPROVE",
            status="PENDING",
        ).first()
        if pending:
            return pending
        if not ApprovalService.requires_approval("ORDINARY_LIFE", "OLPROPOSAL", "APPROVE"):
            return cls.approve_proposal(proposal, actor=actor, reason=comments or "Approval not required by configuration")
        return ApprovalService.submit(
            module="ORDINARY_LIFE",
            entity_type="OLProposal",
            entity_id=proposal.pk,
            action="APPROVE",
            requested_data={"proposal_number": proposal.proposal_number, "amount": str(proposal.payment_required_amount or proposal.quotation.premium_amount)},
            current_data={"status": proposal.status, "underwriting_status": proposal.underwriting_status},
            entity_repr=str(proposal),
            submitted_by=actor,
            comments=cls._reason(comments),
        )

    @classmethod
    @transaction.atomic
    def approve_proposal(cls, proposal, actor=None, reason=""):
        actor = cls._require_actor(actor)
        proposal = OLProposal.objects.select_for_update().select_related("quotation").get(pk=proposal.pk)
        if proposal.status != "PENDING":
            raise ValidationError({"status": "Only pending proposals can be approved."})
        if proposal.underwriting_status != "APPROVED":
            raise ValidationError({"underwriting_status": "Proposal must have approved underwriting first."})
        now = timezone.now()
        proposal.status = "APPROVED"
        proposal.approved_at = now
        proposal.payment_required_amount = proposal.payment_required_amount or proposal.quotation.premium_amount
        proposal.payment_currency = proposal.payment_currency or proposal.quotation.currency
        proposal.save(update_fields=["status", "approved_at", "payment_required_amount", "payment_currency", "updated_at"])
        obligation, created = OLPaymentObligation.objects.get_or_create(
            proposal=proposal,
            obligation_type="FIRST_PREMIUM",
            defaults={
                "amount": proposal.payment_required_amount,
                "currency": proposal.payment_currency,
                "due_date": timezone.localdate(),
                "status": "DUE",
            },
        )
        cls._event(proposal, "APPROVE_PROPOSAL", actor=actor, previous_status="PENDING", new_status=proposal.status, reason=cls._reason(reason), metadata={"payment_obligation_id": str(obligation.pk), "payment_obligation_created": created})
        return proposal

    @classmethod
    @transaction.atomic
    def complete_business_approval(cls, approval_id, reviewer, comments=""):
        reviewer = cls._require_actor(reviewer)
        approval = ApprovalService.approve(approval_id, reviewer, comments=comments)
        if approval.module != "ORDINARY_LIFE" or approval.entity_type != "OLProposal" or approval.action != "APPROVE":
            return approval
        proposal = OLProposal.objects.get(pk=approval.entity_id)
        cls.approve_proposal(proposal, actor=reviewer, reason=comments or "Business approval completed")
        return approval

    @classmethod
    @transaction.atomic
    def reject_business_approval(cls, approval_id, reviewer, comments=""):
        reviewer = cls._require_actor(reviewer)
        comments = cls._reason(comments, required=True)
        approval = ApprovalService.reject(approval_id, reviewer, comments=comments)
        if approval.module != "ORDINARY_LIFE" or approval.entity_type != "OLProposal" or approval.action != "APPROVE":
            return approval
        proposal = OLProposal.objects.get(pk=approval.entity_id)
        if proposal.status == "PENDING":
            proposal.status = "DECLINED"
            proposal.declined_at = timezone.now()
            proposal.save(update_fields=["status", "declined_at", "updated_at"])
            cls._event(proposal, "REJECT_PROPOSAL_APPROVAL", actor=reviewer, previous_status="PENDING", new_status=proposal.status, reason=comments, metadata={"approval_id": str(approval.pk)})
        return approval

    @classmethod
    @transaction.atomic
    def reopen_underwriting(cls, underwriting_case, actor=None, reason=""):
        actor = cls._require_actor(actor)
        reason = cls._reason(reason, required=True)
        underwriting_case = OLUnderwritingCase.objects.select_for_update().select_related("proposal").get(pk=underwriting_case.pk)
        if underwriting_case.decision not in {"DECLINED", "POSTPONED", "REFERRED"}:
            raise ValidationError({"decision": "Only declined, postponed, or referred cases can be reopened."})
        previous = underwriting_case.decision
        underwriting_case.reopened_at = timezone.now()
        underwriting_case.decision = "PENDING"
        underwriting_case.decision_reason = ""
        underwriting_case.decided_at = None
        underwriting_case.reviewer = None
        underwriting_case.save(update_fields=["reopened_at", "decision", "decision_reason", "decided_at", "reviewer", "updated_at"])
        proposal = underwriting_case.proposal
        proposal.status = "UNDERWRITING"
        proposal.underwriting_status = "PENDING"
        proposal.save(update_fields=["status", "underwriting_status", "updated_at"])
        OLUnderwritingDecisionEvent.objects.create(
            underwriting_case=underwriting_case,
            previous_decision=previous,
            decision="PENDING",
            risk_class=underwriting_case.risk_class,
            reason=reason,
            actor=actor,
            metadata={"reopened": True},
        )
        cls._event(underwriting_case, "REOPEN_UNDERWRITING", actor=actor, previous_status=previous, new_status="PENDING", reason=reason)
        return underwriting_case
