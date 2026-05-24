from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .importers import ingest_csv
from .models import ActivityRecord, AuditEvent, ImportBatch, SourceSystem, TenantMembership
from .serializers import ActivityRecordSerializer, ActivityUpdateSerializer, ImportBatchSerializer, SourceSystemSerializer


def current_tenant(user):
    membership = TenantMembership.objects.select_related("tenant").filter(user=user).first()
    return membership.tenant if membership else None


class MeView(APIView):
    def get(self, request):
        tenant = current_tenant(request.user)
        return Response({
            "email": request.user.email,
            "username": request.user.username,
            "tenant": {"id": tenant.id, "name": tenant.name, "slug": tenant.slug} if tenant else None,
        })


class DashboardView(APIView):
    def get(self, request):
        tenant = current_tenant(request.user)
        qs = ActivityRecord.objects.filter(tenant=tenant)
        return Response({
            "by_status": list(qs.values("review_status").annotate(count=Count("id")).order_by("review_status")),
            "by_scope": list(qs.values("scope").annotate(count=Count("id")).order_by("scope")),
            "by_source": list(qs.values("source_system__source_type").annotate(count=Count("id")).order_by("source_system__source_type")),
            "latest_batches": ImportBatchSerializer(ImportBatch.objects.filter(tenant=tenant)[:5], many=True).data,
        })


class SourceSystemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SourceSystemSerializer

    def get_queryset(self):
        return SourceSystem.objects.filter(tenant=current_tenant(self.request.user))


class ImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ImportBatchSerializer

    def get_queryset(self):
        return ImportBatch.objects.filter(tenant=current_tenant(self.request.user)).select_related("source_system")

    @action(detail=False, methods=["post"])
    def upload(self, request):
        tenant = current_tenant(request.user)
        source_id = request.data.get("source_system")
        upload = request.FILES.get("file")
        if not source_id or not upload:
            return Response({"detail": "source_system and file are required."}, status=status.HTTP_400_BAD_REQUEST)
        source = SourceSystem.objects.get(id=source_id, tenant=tenant)
        batch = ingest_csv(
            tenant=tenant,
            source_system=source,
            uploaded_by=request.user,
            file_obj=upload.file,
            filename=upload.name,
        )
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class ActivityRecordViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityRecordSerializer

    def get_queryset(self):
        qs = ActivityRecord.objects.filter(tenant=current_tenant(self.request.user)).select_related("source_system").prefetch_related("audit_events")
        status_filter = self.request.query_params.get("status")
        source_type = self.request.query_params.get("source_type")
        if status_filter:
            qs = qs.filter(review_status=status_filter)
        if source_type:
            qs = qs.filter(source_system__source_type=source_type)
        return qs

    def get_serializer_class(self):
        if self.action in ["partial_update", "update"]:
            return ActivityUpdateSerializer
        return ActivityRecordSerializer

    def perform_update(self, serializer):
        activity = self.get_object()
        if activity.review_status == ActivityRecord.ReviewStatus.LOCKED:
            raise ValidationError("Locked rows cannot be edited.")
        before = {field: str(getattr(activity, field)) for field in serializer.validated_data.keys()}
        updated = serializer.save(edited=True)
        after = {field: str(getattr(updated, field)) for field in serializer.validated_data.keys()}
        AuditEvent.objects.create(
            tenant=updated.tenant,
            activity=updated,
            actor=self.request.user,
            event_type=AuditEvent.EventType.EDITED,
            message="Analyst edited normalized activity fields.",
            diff={"before": before, "after": after},
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        activity = self.get_object()
        activity.review_status = ActivityRecord.ReviewStatus.APPROVED
        activity.approved_by = request.user
        activity.approved_at = timezone.now()
        activity.save(update_fields=["review_status", "approved_by", "approved_at", "updated_at"])
        self._audit(activity, AuditEvent.EventType.APPROVED, "Analyst approved row.")
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        activity = self.get_object()
        activity.review_status = ActivityRecord.ReviewStatus.REJECTED
        activity.save(update_fields=["review_status", "updated_at"])
        self._audit(activity, AuditEvent.EventType.REJECTED, request.data.get("message", "Analyst rejected row."))
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        activity = self.get_object()
        if activity.review_status != ActivityRecord.ReviewStatus.APPROVED:
            return Response({"detail": "Only approved rows can be locked."}, status=status.HTTP_400_BAD_REQUEST)
        activity.review_status = ActivityRecord.ReviewStatus.LOCKED
        activity.locked_at = timezone.now()
        activity.save(update_fields=["review_status", "locked_at", "updated_at"])
        self._audit(activity, AuditEvent.EventType.LOCKED, "Row locked for audit.")
        return Response(ActivityRecordSerializer(activity).data)

    def _audit(self, activity, event_type, message):
        AuditEvent.objects.create(
            tenant=activity.tenant,
            activity=activity,
            actor=self.request.user,
            event_type=event_type,
            message=message,
        )
