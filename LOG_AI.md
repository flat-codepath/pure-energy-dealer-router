# AI Log

## Tools I used

- **Claude (chat):** to decide the stack, plan the folder structure and write the prompts I gave to the coding agent. I also used it to sanity-check the data problems.
- **Google Antigravity:** to scaffold the React app and write the first versions of the Python cleaning script. I reviewed and ran everything myself.
-  **ChatGPT** for a quick regex check and random suggestions.

I didn't let AI decide things I couldn't explain. If I didn't understand a file, I asked it to walk me through it line by line before I committed it.

## My 3 most useful prompts

**1. The Part A build prompt (React + Firebase)**
I gave Antigravity the real dealer table, the allowed products, sources and statuses, and a few test pincodes with the dealer I expected for each (for example 502285 should go to Kandi Energy Point). I also told it the folder structure up front, with components only calling `services/` and never Firestore directly.
*Why it helped:* The code came back organised the way I wanted, and the test pincodes gave me a quick way to check the dealer matching.

**2. "Read the data first and tell me the problems. Don't write code yet."**
This was the first step of my Part B prompt. I made it list every data problem by type, with the lead_ids, before it wrote any cleaning rules.
*Why it helped:* I could check its list against the CSV myself and agree on the rules before any code existed. It also gave me most of the "data problems" section of my README.

**3. The reconciliation rules prompt**
A row can fit more than one label. For example, a lead with a messy phone number AND a pincode no dealer covers is both "fixed" and "assigned_inhouse". Without a rule, the script could label it either way.

So I gave the AI a priority order: rejected > merged > assigned_inhouse > fixed > imported. The highest one wins, and the reason column still lists every change. A messy-phone row with pincode 560001 becomes assigned_inhouse, with the reason "phone normalized; no dealer for prefix 560".
I also asked for dry-run by default, a --commit flag, and a self-check that the report has exactly 40 rows and only the five allowed actions.

*Why it helped:* Every row got one label, and the counts added up. Dry-run let me read reconciliation.csv before anything went into Firestore.

## Where the AI was wrong


- **What it did:**
    - In the first draft of the script, it marked row `L1023` as `rejected` with reason `unknown product: Pure power 5 kwh` instead of mapping it to `PuREPower Home 5kWh`.
    - Used Unicode checkmark symbols (`✓`) in the CLI self-check print statements at the end of the script.
- **How I noticed:** 
    - In `reports/reconciliation.csv`, the rejected count was 5 instead of 4, and `L1023` was rejected even though 5kWh is a valid capacity in our catalog.
    - When running `python scripts/clean_and_import.py` in PowerShell, Python crashed with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`.
     
- **How I fixed it:** 
   -`scripts/clean_and_import.py`, updated `canonical_choice` to check for capacity keywords (`"5kwh"`) when standardizing product strings rather than expecting the word 
   -Replaced the Unicode checkmarks with ASCII `[OK]` markers in `main()`.
- **What I took from it:** 
    -Real-world legacy data often omits brand sub-names like 'Home', so catalog matching needs capacity-based fallback rules."
    -

## Notes

- Everything in this repo has been run and checked by me.
- I made small commits as I went, so the history shows the order I worked in.