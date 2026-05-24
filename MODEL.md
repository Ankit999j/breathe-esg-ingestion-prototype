# Data Model

This prototype uses a small ingestion-first model. The key choice is to keep raw source rows separate from normalized activity records, because auditors and analysts care about both: what the client sent and what our system inferred from it.

## Core Entities

`Tenant` represents a client company. Every source system, import batch, activity row, and audit event belongs to one tenant. `TenantMembership` links a Django user to a tenant. The prototype uses one tenant per analyst login, but the model is ready for multiple analysts per client.

`SourceSystem` identifies where data came from. It stores both the human name, such as "SAP S/4HANA CSV Export", and the source type: `sap`, `utility`, or `travel`.

`ImportBatch` represents one ingestion event. It records the source system, original filename, uploader, imported timestamp, total rows, failed rows, and suspicious rows. This is the source-of-truth envelope for a file upload.

`RawRecord` stores the original parsed row as JSON plus row number and parse errors. This protects traceability: if a normalized record looks wrong, the reviewer can still inspect the row that produced it.

`ActivityRecord` is the normalized emissions activity row. It stores:

- Scope category: Scope 1, Scope 2, or Scope 3.
- Domain category such as `fuel_combustion`, `purchased_electricity`, or `business_travel_flight`.
- Original quantity/unit and normalized quantity/unit.
- Estimated kg CO2e and the factor key used.
- Source references: source system, import batch, raw record, external source ID.
- Review lifecycle: imported, failed, suspicious, approved, rejected, locked.
- Edit and approval metadata.

`EmissionFactor` is intentionally simple. In this prototype the importer uses a small factor map, but the database model exists so a production version can manage factors by geography, time period, activity category, and factor source.

`AuditEvent` records import, edit, approval, rejection, and lock events. The event stores actor, timestamp, message, and optional diff. Locked rows cannot be edited through the API.

## Scope Mapping

- SAP fuel rows become Scope 1 because the company combusts the fuel directly.
- Utility electricity rows become Scope 2 because they represent purchased electricity.
- SAP procurement and corporate travel rows become Scope 3 because they are value-chain activities.

## Unit Normalization

Each importer stores original quantity/unit and normalized quantity/unit. Examples:

- SAP gallons are converted to liters.
- Utility MWh is converted to kWh.
- Ground transport miles are converted to kilometers.
- Hotel stays normalize to room-nights.

Rows with missing or unsupported units are marked failed because the emissions calculation would be hard to defend.

## Source Of Truth

The source-of-truth chain is:

`SourceSystem -> ImportBatch -> RawRecord -> ActivityRecord`

This makes it possible to answer:

- Which client/source produced this row?
- Which upload included it?
- What was the original row payload?
- Did an analyst edit the normalized result?
- Who approved or locked it?

## Review Lifecycle

Rows enter as:

- `imported` when parsing succeeded and no flags were found.
- `suspicious` when parsing succeeded but a human should review the row.
- `failed` when required fields are missing or invalid.

Analysts can approve or reject rows. Approved rows can be locked for audit. Locking is intentionally separate from approval so the analyst can still correct an approved row before final audit close.

## Why This Is Small But Extensible

The model avoids separate tables for SAP line items, utility bills, and travel bookings. That would look more precise but would slow down the assignment and create extra mapping code. Instead, source-specific details remain in `RawRecord.payload`, while defensible common fields live in `ActivityRecord`.

The extensibility point is the importer layer: new source shapes can produce the same normalized activity model without changing the analyst workflow.
