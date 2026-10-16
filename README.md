Kandi

# PURE Energy — Dealer Lead Router

An MIS web application for PURE Energy that captures customer leads across channels (Website, AI Voice Agent, WhatsApp, Dealer Walk-in) and automatically routes each lead to the appropriate regional dealer based on the first 3 digits of the customer's pincode. If no dealer serves the prefix, the lead is automatically assigned to **In-house Sales**.

---

## How to Run

### Prerequisites
- **Node.js**: v18+ (tested on Node v22)
- **Python**: 3.9+ (for the dealer seed script)
- **Firebase Project**: Firestore in region `asia-south1`

### 1. Installation
Clone the repository and install dependencies:
```bash
cd pure-energy-dealer-router
npm install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Firebase Web App configuration:
```bash
cp .env.example .env
```

Your `.env` should contain:
```env
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project_id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project_id.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
```

### 3. Seed Dealers Database (One-time setup)
Download a Service Account key from your Firebase Console (`Project Settings` > `Service accounts` > `Generate new private key`) and place it in the project root as `serviceAccountKey.json`.

Then run the seed script:
```powershell
# Windows PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS="serviceAccountKey.json"
python scripts/seed_dealers.py
```
*(On Linux/macOS: `export GOOGLE_APPLICATION_CREDENTIALS="serviceAccountKey.json" && python scripts/seed_dealers.py`)*

### 4. Deploy Security Rules
In the [Firebase Console](https://console.firebase.google.com/), open **Firestore Database** > **Rules**, paste the contents of `firestore.rules`, and click **Publish** (or run `firebase deploy --only firestore:rules`).

### 5. Start Development Server
```bash
npm run dev
```
Open your browser at `http://localhost:5173`.

### 6. Production Build
```bash
npm run build
```

---

## Assumptions & Design Decisions

1. **Routing Logic**:
   - The first 3 digits of the customer's 6-digit pincode are matched against each dealer's `pincode_prefixes` array.
   - If no dealer matches the prefix (e.g., `560001` or `110001`), the lead is routed to `"In-house Sales"`.
2. **Document ID as Normalized Mobile**:
   - The Firestore document ID is the customer's normalized 10-digit mobile number (`leads/{mobile}`).
   - This provides $O(1)$ duplicate prevention without requiring transactions or composite indexes.
   - Before saving, `getDoc` verifies uniqueness; if the document already exists, the form displays `"This mobile number already exists."`
3. **Mobile Normalization**:
   - The `normalizeMobile` utility cleans spaces, dashes, and standard Indian prefixes (`+91`, `91` on 12-digit numbers, or leading `0`), while safely preserving valid 10-digit numbers starting with `91` (e.g., `9186523513`).
4. **Strict Schema & Security Rules**:
   - Leads require exactly 8 fields: `name`, `mobile`, `pincode`, `product`, `source`, `dealer`, `status`, `createdAt`.
   - Creating a lead requires `status == 'New'`.
   - Updates are restricted exclusively to the `status` field using `request.resource.data.diff(resource.data).affectedKeys().hasOnly(['status'])`.
   - Deletions are forbidden.
5. **No External UI or State Frameworks**:
   - Built with plain React state and clean, responsive vanilla CSS in `src/index.css`.
   - Components communicate with Firestore exclusively through `src/services/` modules.
   - Aggregations in `statsService.js` are pure functions (`array in -> object out`).

---

## Part B: Legacy Leads Cleaning & Import

