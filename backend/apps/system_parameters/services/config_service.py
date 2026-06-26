import logging
from functools import lru_cache
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes


class ConfigurationError(Exception):
    pass


class ConfigurationService:
    """Central configuration service that reads from System Parameters and Choice Lists.

    All business configuration flows through this service. It provides:
    - Choice list options (dropdown values)
    - System parameter values (key-value config)
    - Workflow definitions
    - Numbering formats
    - Compliance rules
    - Document upload rules

    Results are cached with a configurable TTL and invalidated on config changes.
    """

    # ------------------------------------------------------------------
    # Choice List access
    # ------------------------------------------------------------------

    @staticmethod
    def get_choice_list(code: str, active_only: bool = True) -> list[dict]:
        """Return a choice list as a list of {value, label} dicts."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        cache_key = f"config:choice_list:{code}:active={active_only}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except ChoiceList.DoesNotExist:
            logger.error("Choice list '%s' not found in database.", code)
            raise ConfigurationError(f"Choice list '{code}' is not configured.")

        qs = ChoiceOption.objects.filter(choice_list=cl)
        if active_only:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("sort_order", "label")

        result = [{"value": o.code, "label": o.label} for o in qs]
        cache.set(cache_key, result, CACHE_TTL)
        return result

    @staticmethod
    def get_choice_options(code: str, active_only: bool = True) -> list:
        """Return raw ChoiceOption queryset evaluated as list."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        cache_key = f"config:choice_options:{code}:active={active_only}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except ChoiceList.DoesNotExist:
            raise ConfigurationError(f"Choice list '{code}' is not configured.")

        qs = ChoiceOption.objects.filter(choice_list=cl)
        if active_only:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("sort_order", "label")
        result = list(qs)
        cache.set(cache_key, result, CACHE_TTL)
        return result

    @staticmethod
    def get_default_choice(code: str) -> str | None:
        """Return the default option code for a choice list, or None."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except ChoiceList.DoesNotExist:
            return None

        default = ChoiceOption.objects.filter(
            choice_list=cl, is_active=True, is_default=True
        ).first()
        return default.code if default else None

    @staticmethod
    def choice_list_exists(code: str) -> bool:
        from apps.system_parameters.models import ChoiceList
        return ChoiceList.objects.filter(code=code, is_active=True).exists()

    @staticmethod
    def validate_choice(code: str, value: str) -> bool:
        """Check whether a value is valid for a given choice list."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except ChoiceList.DoesNotExist:
            return False
        return ChoiceOption.objects.filter(
            choice_list=cl, code=value, is_active=True
        ).exists()

    # ------------------------------------------------------------------
    # System Parameter access
    # ------------------------------------------------------------------

    @staticmethod
    def get_parameter(code: str, default=None):
        """Return the value of a system parameter by code."""
        from apps.system_parameters.models import SystemParameter

        cache_key = f"config:parameter:{code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            param = SystemParameter.objects.get(code=code, is_active=True)
        except SystemParameter.DoesNotExist:
            logger.warning("System parameter '%s' not found, returning default=%s", code, default)
            return default

        result = param.value
        cache.set(cache_key, result, CACHE_TTL)
        return result

    @staticmethod
    def get_parameter_or_raise(code: str):
        """Return value or raise ConfigurationError."""
        from apps.system_parameters.models import SystemParameter

        try:
            param = SystemParameter.objects.get(code=code, is_active=True)
        except SystemParameter.DoesNotExist:
            raise ConfigurationError(f"Required system parameter '{code}' is not configured.")
        return param.value

    @staticmethod
    def get_json_parameter(code: str, default=None) -> dict | list | None:
        """Convenience: get a JSON-typed parameter."""
        val = ConfigurationService.get_parameter(code, default)
        if val is None:
            return default
        return val

    @staticmethod
    def get_int_parameter(code: str, default: int = 0) -> int:
        val = ConfigurationService.get_parameter(code, default)
        return int(val) if val is not None else default

    @staticmethod
    def get_bool_parameter(code: str, default: bool = False) -> bool:
        val = ConfigurationService.get_parameter(code, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val) if val is not None else default

    @staticmethod
    def get_str_parameter(code: str, default: str = "") -> str:
        val = ConfigurationService.get_parameter(code, default)
        return str(val) if val is not None else default

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    @staticmethod
    def invalidate_cache(pattern: str | None = None):
        """Invalidate configuration cache.

        If pattern is None, uses a global version counter approach.
        For simplicity, we clear the entire cache.
        """
        cache.clear()
        logger.info("Configuration cache invalidated.")

    @staticmethod
    def invalidate_choice_list(code: str):
        cache_key_active = f"config:choice_list:{code}:active=True"
        cache_key_all = f"config:choice_list:{code}:active=False"
        cache.delete(cache_key_active)
        cache.delete(cache_key_all)
        logger.info("Choice list cache invalidated for '%s'", code)

    @staticmethod
    def invalidate_parameter(code: str):
        cache_key = f"config:parameter:{code}"
        cache.delete(cache_key)
        logger.info("Parameter cache invalidated for '%s'", code)


# Module-level convenience
config = ConfigurationService
