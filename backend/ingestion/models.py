from django.conf import settings
from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=40, default="analyst")

    class Meta:
        unique_together = [("user", "tenant")]


class SourceSystem(models.Model):
    class SourceType(models.TextChoices):
        SAP = "sap", "SAP"
        UTILITY = "utility", "Utility"
        TRAVEL = "travel", "Travel"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "name")]

    def __str__(self):
        return f"{self.tenant}: {self.name}"


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source_system = models.ForeignKey(SourceSystem, on_delete=models.PROTECT)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    original_filename = models.CharField(max_length=240)
    imported_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    total_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    suspicious_rows = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-imported_at"]


class RawRecord(models.Model):
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="raw_records")
    row_number = models.PositiveIntegerField()
    payload = models.JSONField()
    parse_errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("batch", "row_number")]


class ActivityRecord(models.Model):
    class Scope(models.TextChoices):
        SCOPE_1 = "scope_1", "Scope 1"
        SCOPE_2 = "scope_2", "Scope 2"
        SCOPE_3 = "scope_3", "Scope 3"

    class ReviewStatus(models.TextChoices):
        IMPORTED = "imported", "Imported"
        FAILED = "failed", "Failed"
        SUSPICIOUS = "suspicious", "Suspicious"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source_system = models.ForeignKey(SourceSystem, on_delete=models.PROTECT)
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT)
    raw_record = models.OneToOneField(RawRecord, on_delete=models.PROTECT, null=True, blank=True)
    external_id = models.CharField(max_length=160, blank=True)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    category = models.CharField(max_length=80)
    facility_code = models.CharField(max_length=80, blank=True)
    supplier_or_vendor = models.CharField(max_length=160, blank=True)
    description = models.CharField(max_length=240, blank=True)
    original_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    original_unit = models.CharField(max_length=40, blank=True)
    normalized_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    normalized_unit = models.CharField(max_length=40, blank=True)
    estimated_kg_co2e = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    emission_factor_key = models.CharField(max_length=120, blank=True)
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.IMPORTED)
    validation_flags = models.JSONField(default=list, blank=True)
    edited = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_activities")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "review_status"]),
            models.Index(fields=["tenant", "scope"]),
            models.Index(fields=["source_system", "external_id"]),
        ]


class EmissionFactor(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    key = models.CharField(max_length=120)
    label = models.CharField(max_length=160)
    unit = models.CharField(max_length=40)
    kg_co2e_per_unit = models.DecimalField(max_digits=12, decimal_places=6)
    source_note = models.CharField(max_length=240, blank=True)

    class Meta:
        unique_together = [("tenant", "key")]


class AuditEvent(models.Model):
    class EventType(models.TextChoices):
        IMPORTED = "imported", "Imported"
        EDITED = "edited", "Edited"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    activity = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    message = models.CharField(max_length=240)
    diff = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]