### Overview
A standalone Python pipeline ([scripts/clean_and_import.py](file:///c:/Users/nagna/pure-energy-dealer-router/scripts/clean_and_import.py)) that reads 40 raw legacy leads from `data/legacy_leads.csv`, standardizes and validates every record, deduplicates multiple submissions by mobile number, routes valid leads to regional dealers (or `In-house Sales`), and imports clean leads into the Firestore `leads` collection while producing a 40-row reconciliation audit report ([reports/reconciliation.csv](file:///c:/Users/nagna/pure-energy-dealer-router/reports/reconciliation.csv)).

### How to Run the Pipeline

#### 1. Dry-Run Mode (Default — No Database Writes)
Generates the reconciliation report and validates all integrity assertions without modifying Firestore:
```bash
python scripts/clean_and_import.py
```

#### 2. Commit Mode (Writes Clean Leads to Firestore)
Requires `GOOGLE_APPLICATION_CREDENTIALS` pointing to your service account key:
```powershell
# Windows PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS="serviceAccountKey.json"
python scripts/clean_and_import.py --commit
```
*(On Linux/macOS: `export GOOGLE_APPLICATION_CREDENTIALS="serviceAccountKey.json" && python scripts/clean_and_import.py --commit`)*

---

### Data Problems Found

The legacy dataset (`data/legacy_leads.csv`, 40 rows) contained 12 distinct types of real-world data quality issues that were audited and resolved:

| Problem Type | Description | Lead IDs Affected | How Handled |
| :--- | :--- | :--- | :--- |
| **Phone Formatting** | Numbers contained spaces, dashes, or leading country codes (`+91`). | `L1004`, `L1006`, `L1037` | Stripped all non-numeric characters (spaces, dashes, dots, brackets). Stripped leading `+91`, `91` (if 12 digits), or `0` (if 11 digits). Verified strictly 10 digits as string (`dtype=str`). Action: `fixed` or `merged`. |
| **Invalid Phone Number** | Incomplete phone number with only 5 digits (`12345`). | `L1009` | Cannot resolve to a valid 10-digit Indian mobile. Action: `rejected` (`invalid phone: 12345`). |
| **Invalid Pincode** | Incomplete pincode with only 4 digits (`5000`). | `L1012` | Must be strictly 6 digits for geographic routing. Action: `rejected` (`invalid pincode: 5000`). |
| **Blank Mandatory Field** | Name field was completely empty (`""`). | `L1026` | Customer name is mandatory for lead creation. Action: `rejected` (`blank name`). |
| **Name Casing & Whitespace** | Name was in all-uppercase (`SATISH P`). | `L1038` | Collapsed repeated whitespace and normalized using title-casing (`Satish P`). Action: `merged` into `L1031`. |
| **Product Casing & Format** | Non-standard spacing and lowercase product (`Pure power 5 kwh`). | `L1023` | Matched case-insensitively and whitespace-insensitively to canonical catalog value `PuREPower Home 5kWh`. Action: `fixed`. |
| **Source Casing** | Source provided in all-lowercase (`website`). | `L1028` | Standardized case-insensitively to canonical `Website`. Action: `fixed`. |
| **Status Formatting** | Lowercase initial letter and trailing space (`converted `). | `L1020` | Trimmed whitespace and mapped case-insensitively to canonical `Converted`. Action: `fixed`. |
| **Invalid Calendar Date** | Physically impossible date (`31/09/2026` — September only has 30 days). | `L1018` | Failed calendar parsing under day-first convention. Action: `rejected` (`unparseable date: 31/09/2026`). |
| **Unmatched Pincode** | Pincode prefix `110` (Delhi) had no matching regional dealer in Telangana / AP. | `L1015` | Routed to fallback dealer `In-house Sales`. Action: `assigned_inhouse`. |
| **Duplicate Mobile Numbers** | Five pairs of records shared identical normalized 10-digit mobile numbers. | `9565623510` (`L1003` & `L1036`)<br>`9680557051` (`L1007` & `L1039`)<br>`9633021001` (`L1010` & `L1037`)<br>`9166838090` (`L1031` & `L1038`)<br>`9663925448` (`L1013` & Row 40) | Kept exactly one record per mobile based on priority: (1) earliest `created_on`, (2) fewest fixed/blank fields, (3) lowest `lead_id`. Kept rows were imported; subsequent duplicates were marked as `merged` naming the kept lead. |
| **Duplicate Lead ID in Input** | `L1033` appeared twice in input CSV (Row 33 for Mohan Rao, Row 40 for Kiran Kumar). | `L1033` (Row 33 & Row 40) | Preserved original `lead_id`s in `reports/reconciliation.csv` to ensure 1:1 input row traceability. Row 40 was recognized as an exact duplicate of `L1013` and marked `merged`. |

---

### Reconciliation Summary

The output report `reports/reconciliation.csv` contains exactly 40 rows (1:1 with input, columns: `lead_id,action,reason`):

| Action | Count | Criteria |
| :--- | :---: | :--- |
| `imported` | **25** | Valid lead, imported with no changes needed. |
| `fixed` | **5** | Valid lead, imported after normalizing phone, casing, or product/source/status. |
| `merged` | **5** | Duplicate mobile number folded into an earlier lead (or already present in Firestore). |
| `rejected` | **4** | Unrecoverable data (bad phone, bad pincode, blank name, invalid date). |
| `assigned_inhouse` | **1** | Valid lead with unassigned pincode prefix (`110`) routed to `In-house Sales`. |
| **Total** | **40** | **Matches input rows 1:1** |

---

### Part B Design Decisions & Technical Details

1. **String Dtype Everywhere**:
   `pandas.read_csv` reads all columns with `dtype=str` and `keep_default_na=False`. This prevents silent corruption of phone numbers (e.g. converting `9848022431` to scientific notation `9.84e+09`) and loss of leading zeros in pincodes.
2. **Dealer Fallback Hierarchy**:
   Dealers are fetched live from Firestore collection `dealers`. If the collection is empty or running offline, the script falls back to `data/dealers.csv` (splitting pipe-separated prefixes like `"530|531"` into arrays).
3. **Deterministic Deduplication**:
   Groups by 10-digit mobile number. The winning record is chosen strictly by: (1) earliest `created_on`, (2) fewest fixes/blank fields, (3) lowest `lead_id`. Rejected records are never eligible to be the kept record.
4. **Idempotent Batch Writes**:
   Before writing to Firestore, existing documents in `leads/{mobile}` are queried. If a document already exists (e.g., entered through the web application), it is skipped and marked as `merged` (`"already exists in Firestore, lead_id kept in app"`). Valid new leads are written atomically using Firestore batch writes (`db.batch()`).
5. **Runtime Integrity Assertions**:
   The script validates 4 hard invariants at the end of execution:
   - Exactly 40 rows in the report matching the input count.
   - Lead IDs follow the input sequence 1:1.
   - Every action belongs to `{imported, fixed, merged, rejected, assigned_inhouse}`.
   - Zero blank reason entries.

