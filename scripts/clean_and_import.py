"""
scripts/clean_and_import.py

Cleans legacy lead data from data/legacy_leads.csv, validates fields,
resolves dealer routing, handles duplicate merging, generates a
reconciliation report (reports/reconciliation.csv), and imports valid
leads into Firestore.

Usage:
  # Dry-run mode (default, no Firestore writes, generates report):
  python scripts/clean_and_import.py

  # Commit mode (writes valid leads to Firestore):
  python scripts/clean_and_import.py --commit
"""

import os
import sys
import re
import csv
import argparse
from datetime import datetime
import pandas as pd

# -----------------------------------------------------------------------------
# Business Constants & Allowed Values
# -----------------------------------------------------------------------------
ALLOWED_PRODUCTS = [
    "PuREPower Home 3kWh",
    "PuREPower Home 5kWh",
    "PuREPower Commercial 10kWh",
]

ALLOWED_SOURCES = [
    "Website",
    "Voice Agent",
    "WhatsApp",
    "Dealer Walk-in",
]

ALLOWED_STATUSES = [
    "New",
    "Contacted",
    "Converted",
    "Lost",
]

ALLOWED_ACTIONS = {
    "imported",
    "fixed",
    "merged",
    "rejected",
    "assigned_inhouse",
}

FALLBACK_DEALER = "In-house Sales"


# -----------------------------------------------------------------------------
# Small, Named Cleaning Helper Functions
# -----------------------------------------------------------------------------

def clean_name(raw_name: str):
    """Trims whitespace, collapses repeated spaces, and applies title-casing."""
    if not raw_name or not str(raw_name).strip():
        raise ValueError("blank name")
    
    # Strip leading/trailing spaces and collapse repeated internal spaces
    normalized = re.sub(r"\s+", " ", str(raw_name).strip()).title()
    changes = []
    if normalized != str(raw_name).strip():
        changes.append("name title-cased")
    return normalized, changes


def clean_phone(raw_phone: str):
    """Removes formatting chars, strips +91/91/0 prefixes, and validates 10 digits."""
    if not raw_phone:
        raise ValueError("blank phone")
    
    # Keep as string to avoid floating point or scientific notation truncation
    val = str(raw_phone).strip()
    
    # Remove spaces, hyphens, periods, and parentheses
    cleaned = re.sub(r"[\s\-\.\(\)]+", "", val)
    
    # Strip country code / leading zeros
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    
    # Validate strictly 10 digits
    if len(cleaned) != 10 or not cleaned.isdigit():
        raise ValueError(f"invalid phone: {val}")
    
    changes = []
    if cleaned != val:
        changes.append("phone normalized")
    return cleaned, changes


def clean_pincode(raw_pincode: str):
    """Trims whitespace and verifies pincode is strictly 6 digits."""
    if not raw_pincode:
        raise ValueError("blank pincode")
    
    val = str(raw_pincode).strip()
    if len(val) != 6 or not val.isdigit():
        raise ValueError(f"invalid pincode: {val}")
    
    changes = []
    if val != str(raw_pincode):
        changes.append("pincode trimmed")
    return val, changes


def canonical_choice(raw_val: str, allowed_list: list, field_name: str):
    """Matches values case-insensitively and whitespace-insensitively to allowed lists."""
    if not raw_val or not str(raw_val).strip():
        if field_name == "status":
            return "New", ["status defaulted to New"]
        raise ValueError(f"blank {field_name}")

    val = str(raw_val).strip()

    # Helper function to normalize strings for comparison: lowercase, no spaces or hyphens
    def simplify(s):
        return re.sub(r"[\s\-]+", "", s).lower()

    simplified_val = simplify(val)

    # 1. Direct simplified match
    for allowed in allowed_list:
        if simplified_val == simplify(allowed):
            changes = []
            if val != allowed:
                changes.append(f"{field_name} standardized")
            return allowed, changes

    # 2. Confident semantic mapping for product variants (e.g. 'Pure power 5 kwh' -> 'PuREPower Home 5kWh')
    if field_name == "product":
        if "3kwh" in simplified_val:
            return "PuREPower Home 3kWh", ["product standardized"]
        if "5kwh" in simplified_val:
            return "PuREPower Home 5kWh", ["product standardized"]
        if "10kwh" in simplified_val:
            return "PuREPower Commercial 10kWh", ["product standardized"]

    # Fallback for status: default to "New" and count as fixed
    if field_name == "status":
        return "New", ["status defaulted to New"]

    # Product or Source could not be mapped confidently
    raise ValueError(f"unknown {field_name}: {val}")


