import React, { useState } from 'react';
import { PRODUCTS, SOURCES } from '../constants.js';
import { normalizeMobile, isValidMobile, isValidPincode, isValidName } from '../utils/validators.js';
import { createLead } from '../services/leadService.js';
import { findDealerByPincode } from '../services/dealerService.js';

export default function LeadForm({ dealers }) {
  // Form input states
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [pincode, setPincode] = useState('');
  const [product, setProduct] = useState(PRODUCTS[0]);
  const [source, setSource] = useState(SOURCES[0]);

  // Validation and UI feedback states
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Live dealer preview based on current pincode input
  const previewDealer =
    pincode.trim().length >= 3 ? findDealerByPincode(pincode.trim(), dealers) : null;

  // Handles form submission
  async function handleSubmit(e) {
    e.preventDefault();
    setSuccessMessage('');

    const newErrors = {};

    // 1. Validate Name
    if (!isValidName(name)) {
      newErrors.name = 'Full name is required.';
    }

    // 2. Validate Mobile (normalize first to accept spaces, dashes, +91)
    const normalizedMobile = normalizeMobile(mobile);
    if (!isValidMobile(normalizedMobile)) {
      newErrors.mobile = 'Please enter a valid 10-digit mobile number.';
    }

    // 3. Validate Pincode
    if (!isValidPincode(pincode)) {
      newErrors.pincode = 'Please enter a valid 6-digit pincode.';
    }

    // 4. Validate Product and Source
    if (!product) {
      newErrors.product = 'Please select a product.';
    }
    if (!source) {
      newErrors.source = 'Please select a lead source.';
    }

    // If any validation errors exist, stop submission and display them inline
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Clear existing errors before network call
    setErrors({});
    setIsSubmitting(true);

    try {
      // Create lead and route to dealer (calls leadService, no direct Firestore calls)
      const created = await createLead(
        {
          name,
          mobile: normalizedMobile,
          pincode,
          product,
          source,
        },
        dealers
      );

      // Show success feedback
      setSuccessMessage(
        `Lead created successfully! Routed to "${created.dealer}".`
      );

      // Reset form to initial state
      setName('');
      setMobile('');
      setPincode('');
      setProduct(PRODUCTS[0]);
      setSource(SOURCES[0]);
    } catch (err) {
      // Check for duplicate mobile error message
      if (err.message === 'This mobile number already exists') {
        setErrors({ mobile: 'This mobile number already exists.' });
      } else {
        setErrors({ general: err.message || 'Failed to save lead. Please try again.' });
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h2>Add New Lead</h2>
      <p className="card-subtitle">
        Customer leads will be automatically routed to the nearest dealer by pincode.
      </p>

      {successMessage && (
        <div className="alert alert-success" role="status">
          {successMessage}
        </div>
      )}

      {errors.general && (
        <div className="alert alert-error" role="alert">
          {errors.general}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        {/* Customer Name */}
        <div className="form-group">
          <label htmlFor="lead-name">Customer Name *</label>
          <input
            id="lead-name"
            type="text"
            placeholder="e.g. Ravi Kumar"
            value={name}
            onChange={e => {
              setName(e.target.value);
              if (errors.name) setErrors(prev => ({ ...prev, name: null }));
            }}
            className={errors.name ? 'input-error' : ''}
          />
          {errors.name && <span className="error-text">{errors.name}</span>}
        </div>

        {/* Mobile Number */}
        <div className="form-group">
          <label htmlFor="lead-mobile">Mobile Number (10 Digits) *</label>
          <input
            id="lead-mobile"
            type="tel"
            placeholder="e.g. 98480 22 431 or +91-9000012345"
            value={mobile}
            onChange={e => {
              setMobile(e.target.value);
              if (errors.mobile) setErrors(prev => ({ ...prev, mobile: null }));
            }}
            className={errors.mobile ? 'input-error' : ''}
          />
          {errors.mobile && <span className="error-text">{errors.mobile}</span>}
        </div>

        {/* Pincode & Routing Preview */}
        <div className="form-group">
          <label htmlFor="lead-pincode">Pincode (6 Digits) *</label>
          <input
            id="lead-pincode"
            type="text"
            maxLength={6}
            placeholder="e.g. 502285"
            value={pincode}
            onChange={e => {
              setPincode(e.target.value);
              if (errors.pincode) setErrors(prev => ({ ...prev, pincode: null }));
            }}
            className={errors.pincode ? 'input-error' : ''}
          />
          {errors.pincode && <span className="error-text">{errors.pincode}</span>}

          {/* Live routing preview indicator */}
          {previewDealer && !errors.pincode && (
            <div className="routing-preview">
              Routed Dealer: <strong>{previewDealer}</strong>
            </div>
          )}
        </div>

        {/* Product Selection */}
        <div className="form-group">
          <label htmlFor="lead-product">Product *</label>
          <select
            id="lead-product"
            value={product}
            onChange={e => setProduct(e.target.value)}
          >
            {PRODUCTS.map(prod => (
              <option key={prod} value={prod}>
                {prod}
              </option>
            ))}
          </select>
        </div>

        {/* Source Selection */}
        <div className="form-group">
          <label htmlFor="lead-source">Lead Source *</label>
          <select
            id="lead-source"
            value={source}
            onChange={e => setSource(e.target.value)}
          >
            {SOURCES.map(src => (
              <option key={src} value={src}>
                {src}
              </option>
            ))}
          </select>
        </div>

        {/* Submit Button */}
        <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Routing & Saving Lead...' : 'Save and Route Lead'}
        </button>
      </form>
    </div>
  );
}
