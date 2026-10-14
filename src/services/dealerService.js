import { collection, getDocs } from 'firebase/firestore';
import { db } from '../firebase.js';
import { IN_HOUSE } from '../constants.js';

// Fetches all dealer records from the Firestore dealers collection.
export async function getDealers() {
  const snapshot = await getDocs(collection(db, 'dealers'));
  return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
}

// Finds matching dealer name based on the first 3 digits of a pincode, falling back to In-house Sales.
export function findDealerByPincode(pincode, dealers) {
  if (!pincode || String(pincode).length < 3 || !Array.isArray(dealers)) {
    return IN_HOUSE;
  }

  const prefix = String(pincode).trim().slice(0, 3);
  const matched = dealers.find(
    dealer => Array.isArray(dealer.pincode_prefixes) && dealer.pincode_prefixes.includes(prefix)
  );

  return matched ? matched.dealer_name : IN_HOUSE;
}