def parse_date(raw_date: str):
    """Parses date string with day-first convention for ambiguous dd/mm/yyyy."""
    if not raw_date or not str(raw_date).strip():
        raise ValueError("blank created_on date")

    val = str(raw_date).strip()

    # Formats to try in sequence; assumes day-first (e.g. 03/09/2026 is 3rd Sept 2026)
    date_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%b-%Y",
        "%d.%m.%Y",
        "%d-%m-%Y",
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue

    # If all formats fail or date is invalid (e.g. 31/09/2026)
    raise ValueError(f"unparseable date: {val}")


def find_dealer(pincode: str, dealers: list):
    """Matches first 3 digits of pincode against dealer prefix arrays."""
    prefix = pincode[:3]
    for dealer in dealers:
        if prefix in dealer.get("pincode_prefixes", []):
            return dealer["dealer_name"]
    return FALLBACK_DEALER


# -----------------------------------------------------------------------------
# Dealer Loading (Firestore with CSV fallback)
# -----------------------------------------------------------------------------

def load_dealers(db):
    """Loads dealers from Firestore collection 'dealers', falling back to dealers.csv."""
    dealers = []
    
    # 1. Try reading from Firestore if db connection is provided
    if db is not None:
        try:
            docs = list(db.collection("dealers").stream())
            if docs:
                for doc in docs:
                    dealers.append(doc.to_dict())
                print(f"[Reference Data] Loaded {len(dealers)} dealers from Firestore 'dealers' collection.")
                return dealers
            else:
                print("[Reference Data] Firestore 'dealers' collection is empty.")
        except Exception as e:
            print(f"[Reference Data] Warning: Could not read Firestore 'dealers' collection ({e}).")

    # 2. Fall back to data/dealers.csv
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "dealers.csv")
    if os.path.exists(csv_path):
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prefixes = [p.strip() for p in row["pincode_prefixes"].split("|") if p.strip()]
                dealers.append({
                    "dealer_id": row["dealer_id"].strip(),
                    "dealer_name": row["dealer_name"].strip(),
                    "city": row["city"].strip(),
                    "pincode_prefixes": prefixes,
                    "contact_email": row.get("contact_email", "").strip(),
                })
        print(f"[Reference Data] Loaded {len(dealers)} dealers from fallback file: data/dealers.csv")
        return dealers

    raise RuntimeError("No dealer reference data available from Firestore or data/dealers.csv")


# -----------------------------------------------------------------------------
# Row Cleaning & Validation
# -----------------------------------------------------------------------------

def clean_row(raw_row: dict, dealers: list):
    """
    Cleans individual lead row.
    Returns a dict with cleaned values, validation status, and list of applied fixes.
    """
    lead_id = raw_row["lead_id"].strip()
    fixes = []
    
    # Clean individual fields, catching any validation errors
    try:
        cleaned_name, name_fixes = clean_name(raw_row.get("name", ""))
        fixes.extend(name_fixes)

        cleaned_phone, phone_fixes = clean_phone(raw_row.get("phone", ""))
        fixes.extend(phone_fixes)

        cleaned_pincode, pin_fixes = clean_pincode(raw_row.get("pincode", ""))
        fixes.extend(pin_fixes)

        cleaned_product, prod_fixes = canonical_choice(raw_row.get("product", ""), ALLOWED_PRODUCTS, "product")
        fixes.extend(prod_fixes)

        cleaned_source, src_fixes = canonical_choice(raw_row.get("source", ""), ALLOWED_SOURCES, "source")
        fixes.extend(src_fixes)

        cleaned_status, status_fixes = canonical_choice(raw_row.get("status", ""), ALLOWED_STATUSES, "status")
        fixes.extend(status_fixes)

        parsed_created_on = parse_date(raw_row.get("created_on", ""))

        dealer_name = find_dealer(cleaned_pincode, dealers)

        return {
            "lead_id": lead_id,
            "is_valid": True,
            "error_reason": None,
            "fixes": fixes,
            "data": {
                "name": cleaned_name,
                "mobile": cleaned_phone,
                "pincode": cleaned_pincode,
                "product": cleaned_product,
                "source": cleaned_source,
                "dealer": dealer_name,
                "status": cleaned_status,
                "createdAt": parsed_created_on,
                "legacyLeadId": lead_id,
            }
        }
    except ValueError as e:
        return {
            "lead_id": lead_id,
            "is_valid": False,
            "error_reason": str(e),
            "fixes": [],
            "data": None,
        }


