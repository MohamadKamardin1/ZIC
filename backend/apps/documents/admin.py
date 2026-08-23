from django.contrib import admin

from .models import DocumentInstance, DocumentTemplate


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "document_type",
        "version",
        "is_active",
        "approved_by",
        "approved_at",
    ]
    list_filter = ["document_type", "is_active", "version"]
    search_fields = ["code", "name", "document_type", "layout_template_path"]
    ordering = ["document_type", "code", "-version"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DocumentInstance)
class DocumentInstanceAdmin(admin.ModelAdmin):
    list_display = [
        "document_type",
        "source_type",
        "source_object_id",
        "template",
        "template_version",
        "page_count",
        "generated_by",
        "generated_at",
        "status",
    ]
    list_filter = ["document_type", "status", "template", "generated_at"]
    search_fields = [
        "document_type",
        "source_app_label",
        "source_model",
        "source_object_id",
        "correlation_id",
        "checksum",
    ]
    ordering = ["-generated_at"]
    readonly_fields = [field.name for field in DocumentInstance._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
