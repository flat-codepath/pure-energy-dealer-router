import os
import sys
import csv
import firebase_admin
from firebase_admin import credentials, firestore

def seed_dealers():
    """
    Seeds the 'dealers' Firestore collection from data/dealers.csv.
    Uses the GOOGLE_APPLICATION_CREDENTIALS environment variable.
    Idempotent: Uses dealer_id as the document ID, so it is safe to re-run.
    """
    # 1. Verify GOOGLE_APPLICATION_CREDENTIALS is set
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Set it before running:")
        print("  Windows (PowerShell): $env:GOOGLE_APPLICATION_CREDENTIALS=\"path/to/serviceAccountKey.json\"")
        print("  Linux/Mac:            export GOOGLE_APPLICATION_CREDENTIALS=\"path/to/serviceAccountKey.json\"")
        sys.exit(1)

    if not os.path.exists(cred_path):
        print(f"ERROR: Credentials file does not exist at: {cred_path}")
        sys.exit(1)

    # 2. Locate data/dealers.csv
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "dealers.csv")

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at: {csv_path}")
        sys.exit(1)

    # 3. Initialize Firebase Admin SDK
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    print(f"Connected to Firestore. Reading {csv_path}...")

    # 4. Read CSV and upsert documents into the 'dealers' collection
    seeded_count = 0
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dealer_id = row["dealer_id"].strip()
            
            # Split pipe-separated prefixes into an array of strings (e.g. "530|531" -> ["530", "531"])
            prefixes = [p.strip() for p in row["pincode_prefixes"].split("|") if p.strip()]

            dealer_data = {
                "dealer_id": dealer_id,
                "dealer_name": row["dealer_name"].strip(),
                "city": row["city"].strip(),
                "pincode_prefixes": prefixes,
                "contact_email": row["contact_email"].strip(),
            }

            # Doc ID is dealer_id (e.g. D01), ensuring idempotency on re-run
            db.collection("dealers").document(dealer_id).set(dealer_data)
            print(f"  ✓ Seeded {dealer_id}: {dealer_data['dealer_name']} (Prefixes: {prefixes})")
            seeded_count += 1

    print(f"\nSuccessfully seeded {seeded_count} dealers into Firestore 'dealers' collection.")

if __name__ == "__main__":
    seed_dealers()