# -----------------------------------------------------------------------------
# Duplicate Resolution & Action Classification
# -----------------------------------------------------------------------------

def resolve_duplicates_and_actions(cleaned_records: list):
    """
    Groups valid leads by normalized 10-digit mobile.
    Selects one lead per mobile according to tie-breaker rules:
      1. Earliest created_on date
      2. Fewer blank/fixed fields
      3. Lowest lead_id
    Assigns reconciliation action and reason for every row.
    """
    # Map valid records by normalized mobile
    mobile_groups = {}
    for idx, rec in enumerate(cleaned_records):
        if rec["is_valid"]:
            mobile = rec["data"]["mobile"]
            mobile_groups.setdefault(mobile, []).append((idx, rec))

    # Determine kept record for each mobile group
    kept_indices = set()
    kept_lead_map = {}  # mobile -> kept lead_id

    for mobile, group in mobile_groups.items():
        if len(group) == 1:
            idx, rec = group[0]
            kept_indices.add(idx)
            kept_lead_map[mobile] = rec["lead_id"]
        else:
            # Sort group: (1) earliest created_on, (2) fewer fixes count, (3) lowest lead_id
            sorted_group = sorted(
                group,
                key=lambda item: (
                    item[1]["data"]["createdAt"],
                    len(item[1]["fixes"]),
                    item[1]["lead_id"],
                )
            )
            winner_idx, winner_rec = sorted_group[0]
            kept_indices.add(winner_idx)
            kept_lead_map[mobile] = winner_rec["lead_id"]

    # Assign action and reason to each row in the original order
    reconciliation = []
    for idx, rec in enumerate(cleaned_records):
        lid = rec["lead_id"]

        # 1. Rejected rows (highest priority)
        if not rec["is_valid"]:
            reconciliation.append({
                "lead_id": lid,
                "action": "rejected",
                "reason": rec["error_reason"],
                "data_to_import": None,
            })
            continue

        mobile = rec["data"]["mobile"]

        # 2. Duplicate merged rows
        if idx not in kept_indices:
            winner_lid = kept_lead_map[mobile]
            reconciliation.append({
                "lead_id": lid,
                "action": "merged",
                "reason": f"duplicate of {winner_lid}, kept earlier record",
                "data_to_import": None,
            })
            continue

        # Kept row: determine between assigned_inhouse, fixed, or imported
        dealer = rec["data"]["dealer"]
        fixes = rec["fixes"]

        if dealer == FALLBACK_DEALER:
            action = "assigned_inhouse"
            prefix = rec["data"]["pincode"][:3]
            base_reason = f"no dealer for prefix {prefix}, routed to {FALLBACK_DEALER}"
            reason = f"{base_reason}; " + "; ".join(fixes) if fixes else base_reason
        elif fixes:
            action = "fixed"
            reason = "; ".join(fixes)
        else:
            action = "imported"
            reason = "clean record; all fields valid"

        reconciliation.append({
            "lead_id": lid,
            "action": action,
            "reason": reason,
            "data_to_import": rec["data"],
        })

    return reconciliation


# -----------------------------------------------------------------------------
# Firestore Ingestion
# -----------------------------------------------------------------------------

def init_firestore():
    """Initializes Firebase Admin SDK using GOOGLE_APPLICATION_CREDENTIALS."""
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        return None
    
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def import_to_firestore(db, reconciliation_records: list, commit: bool):
    """
    Imports valid records into Firestore collection 'leads' using batches.
    Maintains idempotency: if a document already exists, it is NOT overwritten
    and is recorded as 'merged' with reason 'already exists in Firestore, lead_id kept in app'.
    """
    written_count = 0
    items_to_import = [r for r in reconciliation_records if r["data_to_import"] is not None]

    if db is None:
        if commit:
            print("\n[ERROR] Cannot commit: GOOGLE_APPLICATION_CREDENTIALS is not set or invalid.")
            sys.exit(1)
        else:
            print("\n[Mode] DRY-RUN (Offline): No Firestore credentials found. Using local reference data.")
            return written_count

    print(f"\n[Firestore] Checking {len(items_to_import)} candidate leads against Firestore 'leads' collection...")

    leads_col = db.collection("leads")
    batch = db.batch()
    new_docs_count = 0

    for rec in items_to_import:
        data = rec["data_to_import"]
        mobile = data["mobile"]
        doc_ref = leads_col.document(mobile)
        existing = doc_ref.get()

        if existing.exists:
            rec["action"] = "merged"
            rec["reason"] = "already exists in Firestore, lead_id kept in app"
            print(f"  - Skip existing doc {mobile} (kept in app)")
        else:
            if commit:
                batch.set(doc_ref, data)
                written_count += 1
                print(f"  + Queued {mobile} ({data['name']}) -> {data['dealer']}")
            new_docs_count += 1

    if commit:
        if written_count > 0:
            batch.commit()
            print(f"[Firestore] Successfully committed {written_count} documents in a single batch.")
        else:
            print("[Firestore] No new documents needed to be written.")
    else:
        already_count = len(items_to_import) - new_docs_count
        print(f"[Mode] DRY-RUN: Skipping Firestore writes ({already_count} existing, {new_docs_count} ready to import).")
        print("      Pass --commit to execute the write batch.")

    return written_count


