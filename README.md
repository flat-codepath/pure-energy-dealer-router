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

## Data Problems (Part B Placeholder)

*(This section will be populated with data cleaning findings and anomalies identified from `data/legacy_leads.csv` during Part B).*

<!-- TODO: Add findings from Part B analysis -->
