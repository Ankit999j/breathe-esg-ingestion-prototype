from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityRecordViewSet, DashboardView, ImportBatchViewSet, MeView, SourceSystemViewSet

router = DefaultRouter()
router.register("sources", SourceSystemViewSet, basename="source")
router.register("batches", ImportBatchViewSet, basename="batch")
router.register("activities", ActivityRecordViewSet, basename="activity")

urlpatterns = [
    path("me/", MeView.as_view()),
    path("dashboard/", DashboardView.as_view()),
    path("auth/", include("rest_framework.urls")),
    path("", include(router.urls)),
]
