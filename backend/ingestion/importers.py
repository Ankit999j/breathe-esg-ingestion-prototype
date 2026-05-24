import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.db import transaction

from .models import ActivityRecord, AuditEvent, ImportBatch, RawRecord

KNOWN_PLANTS = {
    "DE01": "Berlin Plant",
    "IN-PNQ": "Pune Plant",
    "US-TX1": "Austin Plant",
}

AIRPORT_DISTANCE_KM = {
    ("BLR", "DEL"): 1740,
    ("DEL", "FRA"): 6120,
    ("SFO", "JFK"): 4160,
    ("LHR", "JFK"): 5540,
}

UNIT_TO_BASE = {
    "l": ("liter", Decimal("1")),
    "liter": ("liter", Decimal("1")),
    "litre": ("liter", Decimal("1")),
    "gal": ("liter", Decimal("3.78541")),
    "gallon": ("liter", Decimal("3.78541")),
    "kg": ("kg", Decimal("1")),
    "kwh": ("kWh", Decimal("1")),
    "mwh": ("kWh", Decimal("1000")),
    "km": ("km", Decimal("1")),
    "mile": ("km", Decimal("1.60934")),
    "mi": ("km", Decimal("1.60934")),
    "night": ("room-night", Decimal("1")),
    "room-night": ("room-night", Decimal("1")),
}

EMISSION_FACTORS = {
    "diesel_liter": Decimal("2.680"),
    "petrol_liter": Decimal("2.310"),
    "natural_gas_kwh": Decimal("0.184"),
    "electricity_location_kwh": Decimal("0.420"),
    "flight_passenger_km": Decimal("0.158"),
    "hotel_room_night": Decimal("18.500"),
    "ground_transport_km": Decimal("0.180"),
    "procurement_spend_usd": Decimal("0.450"),
}


def ingest_csv(*, tenant, source_system, uploaded_by, file_obj, filename):
    if hasattr(file_obj, "read"):
        data = file_obj.read()
        text = data.decode("utf-8-sig") if isinstance(data, bytes) else str(data)
    else:
        text = str(file_obj)
    reader = csv.DictReader(StringIO(text))
    rows = list(reader)
    batch = ImportBatch.objects.create(
        tenant=tenant,
        source_system=source_system,
        uploaded_by=uploaded_by,
        original_filename=filename,
        total_rows=len(rows),
    )

    importer = {
        "sap": _normalize_sap,
        "utility": _normalize_utility,
        "travel": _normalize_travel,
    }[source_system.source_type]

    failed = 0
    suspicious = 0
    with transaction.atomic():
        for index, row in enumerate(rows, start=2):
            raw = RawRecord.objects.create(batch=batch, row_number=index, payload=row)
            activity = importer(tenant, source_system, batch, raw, row)
            if activity.review_status == ActivityRecord.ReviewStatus.FAILED:
                failed += 1
            if activity.review_status == ActivityRecord.ReviewStatus.SUSPICIOUS:
                suspicious += 1
            AuditEvent.objects.create(
                tenant=tenant,
                activity=activity,
                actor=uploaded_by,
                event_type=AuditEvent.EventType.IMPORTED,
                message=f"Imported from {source_system.name} row {index}",
            )

    batch.failed_rows = failed
    batch.suspicious_rows = suspicious
    batch.status = ImportBatch.Status.PROCESSED
    batch.save(update_fields=["failed_rows", "suspicious_rows", "status"])
    return batch


def _normalize_sap(tenant, source_system, batch, raw, row):
    external_id = _first(row, "Document Number", "Belegnummer", "Material Document")
    plant = _first(row, "Plant", "Werk")
    date = _date(_first(row, "Posting Date", "Buchungsdatum"))
    material = _first(row, "Material", "Materialkurztext", "Short Text").lower()
    qty = _decimal(_first(row, "Quantity", "Menge"))
    unit = _first(row, "Unit", "MEINS", "Einheit")
    vendor = _first(row, "Vendor", "Lieferant")
    amount = _decimal(_first(row, "Amount USD", "Betrag USD"))

    flags = []
    if plant and plant not in KNOWN_PLANTS:
        flags.append("unknown_plant_code")
    if not date:
        flags.append("invalid_or_missing_posting_date")
    normalized_qty, normalized_unit = _normalize_unit(qty, unit)
    if qty is None or not normalized_unit:
        flags.append("missing_or_unknown_unit")

    category = "fuel_combustion" if any(word in material for word in ["diesel", "petrol", "gas"]) else "purchased_goods"
    scope = ActivityRecord.Scope.SCOPE_1 if category == "fuel_combustion" else ActivityRecord.Scope.SCOPE_3
    factor_key = "diesel_liter" if "diesel" in material else "petrol_liter" if "petrol" in material else "procurement_spend_usd"
    basis_qty = normalized_qty if category == "fuel_combustion" else amount
    estimated = _estimate(factor_key, basis_qty)

    if category == "purchased_goods" and amount is None:
        flags.append("missing_procurement_spend")
    if normalized_qty and normalized_qty > Decimal("50000"):
        flags.append("unusually_large_quantity")

    return _activity(
        tenant, source_system, batch, raw, external_id, date, scope, category, plant,
        vendor, material, qty, unit, normalized_qty, normalized_unit, estimated, factor_key, flags
    )


