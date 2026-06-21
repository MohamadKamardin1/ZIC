from apps.core.exceptions import ZICAPIException


class ApplicationTransitionError(ZICAPIException):
    def __init__(self, message="Invalid status transition", details=None):
        super().__init__(
            message=message,
            code="APPLICATION_TRANSITION_ERROR",
            status_code=400,
            details=details,
        )


class ApplicationValidationError(ZICAPIException):
    def __init__(self, message="Application validation failed", details=None):
        super().__init__(
            message=message,
            code="APPLICATION_VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class PartnerConversionError(ZICAPIException):
    def __init__(self, message="Partner conversion failed", details=None):
        super().__init__(
            message=message,
            code="PARTNER_CONVERSION_ERROR",
            status_code=400,
            details=details,
        )
