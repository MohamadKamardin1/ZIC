import logging
from datetime import date

from django.db.models import Max

from .config_service import ConfigurationService, ConfigurationError

logger = logging.getLogger(__name__)


class NumberingEngine:
    """Configuration-driven numbering engine.

    Generates sequential numbers for applications, partners, policies, etc.
    All prefixes, formats, and padding are driven by System Parameters.
    """

    @staticmethod
    def get_prefix_config(numbering_code: str) -> dict:
        """Return numbering configuration for a given code.

        Expected System Parameters:
          {numbering_code}_PREFIX         -> str (e.g. "PA", "PN")
          SEQUENCE_PADDING               -> int (e.g. 6)
          INCLUDE_YEAR                   -> bool
        """
        prefix = ConfigurationService.get_str_parameter(
            f"{numbering_code}_PREFIX", numbering_code
        )
        padding = ConfigurationService.get_int_parameter("SEQUENCE_PADDING", 6)
        include_year = ConfigurationService.get_bool_parameter("INCLUDE_YEAR", True)
        return {
            "prefix": prefix,
            "padding": padding,
            "include_year": include_year,
        }

    @staticmethod
    def generate_number(
        numbering_code: str,
        model_class,
        filter_kwargs: dict | None = None,
        field_name: str = "application_number",
        prefix_field: str | None = None,
        context: dict | None = None,
    ) -> str:
        """Generate a sequential number using configuration-driven format.

        Args:
            numbering_code: Configuration code (e.g. "INDIVIDUAL_APP", "PARTNER")
            model_class: Django model class to query for existing numbers
            filter_kwargs: Additional filters for the sequence query
            field_name: The model field storing the number
            prefix_field: If provided, use a context value as prefix (e.g. partner_type)
            context: Optional context dict (e.g. {"partner_type": "INDIVIDUAL"})

        Returns:
            Formatted number string
        """
        cfg = NumberingEngine.get_prefix_config(numbering_code)

        prefix = cfg["prefix"]
        padding = cfg["padding"]
        include_year = cfg["include_year"]

        # Allow dynamic prefix from context
        if prefix_field and context and context.get(prefix_field):
            from apps.system_parameters.models import SystemParameter
            partner_type = context[prefix_field]
            specific_code = f"{partner_type}_{numbering_code.split('_', 1)[-1] if '_' in numbering_code else numbering_code}_PREFIX"
            specific_prefix = ConfigurationService.get_str_parameter(specific_code, "")
            if specific_prefix:
                prefix = specific_prefix

        today = date.today()
        year = today.year

        # Build the query prefix
        query_prefix = f"{prefix}-"
        if include_year:
            query_prefix += f"{year}-"

        filters = {f"{field_name}__startswith": query_prefix}
        if filter_kwargs:
            filters.update(filter_kwargs)

        last = (
            model_class.objects
            .filter(**filters)
            .aggregate(last_num=Max(field_name))
        )["last_num"]

        if last:
            try:
                parts = str(last).split("-")
                num = int(parts[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1

        sequence = str(num).zfill(padding)

        if include_year:
            return f"{prefix}-{year}-{sequence}"
        return f"{prefix}-{sequence}"

    @staticmethod
    def generate_application_number(partner_type: str = "INDIVIDUAL") -> str:
        """Generate an application number using configured prefixes."""
        from apps.partner_onboarding.models import PartnerApplication

        code = "INDIVIDUAL_APP" if partner_type == "INDIVIDUAL" else "CORPORATE_APP"
        return NumberingEngine.generate_number(
            numbering_code=code,
            model_class=PartnerApplication,
            context={"partner_type": partner_type},
            prefix_field="partner_type",
        )

    @staticmethod
    def generate_partner_number() -> str:
        """Generate a partner number using configured prefix."""
        from apps.partners.models import Partner

        return NumberingEngine.generate_number(
            numbering_code="PARTNER",
            model_class=Partner,
            field_name="partner_number",
        )


# Module-level convenience
numbering = NumberingEngine
