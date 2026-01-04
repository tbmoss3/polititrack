import type { TransparencyBreakdown } from '../../api/types'
import clsx from 'clsx'

interface TransparencyScoreProps {
  score: number | null
  breakdown: TransparencyBreakdown | null
}

export default function TransparencyScore({ score, breakdown }: TransparencyScoreProps) {
  if (score === null) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Transparency Score</h3>
        <p className="text-gray-500">No transparency data available</p>
      </div>
    )
  }

  const scoreClass = clsx('text-5xl font-bold', {
    'text-green-600': score >= 70,
    'text-yellow-600': score >= 40 && score < 70,
    'text-red-600': score < 40,
  })

  const scoreLabel = score >= 70 ? 'High' : score >= 40 ? 'Medium' : 'Low'

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Transparency Score</h3>

      <div className="flex items-center justify-center mb-6">
        <div className="text-center">
          <p className={scoreClass}>{score.toFixed(0)}</p>
          <p className="text-gray-500 text-sm">{scoreLabel} Transparency</p>
        </div>
      </div>

      {breakdown && (
        <div className="space-y-3">
          <ScoreBar
            label="Financial Disclosure"
            score={breakdown.financial_disclosure}
            maxScore={30}
          />
          <ScoreBar
            label="Stock Disclosure"
            score={breakdown.stock_disclosure}
            maxScore={30}
          />
          <ScoreBar
            label="Vote Participation"
            score={breakdown.vote_participation}
            maxScore={20}
          />
          <ScoreBar
            label="Campaign Finance"
            score={breakdown.campaign_finance}
            maxScore={20}
          />
        </div>
      )}

      <p className="text-xs text-gray-400 mt-4">
        Score based on disclosure timeliness, voting participation, and reporting compliance.
      </p>
    </div>
  )
}

interface ScoreBarProps {
  label: string
  score: number
  maxScore: number
}

function ScoreBar({ label, score, maxScore }: ScoreBarProps) {
  const percentage = (score / maxScore) * 100

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="text-gray-900 font-medium">
          {score.toFixed(0)}/{maxScore}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={clsx('h-2 rounded-full', {
            'bg-green-500': percentage >= 70,
            'bg-yellow-500': percentage >= 40 && percentage < 70,
            'bg-red-500': percentage < 40,
          })}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
