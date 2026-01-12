/**
 * Format a number as currency with appropriate suffix (K, M).
 */
export function formatCurrency(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`
  }
  return `$${value}`
}

/**
 * Format a number with commas.
 */
export function formatNumber(value: number): string {
  return value.toLocaleString()
}

/**
 * Format a date string to locale date.
 */
export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString()
}
