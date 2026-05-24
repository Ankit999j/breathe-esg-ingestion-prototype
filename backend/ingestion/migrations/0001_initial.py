# Generated for the Breathe ESG intern assignment prototype.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="EmissionFactor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=120)),
                ("label", models.CharField(max_length=160)),
                ("unit", models.CharField(max_length=40)),
                ("kg_co2e_per_unit", models.DecimalField(decimal_places=6, max_digits=12)),
                ("source_note", models.CharField(blank=True, max_length=240)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="ingestion.tenant")),
            ],
            options={"unique_together": {("tenant", "key")}},
        ),
        migrations.CreateModel(
            name="SourceSystem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("source_type", models.CharField(choices=[("sap", "SAP"), ("utility", "Utility"), ("travel", "Travel")], max_length=20)),
                ("description", models.TextField(blank=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="ingestion.tenant")),
            ],
            options={"unique_together": {("tenant", "name")}},
        ),
        migrations.CreateModel(
            name="TenantMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(default="analyst", max_length=40)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="ingestion.tenant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("user", "tenant")}},
        ),
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_filename", models.CharField(max_length=240)),
                ("imported_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("status", models.CharField(choices=[("received", "Received"), ("processed", "Processed"), ("failed", "Failed")], default="received", max_length=20)),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("failed_rows", models.PositiveIntegerField(default=0)),
                ("suspicious_rows", models.PositiveIntegerField(default=0)),
                ("source_system", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ingestion.sourcesystem")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="ingestion.tenant")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-imported_at"]},
        ),
        migrations.CreateModel(
            name="RawRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row_number", models.PositiveIntegerField()),
                ("payload", models.JSONField()),
                ("parse_errors", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="ingestion.importbatch")),
            ],
            options={"unique_together": {("batch", "row_number")}},
        ),
        migrations.CreateModel(
            name="ActivityRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(blank=True, max_length=160)),
                ("activity_date", models.DateField(blank=True, null=True)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("scope", models.CharField(choices=[("scope_1", "Scope 1"), ("scope_2", "Scope 2"), ("scope_3", "Scope 3")], max_length=20)),
                ("category", models.CharField(max_length=80)),
                ("facility_code", models.CharField(blank=True, max_length=80)),
                ("supplier_or_vendor", models.CharField(blank=True, max_length=160)),
                ("description", models.CharField(blank=True, max_length=240)),
                ("original_quantity", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ("original_unit", models.CharField(blank=True, max_length=40)),
                ("normalized_quantity", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ("normalized_unit", models.CharField(blank=True, max_length=40)),
                ("estimated_kg_co2e", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ("emission_factor_key", models.CharField(blank=True, max_length=120)),
                ("review_status", models.CharField(choices=[("imported", "Imported"), ("failed", "Failed"), ("suspicious", "Suspicious"), ("approved", "Approved"), ("rejected", "Rejected"), ("locked", "Locked")], default="imported", max_length=20)),
                ("validation_flags", models.JSONField(blank=True, default=list)),
                ("edited", models.BooleanField(default=False)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_activities", to=settings.AUTH_USER_MODEL)),
                ("import_batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ingestion.importbatch")),
                ("raw_record", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="ingestion.rawrecord")),
                ("source_system", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ingestion.sourcesystem")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="ingestion.tenant")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant", "review_status"], name="ingestion_a_tenant__4853b6_idx"),
                    models.Index(fields=["tenant", "scope"], name="ingestion_a_tenant__b92c75_idx"),
                    models.Index(fields=["source_system", "external_id"], name="ingestion_a_source__a55e50_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("imported", "Imported"), ("edited", "Edited"), ("approved", "Approved"), ("rejected", "Rejected"), ("locked", "Locked")], max_length=20)),
                ("message", models.CharField(max_length=240)),
                ("diff", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("activity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="ingestion.activityrecord")),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="ingestion.tenant")),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
