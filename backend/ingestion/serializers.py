from rest_framework import serializers

from .models import ActivityRecord, AuditEvent, ImportBatch, SourceSystem


class SourceSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceSystem
        fields = ["id", "name", "source_type", "description"]


class ImportBatchSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source_system.name", read_only=True)
    source_type = serializers.CharField(source="source_system.source_type", read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            "id", "source_system", "source_name", "source_type", "original_filename",
            "imported_at", "status", "total_rows", "failed_rows", "suspicious_rows",
        ]


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "actor_email", "event_type", "message", "diff", "created_at"]


class ActivityRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source_system.name", read_only=True)
    source_type = serializers.CharField(source="source_system.source_type", read_only=True)
    audit_events = AuditEventSerializer(many=True, read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            "id", "source_name", "source_type", "external_id", "activity_date",
            "period_start", "period_end", "scope", "category", "facility_code",
            "supplier_or_vendor", "description", "original_quantity", "original_unit",
            "normalized_quantity", "normalized_unit", "estimated_kg_co2e",
            "emission_factor_key", "review_status", "validation_flags", "edited",
            "locked_at", "approved_at", "created_at", "updated_at", "audit_events",
        ]
        read_only_fields = [
            "source_name", "source_type", "review_status", "edited", "locked_at",
            "approved_at", "created_at", "updated_at", "audit_events",
        ]


class ActivityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityRecord
        fields = [
            "activity_date", "period_start", "period_end", "category", "facility_code",
            "supplier_or_vendor", "description", "normalized_quantity",
            "normalized_unit", "estimated_kg_co2e", "emission_factor_key",
        ]
