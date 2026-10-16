
# Note
If I joined PURE Energy, the first thing I'd build is a dealer login with a "my leads" page, plus an alert when a new lead arrives.

Right now my app sends each lead to the right dealer, but the dealer never hears about it unless someone calls them. The dashboard is also open to anyone, which is fine for a demo but not for real customer phone numbers. With Firebase Auth, each dealer would see only their own leads and update the status themselves. A Cloud Function would send a WhatsApp or email message the moment a lead is assigned.

Next, I'd add a simple reminder: if a lead is still "New" after 24 hours, flag it and nudge the dealer.

Why: a lead nobody follows up on is wasted marketing money. Once dealers update statuses themselves, the data shows which dealers convert well and which are slow, so the team knows where to help.