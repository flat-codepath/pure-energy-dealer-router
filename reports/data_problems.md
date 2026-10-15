# Legacy Leads Data Audit & Problem Report

This report documents all data quality issues identified in `data/legacy_leads.csv` (40 rows) prior to cleaning and Firestore ingestion.

## 1. Distinct Raw Values

| Field | Distinct Raw Value Found | Frequency | Canonical Mapping | Mapping Strategy |
| :--- | :--- | :---: | :--- | :--- |
| **Product** | `PuREPower Home 3kWh` | 13 | `PuREPower Home 3kWh` | Exact match |
| | `PuREPower Home 5kWh` | 13 | `PuREPower Home 5kWh` | Exact match |
| | `PuREPower Commercial 10kWh` | 13 | `PuREPower Commercial 10kWh` | Exact match |
| | `Pure power 5 kwh` | 1 | `PuREPower Home 5kWh` | Case-insensitive & normalized whitespace/hyphen matching |
| **Source** | `Website` | 15 | `Website` | Exact match |
| | `Voice Agent` | 10 | `Voice Agent` | Exact match |
| | `WhatsApp` | 9 | `WhatsApp` | Exact match |
| | `Dealer Walk-in` | 5 | `Dealer Walk-in` | Exact match |
| | `website` | 1 | `Website` | Case-insensitive match |
| **Status** | `New` | 17 | `New` | Exact match |
| | `Contacted` | 7 | `Contacted` | Exact match |
| | `Converted` | 8 | `Converted` | Exact match |
| | `Lost` | 7 | `Lost` | Exact match |
| | `converted ` | 1 | `Converted` | Case-insensitive & stripped trailing whitespace |

---

## 2. Identified Data Problems by Category

### Phone Formatting (Punctuation, Spaces, Country Codes)
- **Problem**: Phone numbers contain internal spaces, hyphens, or leading international country codes (`+91`).
- **Affected `lead_id`s**: `L1004` (`98480 22 431`), `L1006` (`+91-9000012345`), `L1037` (`+91 9633021001`).
- **Cleaning Rule**: Strip all spaces, dashes, dots, and brackets. Strip leading `+91`, `91` (if 12 digits), or `0` (if 11 digits). Number must resolve to exactly 10 numeric digits.

### Invalid / Short Phone Number
- **Problem**: Phone number has only 5 digits (`12345`).
- **Affected `lead_id`s**: `L1009`.
- **Cleaning Rule**: Rejected as invalid phone number.

### Invalid / Short Pincode
- **Problem**: Pincode has only 4 digits (`5000`).
- **Affected `lead_id`s**: `L1012`.
- **Cleaning Rule**: Rejected as invalid pincode.

### Blank Mandatory Field
- **Problem**: Missing customer name.
- **Affected `lead_id`s**: `L1026`.
- **Cleaning Rule**: Rejected due to blank name.

### Name Casing
- **Problem**: Name in all uppercase (`SATISH P`).
- **Affected `lead_id`s**: `L1038`.
- **Cleaning Rule**: Collapsed whitespace and title-cased to `Satish P`.

### Non-Standard Product Spelling
- **Problem**: Lowercase and alternate spacing (`Pure power 5 kwh`).
- **Affected `lead_id`s**: `L1023`.
- **Cleaning Rule**: Canonicalized to `PuREPower Home 5kWh`.

### Source Casing
- **Problem**: All-lowercase source (`website`).
- **Affected `lead_id`s**: `L1028`.
- **Cleaning Rule**: Canonicalized to `Website`.

### Status Whitespace and Casing
- **Problem**: Lowercase and trailing whitespace (`converted `).
- **Affected `lead_id`s**: `L1020`.
- **Cleaning Rule**: Trimmed and canonicalized to `Converted`.

### Invalid Calendar Date
- **Problem**: Non-existent date (`31/09/2026` - September has 30 days).
- **Affected `lead_id`s**: `L1018`.
- **Cleaning Rule**: Day-first parsing fails on invalid calendar dates -> Rejected.

### Unmatched Pincode Prefix
- **Problem**: Pincode `110001` (prefix `110`) does not belong to any dealer's prefix list.
- **Affected `lead_id`s**: `L1015`.
- **Cleaning Rule**: Routed to fallback dealer `"In-house Sales"`; action marked `assigned_inhouse`.

### Duplicate Mobile Numbers
- **Problem**: 5 pairs of leads share the same normalized 10-digit mobile number:
  - `9565623510`: `L1003` (earlier date 2026-09-03) kept; `L1036` (2026-09-28) merged.
  - `9680557051`: `L1007` kept (lowest ID); `L1039` merged.
  - `9633021001`: `L1010` kept (0 fixes); `L1037` merged (phone normalized).
  - `9166838090`: `L1031` kept (0 fixes); `L1038` merged (name title-cased).
  - `9663925448`: `L1013` kept (lowest ID); Row 40 merged.

### Duplicate Lead ID Anomaly
- **Problem**: `L1033` appears twice in the input CSV (Row 33 for Mohan Rao, Row 40 for Kiran Kumar).
- **Handling**: Both rows are processed in input sequence. Row 40 is merged into `L1013`.
