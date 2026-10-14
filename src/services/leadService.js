import {
  collection,
  doc,
  getDoc,
  setDoc,
  updateDoc,
  query,
  orderBy,
  onSnapshot,
  serverTimestamp,
} from 'firebase/firestore';
import { db } from '../firebase.js';
import { findDealerByPincode } from './dealerService.js';

// Checks for duplicate mobile and creates a new lead document routed to a dealer.
export async function createLead({ name, mobile, pincode, product, source }, dealers) {
  const leadRef = doc(db, 'leads', mobile);
  const existingDoc = await getDoc(leadRef);

  if (existingDoc.exists()) {
    throw new Error('This mobile number already exists');
  }

  const dealer = findDealerByPincode(pincode, dealers);

  // Exactly 8 keys to strictly satisfy security rules
  const newLead = {
    name: name.trim(),
    mobile,
    pincode: pincode.trim(),
    product,
    source,
    dealer,
    status: 'New',
    createdAt: serverTimestamp(),
  };

  await setDoc(leadRef, newLead);
  return { id: mobile, ...newLead };
}

// Subscribes to live updates from the leads collection ordered by creation date.
export function subscribeToLeads(onUpdate, onError) {
  const leadsCol = collection(db, 'leads');
  const q = query(leadsCol, orderBy('createdAt', 'desc'));

  return onSnapshot(
    q,
    snapshot => {
      const leads = snapshot.docs.map(docSnapshot => ({
        id: docSnapshot.id,
        ...docSnapshot.data(),
      }));
      onUpdate(leads);
    },
    error => {
      if (onError) onError(error);
      else console.error('Error subscribing to leads:', error);
    }
  );
}

// Updates the status of an existing lead document.
export async function updateLeadStatus(mobile, newStatus) {
  const leadRef = doc(db, 'leads', mobile);
  await updateDoc(leadRef, { status: newStatus });
}
