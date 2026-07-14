/**
 * Serializes an object into a URI query string, stripping null, undefined, or empty values.
 */
export const buildQueryString = (params: Record<string, unknown>): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      if (Array.isArray(value)) {
        (value as unknown[]).forEach((val) => query.append(key, String(val)));
      } else {
        query.append(key, String(value));
      }
    }
  });
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
};
