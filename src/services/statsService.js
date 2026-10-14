import { STATUSES, IN_HOUSE } from '../constants.js';

// Counts leads grouped by dealer name, including all known dealers and In-house Sales.
export function countByDealer(leads = [], dealers = []) {
  const counts = {};

  // Pre-populate with all known dealers to show 0-count dealers
  dealers.forEach(dealer => {
    if (dealer && dealer.dealer_name) {
      counts[dealer.dealer_name] = 0;
    }
  });

  // Always include In-house Sales fallback
  counts[IN_HOUSE] = 0;

  // Tally each lead by dealer
  leads.forEach(lead => {
    const dealerName = (lead && lead.dealer) || IN_HOUSE;
    counts[dealerName] = (counts[dealerName] || 0) + 1;
  });

  return counts;
}

// Counts leads grouped by status, showing all four canonical statuses even with zero.
export function countByStatus(leads = []) {
  const counts = {};

  // Initialize all canonical statuses to 0
  STATUSES.forEach(status => {
    counts[status] = 0;
  });

  // Tally each lead by status
  leads.forEach(lead => {
    if (lead && lead.status) {
      counts[lead.status] = (counts[lead.status] || 0) + 1;
    }
  });

  return counts;
}