def _normalize_utility(tenant, source_system, batch, raw, row):
    account = _first(row, "Account Number", "Utility Account")
    meter = _first(row, "Meter Number", "Meter")
    start = _date(_first(row, "Billing Start", "Service From"))
    end = _date(_first(row, "Billing End", "Service To"))
    qty = _decimal(_first(row, "Usage", "kWh"))
    unit = _first(row, "Unit", "Usage Unit") or "kWh"
    tariff = _first(row, "Tariff", "Rate Class")
    facility = _first(row, "Facility Code", "Site")
    normalized_qty, normalized_unit = _normalize_unit(qty, unit)

    flags = []
    if not meter:
        flags.append("missing_meter_number")
    if not start or not end or start > end:
        flags.append("invalid_billing_period")
    if normalized_unit != "kWh":
        flags.append("electricity_not_normalized_to_kwh")
    if normalized_qty and normalized_qty > Decimal("250000"):
        flags.append("unusually_large_meter_usage")

    estimated = _estimate("electricity_location_kwh", normalized_qty)
    description = f"{meter} {tariff}".strip()
    return _activity(
        tenant, source_system, batch, raw, account, start, ActivityRecord.Scope.SCOPE_2,
        "purchased_electricity", facility, "", description, qty, unit, normalized_qty,
        normalized_unit, estimated, "electricity_location_kwh", flags, period_start=start, period_end=end
    )


def _normalize_travel(tenant, source_system, batch, raw, row):
    trip_id = _first(row, "Trip ID", "Report ID")
    traveler = _first(row, "Employee", "Traveler")
    category = _first(row, "Category", "Expense Type").lower()
    date = _date(_first(row, "Transaction Date", "Start Date"))
    origin = _first(row, "Origin Airport", "From")
    destination = _first(row, "Destination Airport", "To")
    qty = _decimal(_first(row, "Distance", "Nights", "Amount"))
    unit = _first(row, "Unit")

    flags = []
    normalized_qty = None
    normalized_unit = ""
    factor_key = "ground_transport_km"
    normalized_category = "business_travel_ground"

    if "flight" in category:
        normalized_category = "business_travel_flight"
        factor_key = "flight_passenger_km"
        if not qty and origin and destination:
            qty = Decimal(AIRPORT_DISTANCE_KM.get((origin, destination), AIRPORT_DISTANCE_KM.get((destination, origin), 0)))
            unit = "km"
        if not origin or not destination:
            flags.append("missing_airport_code")
        if not qty:
            flags.append("missing_flight_distance")
    elif "hotel" in category:
        normalized_category = "business_travel_hotel"
        factor_key = "hotel_room_night"
        unit = unit or "room-night"
    else:
        unit = unit or "km"

    normalized_qty, normalized_unit = _normalize_unit(qty, unit)
    if not date:
        flags.append("invalid_or_missing_travel_date")
    if qty is None or not normalized_unit:
        flags.append("missing_or_unknown_unit")

    estimated = _estimate(factor_key, normalized_qty)
    description = " ".join(part for part in [category, origin, destination] if part)
    return _activity(
        tenant, source_system, batch, raw, trip_id, date, ActivityRecord.Scope.SCOPE_3,
        normalized_category, "", traveler, description, qty, unit, normalized_qty,
        normalized_unit, estimated, factor_key, flags
    )


def _activity(tenant, source_system, batch, raw, external_id, date, scope, category, facility, vendor, description,
              qty, unit, normalized_qty, normalized_unit, estimated, factor_key, flags, period_start=None, period_end=None):
    status = ActivityRecord.ReviewStatus.FAILED if any("missing" in flag or "invalid" in flag for flag in flags) else (
        ActivityRecord.ReviewStatus.SUSPICIOUS if flags else ActivityRecord.ReviewStatus.IMPORTED
    )
    return ActivityRecord.objects.create(
        tenant=tenant,
        source_system=source_system,
        import_batch=batch,
        raw_record=raw,
        external_id=external_id,
        activity_date=date,
        period_start=period_start,
        period_end=period_end,
        scope=scope,
        category=category,
        facility_code=facility,
        supplier_or_vendor=vendor,
        description=description[:240],
        original_quantity=qty,
        original_unit=unit,
        normalized_quantity=normalized_qty,
        normalized_unit=normalized_unit,
        estimated_kg_co2e=estimated,
        emission_factor_key=factor_key,
        review_status=status,
        validation_flags=flags,
    )


def _first(row, *names):
    lowered = {key.lower().strip(): value for key, value in row.items() if key}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return None


def _normalize_unit(qty, unit):
    if qty is None or not unit:
        return None, ""
    key = unit.lower().strip()
    if key not in UNIT_TO_BASE:
        return None, ""
    normalized_unit, multiplier = UNIT_TO_BASE[key]
    return qty * multiplier, normalized_unit


def _estimate(factor_key, qty):
    if qty is None:
        return None
    return qty * EMISSION_FACTORS[factor_key]
