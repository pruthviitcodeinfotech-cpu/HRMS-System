/**
 * Validates if a string is a valid email address.
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validates if a string contains only numeric digits.
 */
export const isNumeric = (str: string): boolean => {
  const numericRegex = /^\d+$/;
  return numericRegex.test(str);
};

/**
 * Validates if a string matches the standard Indian Mobile Number pattern (+91 or 10-digit).
 */
export const isValidIndianMobile = (mobile: string): boolean => {
  const mobileRegex = /^(?:\+91|91)?[6-9]\d{9}$/;
  return mobileRegex.test(mobile);
};
