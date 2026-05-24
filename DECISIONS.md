# Decisions

## Architecture

I chose Django REST Framework for the backend and React for the analyst interface. Django owns the domain model, import logic, review actions, and audit trail. React is intentionally thin: it displays dashboard counts, upload controls, a normalized row table, detail view, and review actions.

## SAP Source

Decision: handle SAP fuel/procurement as a CSV export rather than a live SAP API.

Why: SAP S/4HANA exposes OData services for inventory/material documents, but a four-day prototype should not pretend to integrate with a client's SAP tenant. Analysts often receive scheduled exports from SAP/Fiori, BW, or a shared folder. CSV is a realistic ingestion boundary and lets the prototype focus on normalization and review.

Subset handled:

- Material document style rows.
- Posting date.
- Plant code.
- Material/description.
- Quantity and unit.
- Vendor.
- Spend amount for procurement.
- German header variants for common fields.

Ignored:

- IDoc parsing.
- BAPI/OData authentication.
- Purchase order lifecycle.
- Tax/currency treatment beyond a simple USD amount.
- SAP master data sync beyond a small plant lookup.

PM questions:

- Which SAP module/export is the actual source: MM material documents, FI invoices, Ariba, or BW report?
- Can we get plant and material master lookups?
- Should procurement emissions be spend-based, supplier-specific, or product-specific?

## Utility Source

Decision: handle electricity as utility portal CSV exports.

Why: Green Button exists for standardized interval and billing data, but many facilities teams still download CSVs from utility portals. CSV lets the prototype represent billing periods, meters, kWh/MWh units, tariffs, and demand fields without building OAuth or XML parsing.

Subset handled:

- Account number.
- Meter number.
- Facility code.
- Billing start/end.
- Usage and unit.
- Tariff/rate class.
- Demand kW as raw context.

Ignored:

- PDF bill OCR.
- Green Button XML.
- Interval data aggregation.
- Market-based Scope 2 instruments.
- Utility account credential management.

PM questions:

- Do facilities teams provide billing CSVs, interval data, or PDFs?
- Which geographies need grid factors?
- Do we need both location-based and market-based Scope 2?

## Travel Source

Decision: handle travel as a Concur/Navan-like CSV report export.

Why: SAP Concur publishes report-entry structures, and many travel/expense systems expose report IDs, expense types, transaction dates, traveler fields, and custom fields. For a prototype, CSV export avoids API credential setup while preserving the shape of expense/travel data.

Subset handled:

- Trip/report ID.
- Transaction date.
- Traveler.
- Category: flight, hotel, ground transport.
- Airport codes for flights.
- Distance or inferred distance for known airport pairs.
- Nights for hotels.

Ignored:

- Live Concur/Navan APIs.
- Segment-level itinerary reconstruction.
- Cabin class and radiative forcing multipliers.
- Hotel country-specific factors.
- Employee PII minimization beyond a simple traveler string.

PM questions:

- Is the source travel booking data, expense report data, or card transaction data?
- Are airport pairs available, or only spend/category?
- Do auditors require itinerary-level detail or aggregated travel activity?

## Emissions Calculation

Decision: include simple factor keys and estimated kg CO2e, but do not build a production factor engine.

Why: The assignment is about ingestion, normalization, and review judgment. A minimal estimate helps validate normalization without pretending to solve factor governance.
