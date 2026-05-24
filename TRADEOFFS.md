# Tradeoffs

## 1. No Real SAP API Integration

I used SAP-style CSV exports instead of OData, IDoc, or BAPI integration. A real SAP connection would require client-specific credentials, authorization scopes, network access, and detailed module decisions. For this assignment, the better use of time is modeling source-of-truth tracking and normalizing messy rows.

## 2. No PDF Bill OCR

I did not parse utility PDF bills. OCR would add substantial noise and would likely dominate the prototype. A utility portal CSV still exercises the important sustainability-data problems: meters, units, billing periods, tariffs, and non-calendar date ranges.

## 3. No Production Emission Factor Engine

The prototype uses a small set of factor keys and static factors. A production system needs versioned factors by geography, time period, factor source, market/location method, and audit approval. I included the `EmissionFactor` model as a clear extension point, but kept the implementation focused on ingestion and review.

## Other Conscious Omissions

- No complex role-based permissions: one analyst role is enough to demonstrate tenant separation and review workflow.
- No automated auditor export: locked rows are modeled, but final package generation is outside the prototype.
- No duplicate detection across every source: only obvious validation flags are implemented.
