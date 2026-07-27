// Mirrors the complexity rule enforced server-side in
// backend/app/modules/profile/schemas.py (_validate_strong_password).

export interface PasswordRequirement {
  key: string;
  label: string;
  met: boolean;
}

export function getPasswordRequirements(password: string): PasswordRequirement[] {
  return [
    { key: "length", label: "At least 8 characters", met: password.length >= 8 },
    { key: "upper", label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { key: "lower", label: "One lowercase letter", met: /[a-z]/.test(password) },
    { key: "digit", label: "One digit", met: /\d/.test(password) },
    {
      key: "special",
      label: "One special character",
      met: /[!"#$%&'()*+,\-./:;<=>?@[\]^_`{|}~\\]/.test(password),
    },
  ];
}

export function isStrongPassword(password: string): boolean {
  return getPasswordRequirements(password).every((req) => req.met);
}
