# Sources Researched

## SAP Fuel And Procurement

Researched format: SAP S/4HANA material/inventory data exposed through OData and common export/report workflows.

Useful references:

- SAP Help Portal describes OData services for inventory, including Material Document APIs that retrieve and create material documents: https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/eb2a39dd0c124fed8252f684002d55e1/013f0f9ef9dc48daa3c4709ab8860333.html
- SAP OData metadata supports unit annotations, which is relevant because quantities and units travel together in SAP exports: https://sap.github.io/odata-vocabularies/docs/v2-annotations.html

What I learned:

- SAP source rows usually need master data context. Plant, vendor, material, and unit codes are meaningful only with lookup tables.
- Material-document style data has posting dates, plant codes, material descriptions, quantities, and base units.
- A prototype should not hide the complexity of SAP integration behind a fake API.

Sample data shape:

The SAP sample is a flat CSV with document number, posting date, plant, material, quantity, unit, vendor, and amount. It includes mixed date formats, gallons vs liters, an unknown plant code, a missing quantity, and a very large fuel quantity.

What would break in real deployment:

- Unknown plant/material codes would require master-data sync.
- Currency and unit conversion would need governance.
- Procurement emissions would need a real category taxonomy and factor source.
- A live SAP integration would require authentication, authorization, retries, and data extraction scheduling.

## Utility Electricity

Researched format: utility usage and billing data, including Green Button / ESPI concepts and common portal exports.

Useful references:

- Green Button explains utility usage data access for interval and billing data: https://archive.greenbuttondata.org/faq/
- Green Button Connect My Data describes authorized access to electricity, gas, or water usage data at intervals such as monthly, daily, hourly, or shorter: https://www.greenbuttondata.org/cmd.html

What I learned:

- Utilities can provide usage as interval data or billing-period summaries.
- Meter number, billing period, usage unit, and tariffs matter for review.
- Billing periods often do not align with calendar months, which affects reporting allocation.

Sample data shape:

The utility sample is a portal-style CSV with account number, meter number, facility code, billing start/end, usage, unit, tariff, demand kW, and amount. It includes kWh and MWh, a missing meter, a reversed billing period, and an unusually large usage row.

What would break in real deployment:

- Overlapping meter periods need richer duplicate/overlap detection.
- Location-based factors depend on region and period.
- Market-based Scope 2 needs contracts, RECs, tariffs, or supplier-specific factors.
- Some clients will only have PDFs or Green Button XML rather than CSV.

## Corporate Travel

Researched format: SAP Concur report entry structures and common travel/expense exports.

Useful references:

- SAP Concur report entry data describes transaction/report-entry fields and expense-entry structures: https://help.sap.com/docs/CONCUR_EXPENSE/bb83754b1c5541808d50c09901e11475/c89376c016964053927f3f5474311d12.html

What I learned:

- Travel platforms often expose report IDs, transaction dates, expense types, travelers, and custom fields.
- Emissions category depends on the expense type: flight, hotel, rail, taxi, rental car, etc.
- Flight rows may have airport codes but no explicit distance.

Sample data shape:

The travel sample is a CSV with trip ID, transaction date, employee, category, origin/destination airport, distance, unit, and amount. It includes flights with inferred distances, hotels as room-nights, ground transport in miles, and a flight missing its destination airport.

What would break in real deployment:

- Airport distances need a complete airport database and routing logic.
- Cabin class, haul length, radiative forcing, and stopovers affect flight emissions.
- Hotel factors vary by country and sometimes hotel brand.
- Expense exports may contain spend-only data that cannot support activity-based emissions without additional assumptions.
