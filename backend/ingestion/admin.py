from django.contrib import admin

from .models import ActivityRecord, AuditEvent, EmissionFactor, ImportBatch, RawRecord, SourceSystem, Tenant, TenantMembership

admin.site.register(Tenant)
admin.site.register(TenantMembership)
admin.site.register(SourceSystem)
admin.site.register(ImportBatch)
admin.site.register(RawRecord)
admin.site.register(ActivityRecord)
admin.site.register(EmissionFactor)
admin.site.register(AuditEvent)
