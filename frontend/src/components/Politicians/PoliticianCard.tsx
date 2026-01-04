import { Link } from 'react-router-dom'
import type { Politician } from '../../api/types'
import clsx from 'clsx'

interface PoliticianCardProps {
  politician: Politician
}

export default function PoliticianCard({ politician }: PoliticianCardProps) {
  const partyBadgeClass = clsx('party-badge', {
    'party-badge-d': politician.party === 'D',
    'party-badge-r': politician.party === 'R',
    'party-badge-i': politician.party === 'I' || politician.party === 'ID',
  })

  const partyName = {
    D: 'Democrat',
    R: 'Republican',
    I: 'Independent',
    ID: 'Independent',
  }[politician.party || 'I'] || 'Unknown'

  const transparencyClass = clsx('transparency-score', {
    'transparency-score-high': politician.transparency_score && politician.transparency_score >= 70,
    'transparency-score-medium': politician.transparency_score && politician.transparency_score >= 40 && politician.transparency_score < 70,
    'transparency-score-low': politician.transparency_score && politician.transparency_score < 40,
  })

  return (
    <Link
      to={`/politician/${politician.id}`}
      className="card hover:shadow-lg transition-shadow"
    >
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center text-2xl">
            {politician.chamber === 'senate' ? '🏛️' : '🏠'}
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

          <p className="text-xs text-gray-500 mt-1">
            {partyName} • {politician.chamber === 'senate' ? 'Senate' : 'House'}
          </p>
        </div>

        <div className="flex-shrink-0 text-right">
          {politician.transparency_score !== null ? (
            <div>
              <p className="text-xs text-gray-500 uppercase">Transparency</p>
              <p className={transparencyClass}>
                {politician.transparency_score.toFixed(0)}
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
