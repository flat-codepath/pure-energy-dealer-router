import React, { useState } from 'react';
import { STATUSES } from '../constants.js';
import { updateLeadStatus } from '../services/leadService.js';

export default function StatusSelect({ mobile, currentStatus }) {
  const [status, setStatus] = useState(currentStatus || 'New');
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState(null);

  // Sync state if external lead status changes
  React.useEffect(() => {
    setStatus(currentStatus || 'New');
  }, [currentStatus]);

  async function handleChange(e) {
    const newStatus = e.target.value;
    const previousStatus = status;

    setStatus(newStatus);
    setIsUpdating(true);
    setError(null);

    try {
      // Calls leadService to update status in Firestore (leads/{mobile})
      await updateLeadStatus(mobile, newStatus);
    } catch (err) {
      // Revert status on failure and show error
      setStatus(previousStatus);
      setError('Failed to update status');
      console.error('Status update failed:', err);
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <div className="status-select-wrapper">
      <select
        value={status}
        onChange={handleChange}
        disabled={isUpdating}
        className={`status-select status-${status.toLowerCase()}`}
        aria-label="Update lead status"
      >
        {STATUSES.map(s => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      {isUpdating && <span className="status-updating-indicator">...</span>}
      {error && <span className="error-text small-error">{error}</span>}
    </div>
  );
}
