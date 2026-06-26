import uuid

from django.db import models


class ParameterGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_parameter_group"
        verbose_name = "Parameter Group"
        verbose_name_plural = "Parameter Groups"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{'--' * self._level()}{self.name}"

    def _level(self):
        level = 0
        p = self.parent
        while p:
            level += 1
            p = p.parent
        return level


class SystemParameter(models.Model):
    VALUE_TYPE_CHOICES = [
        ("STRING", "String"),
        ("TEXT", "Text"),
        ("INTEGER", "Integer"),
        ("FLOAT", "Float"),
        ("BOOLEAN", "Boolean"),
        ("JSON", "JSON"),
        ("FILE", "File"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        ParameterGroup,
        on_delete=models.CASCADE,
        related_name="parameters",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    value_type = models.CharField(
        max_length=10, choices=VALUE_TYPE_CHOICES, default="STRING"
    )
    string_value = models.TextField(blank=True, null=True)
    integer_value = models.IntegerField(null=True, blank=True)
    float_value = models.FloatField(null=True, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    json_value = models.JSONField(null=True, blank=True)
    file_value = models.FileField(
        upload_to="system_parameters/%Y/%m/", null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_encrypted = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_parameter"
        verbose_name = "System Parameter"
        verbose_name_plural = "System Parameters"
        ordering = ["group__sort_order", "sort_order", "name"]

    def __str__(self):
        return f"{self.group.name} / {self.name}"

    @property
    def value(self):
        if self.value_type == "STRING":
            return self.string_value
        if self.value_type == "TEXT":
            return self.string_value
        if self.value_type == "INTEGER":
            return self.integer_value
        if self.value_type == "FLOAT":
            return self.float_value
        if self.value_type == "BOOLEAN":
            return self.boolean_value
        if self.value_type == "JSON":
            return self.json_value
        return None

    @value.setter
    def value(self, val):
        if self.value_type == "STRING":
            self.string_value = str(val) if val is not None else None
        elif self.value_type == "TEXT":
            self.string_value = str(val) if val is not None else None
        elif self.value_type == "INTEGER":
            self.integer_value = int(val) if val is not None else None
        elif self.value_type == "FLOAT":
            self.float_value = float(val) if val is not None else None
        elif self.value_type == "BOOLEAN":
            if isinstance(val, str):
                self.boolean_value = val.lower() in ("true", "1", "yes")
            else:
                self.boolean_value = bool(val) if val is not None else None
        elif self.value_type == "JSON":
            self.json_value = val


class ChoiceList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        ParameterGroup,
        on_delete=models.CASCADE,
        related_name="choice_lists",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_choice_list"
        verbose_name = "Choice List"
        verbose_name_plural = "Choice Lists"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ChoiceOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    choice_list = models.ForeignKey(
        ChoiceList,
        on_delete=models.CASCADE,
        related_name="options",
    )
    code = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_choice_option"
        verbose_name = "Choice Option"
        verbose_name_plural = "Choice Options"
        ordering = ["choice_list", "sort_order", "label"]
        unique_together = [["choice_list", "code"]]

    def __str__(self):
        return f"{self.choice_list.name} / {self.label}"
