from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ingestion.importers import ingest_csv
from ingestion.models import SourceSystem, Tenant, TenantMembership


class Command(BaseCommand):
    help = "Create demo tenant, analyst, sources, and import sample CSV data."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(slug="acme", defaults={"name": "Acme Manufacturing"})
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="analyst@acme.example",
            defaults={"email": "analyst@acme.example"},
        )
        if created:
            user.set_password("demo12345")
            user.save()
        TenantMembership.objects.get_or_create(user=user, tenant=tenant, defaults={"role": "analyst"})

        sources = {
            "sap": SourceSystem.objects.get_or_create(
                tenant=tenant,
                name="SAP S/4HANA CSV Export",
                source_type=SourceSystem.SourceType.SAP,
                defaults={"description": "Monthly fuel and procurement export from SAP, including German header variants."},
            )[0],
            "utility": SourceSystem.objects.get_or_create(
                tenant=tenant,
                name="Utility Portal CSV",
                source_type=SourceSystem.SourceType.UTILITY,
                defaults={"description": "Facilities team electricity usage export from utility portal."},
            )[0],
            "travel": SourceSystem.objects.get_or_create(
                tenant=tenant,
                name="Corporate Travel CSV",
                source_type=SourceSystem.SourceType.TRAVEL,
                defaults={"description": "Concur/Navan-like business travel report export."},
            )[0],
        }

        sample_dir = Path(__file__).resolve().parents[3] / "samples"
        for key, source in sources.items():
            path = sample_dir / f"{key}_sample.csv"
            if path.exists():
                ingest_csv(
                    tenant=tenant,
                    source_system=source,
                    uploaded_by=user,
                    file_obj=path.read_text(encoding="utf-8"),
                    filename=path.name,
                )

        self.stdout.write(self.style.SUCCESS("Seeded demo data. Login: analyst@acme.example / demo12345"))
