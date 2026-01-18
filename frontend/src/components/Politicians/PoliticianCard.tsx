import React from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import type { Politician } from '../../api/types'
import { getPartyBadgeClass, getPartyName } from '../../utils'

interface PoliticianCardProps {
  politician: Politician
}

function PoliticianCardComponent({ politician }: PoliticianCardProps) {
  const partyBadgeClass = getPartyBadgeClass(politician.party)

  // Convert to number in case it comes as string from API
  const score = politician.transparency_score ? Number(politician.transparency_score) : null

  const transparencyClass = clsx('transparency-score', {
    'transparency-score-high': score && score >= 70,
    'transparency-score-medium': score && score >= 40 && score < 70,
    'transparency-score-low': score && score < 40,
  })

  return (
    <Link
      to={`/politician/${politician.id}`}
      className="card hover:shadow-lg transition-shadow"
    >
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center text-2xl">
            <span aria-hidden="true">{politician.chamber === 'senate' ? '🏛️' : '🏠'}</span>
            <span className="sr-only">{politician.chamber === 'senate' ? 'Senator' : 'Representative'}</span>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-semibold text-gray-900 truncate">
              {politician.full_name}
            </h3>
            <span className={partyBadgeClass}>{politician.party}</span>
          </div>

          <p className="text-sm text-gray-600">
            {politician.title} • {politician.state}
            {politician.district && ` District ${politician.district}`}
          </p>

          <p className="text-xs text-gray-600 mt-1">
            {getPartyName(politician.party)} • {politician.chamber === 'senate' ? 'Senate' : 'House'}
          </p>
        </div>

        <div className="flex-shrink-0 text-right">
          {score !== null ? (
            <div>
              <p className="text-xs text-gray-500 uppercase">Transparency</p>
              <p className={transparencyClass}>
                {score.toFixed(0)}
              </p>
            </div>
          ) : (
            <p className="text-xs text-gray-400">No score</p>
          )}
        </div>
      </div>
    </Link>
  )
}

// Memoize to prevent unnecessary re-renders in lists
const PoliticianCard = React.memo(PoliticianCardComponent)

export default PoliticianCard
