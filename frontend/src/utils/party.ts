import clsx from 'clsx'

/**
 * Map of party codes to full names.
 */
export const PARTY_NAMES: Record<string, string> = {
  D: 'Democrat',
  R: 'Republican',
  I: 'Independent',
  ID: 'Independent',
}

/**
 * Get the CSS class for a party badge.
 */
export function getPartyBadgeClass(party: string | undefined, extraClasses?: string): string {
  return clsx('party-badge', extraClasses, {
    'party-badge-d': party === 'D',
    'party-badge-r': party === 'R',
    'party-badge-i': party === 'I' || party === 'ID',
  })
}

/**
 * Get the full name for a party code.
 */
export function getPartyName(party: string | undefined): string {
  return PARTY_NAMES[party || 'I'] || 'Unknown'
}
