from django.utils.deprecation import MiddlewareMixin

from apps.governance.services.audit_service import AuditContext


class AuditContextMiddleware(MiddlewareMixin):
    def process_request(self, request):
        AuditContext.set_request(request)

    def process_response(self, request, response):
        AuditContext.clear()
        return response

    def process_exception(self, request, exception):
        AuditContext.clear()
