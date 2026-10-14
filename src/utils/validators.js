/**
 * Strips spaces, dashes, and leading country code / prefixes (+91, 91 when 12 digits, or leading 0).
 * Examples:
 *   "98480 22 431"    -> "9848022431"
 *   "+91-9000012345"  -> "9000012345"
 *   "09848022431"     -> "9848022431"
 */
export function normalizeMobile(raw) {
  if (!raw) return '';

  let cleaned = String(raw).trim();

  // Strip explicit "+91" prefix if present
  if (cleaned.startsWith('+91')) {
    cleaned = cleaned.slice(3);
  }

  // Remove all non-digit characters (spaces, dashes, parentheses)
  cleaned = cleaned.replace(/\D/g, '');

  // If 11 digits starting with 0, remove the leading 0
  if (cleaned.length === 11 && cleaned.startsWith('0')) {
    cleaned = cleaned.slice(1);
  }

  // If 12 digits starting with 91, remove the country code 91
  if (cleaned.length === 12 && cleaned.startsWith('91')) {
    cleaned = cleaned.slice(2);
  }

  return cleaned;
}

/**
 * Validates that the normalized mobile number is exactly 10 digits.
 */
export function isValidMobile(mobile) {
  const normalized = normalizeMobile(mobile);
  return /^[0-9]{10}$/.test(normalized);
}

/**
 * Validates that the pincode is exactly 6 digits.
 */
export function isValidPincode(pincode) {
  if (!pincode) return false;
  const cleaned = String(pincode).trim();
  return /^[0-9]{6}$/.test(cleaned);
}

/**
 * Validates that customer name is non-empty.
 */
export function isValidName(name) {
  return typeof name === 'string' && name.trim().length > 0;
}
