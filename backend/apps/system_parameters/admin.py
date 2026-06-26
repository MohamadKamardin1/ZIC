from django.contrib import admin

from .models import ParameterGroup, SystemParameter, ChoiceList, ChoiceOption


class ChoiceOptionInline(admin.TabularInline):
    model = ChoiceOption
    extra = 1
    ordering = ["sort_order"]


@admin.register(ParameterGroup)
class ParameterGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "parent", "sort_order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    ordering = ["sort_order", "name"]


@admin.register(SystemParameter)
class SystemParameterAdmin(admin.ModelAdmin):
    list_display = [
        "name", "code", "group", "value_type", "is_active", "sort_order",
    ]
    list_filter = ["group", "value_type", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering = ["group__sort_order", "sort_order", "name"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "group", "name", "code", "description",
                    "value_type", "is_active", "sort_order",
                ],
            },
        ),
        ("Value", {"fields": [
            "string_value", "integer_value", "float_value",
            "boolean_value", "json_value", "file_value",
        ]}),
        ("Security", {"fields": ["is_encrypted"]}),
    ]


@admin.register(ChoiceList)
class ChoiceListAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    inlines = [ChoiceOptionInline]


@admin.register(ChoiceOption)
class ChoiceOptionAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "choice_list", "is_default", "is_active"]
    list_filter = ["choice_list", "is_active", "is_default"]
    search_fields = ["code", "label"]