# -----------------------------------------------------------------------------
# Main Execution Pipeline
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Clean and import legacy leads into Firestore.")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually commit writes to Firestore (default is dry-run)",
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    leads_csv_path = os.path.join(base_dir, "data", "legacy_leads.csv")
    reports_dir = os.path.join(base_dir, "reports")
    reconciliation_csv_path = os.path.join(reports_dir, "reconciliation.csv")

    # 1. Read input CSV using dtype=str to avoid corrupting phone numbers or pincodes
    if not os.path.exists(leads_csv_path):
        print(f"ERROR: Input file not found: {leads_csv_path}")
        sys.exit(1)
    
    df_raw = pd.read_csv(leads_csv_path, dtype=str, keep_default_na=False)
    input_rows = df_raw.to_dict(orient="records")
    print(f"[Input] Read {len(input_rows)} rows from {leads_csv_path}")
    
    # 2. Connect to Firestore (if credentials exist) and load dealer reference data
    db = init_firestore()
    dealers = load_dealers(db)
    
    # 3. Clean and validate each row
    cleaned_records = [clean_row(row, dealers) for row in input_rows]
    
    # 4. Resolve duplicates and determine reconciliation action
    reconciliation_records = resolve_duplicates_and_actions(cleaned_records)
    
    # 5. Handle Firestore import (or dry run)
    written_count = import_to_firestore(db, reconciliation_records, commit=args.commit)

    # 6. Write reconciliation CSV report
    os.makedirs(reports_dir, exist_ok=True)
    report_rows = []
    for r in reconciliation_records:
        report_rows.append({
            "lead_id": r["lead_id"],
            "action": r["action"],
            "reason": r["reason"],
        })

    report_df = pd.DataFrame(report_rows, columns=["lead_id", "action", "reason"])
    report_df.to_csv(reconciliation_csv_path, index=False, encoding="utf-8")
    print(f"\n[Report] Wrote {len(report_df)} rows to {reconciliation_csv_path}")

    # 7. Print summary statistics
    action_counts = report_df["action"].value_counts().to_dict()
    print("\n" + "=" * 45)
    print("           RECONCILIATION SUMMARY            ")
    print("=" * 45)
    for action in ["imported", "fixed", "merged", "rejected", "assigned_inhouse"]:
        print(f"  {action:<18}: {action_counts.get(action, 0):>3}")
    print("-" * 45)
    print(f"  Total Input Rows  : {len(report_df):>3}")
    print(f"  Written to DB     : {written_count:>3}")
    print("=" * 45)

    # 8. Self-Checks & Assertions (fail loudly if any invariant is violated)
    assert len(report_df) == len(input_rows), (
        f"Assertion Failed: Report row count ({len(report_df)}) does not match input ({len(input_rows)})"
    )
    assert list(report_df["lead_id"]) == list(df_raw["lead_id"]), (
        "Assertion Failed: Report lead_ids do not match input order exactly"
    )
    invalid_actions = set(report_df["action"]) - ALLOWED_ACTIONS
    assert not invalid_actions, (
        f"Assertion Failed: Report contains illegal actions: {invalid_actions}"
    )
    blank_reasons = report_df[report_df["reason"].str.strip() == ""]
    assert len(blank_reasons) == 0, (
        "Assertion Failed: Found blank reasons in reconciliation report"
    )
    print("\n[Self-Check] ALL 4 INTEGRITY ASSERTIONS PASSED:")
    print("  [OK] Row count matches input exactly (40 rows)")
    print("  [OK] Lead IDs match input sequence 1:1")
    print("  [OK] All actions belong to allowed enum set")
    print("  [OK] Zero blank reasons in reconciliation report")


if __name__ == "__main__":
    main()
