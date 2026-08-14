from __future__ import annotations

from apps.users.models import ReportCategory, User


class ReportCategoryCode:
    ORDINARY_LIFE = 'ordinary_life'
    GROUP_CREDIT = 'group_credit'
    GROUP_LIFE = 'group_life'
    CLAIMS = 'claims'
    COMMISSION = 'commission'
    FINANCE = 'finance'
    UNDERWRITING = 'underwriting'
    REINSURANCE = 'reinsurance'
    AUDIT = 'audit'
    IFRS17 = 'ifrs17'


REPORT_CATEGORY_CODES = (
    ReportCategoryCode.ORDINARY_LIFE,
    ReportCategoryCode.GROUP_CREDIT,
    ReportCategoryCode.GROUP_LIFE,
    ReportCategoryCode.CLAIMS,
    ReportCategoryCode.COMMISSION,
    ReportCategoryCode.FINANCE,
    ReportCategoryCode.UNDERWRITING,
    ReportCategoryCode.REINSURANCE,
    ReportCategoryCode.AUDIT,
    ReportCategoryCode.IFRS17,
)


class ReportVisibilityChecker:
    """Integration point for future report listing and execution services."""

    @staticmethod
    def visible_categories(user: User):
        return user.visible_report_categories()

    @staticmethod
    def can_view(user: User, category_code: str) -> bool:
        return user.can_view_report_category(category_code)

    @staticmethod
    def require(user: User, category_code: str) -> ReportCategory:
        category = ReportCategory.objects.filter(
            code__iexact=(category_code or '').strip(),
            is_active=True,
        ).first()
        if category is None or not ReportVisibilityChecker.can_view(user, category.code):
            raise PermissionError(f'Report category is not visible: {category_code}')
        return category
