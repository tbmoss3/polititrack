import { useState } from 'react'
import type { TransparencyBreakdown } from '../../api/types'
import clsx from 'clsx'

interface TransparencyScoreProps {
  score: number | null
  breakdown: TransparencyBreakdown | null
}

// Scoring methodology explanations
const SCORE_EXPLANATIONS = {
  stock_disclosure: {
    title: 'Stock Trade Disclosure Speed (30 pts)',
    description: 'How quickly stock trades are disclosed after the transaction.',
    criteria: [
      { label: '30 points', condition: 'Average disclosure within 30 days' },
      { label: '20 points', condition: 'Average disclosure within 45 days' },
      { label: '10 points', condition: 'Average disclosure within 60 days' },
      { label: '15 points', condition: 'No stock trades on record' },
    ],
    note: 'The STOCK Act requires disclosure within 45 days of a transaction.',
  },
  vote_participation: {
    title: 'Voting Participation (30 pts)',
    description: 'Percentage of votes where the member voted Yes or No.',
    criteria: [
      { label: 'Points = Rate x 30', condition: 'Based on participation rate' },
      { label: '15 points', condition: 'If no voting data available' },
    ],
    note: 'Higher participation indicates active engagement in legislative duties.',
  },
  campaign_finance: {
    title: 'Campaign Finance Reporting (20 pts)',
    description: 'Compliance with FEC campaign finance disclosure requirements.',
    criteria: [
      { label: '20 points', condition: 'Has FEC filings on record' },
      { label: '10 points', condition: 'No campaign finance data found' },
    ],
    note: 'Data sourced from the Federal Election Commission (FEC).',
  },
  financial_disclosure: {
    title: 'General Disclosure Compliance (20 pts)',
    description: 'Overall transparency based on available public information.',
    criteria: [
      { label: '5 points', condition: 'Has official website listed' },
      { label: '10 points', condition: 'Has stock trades or finance data' },
      { label: '5 points', condition: 'Base points for being in system' },
    ],
    note: 'Reflects overall accessibility of public information.',
  },
}

export default function TransparencyScore({ score, breakdown }: TransparencyScoreProps) {
  const [showExplanation, setShowExplanation] = useState(false)

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
            label="Stock Disclosure"
            score={breakdown.stock_disclosure}
            maxScore={30}
          />
          <ScoreBar
            label="Vote Participation"
            score={breakdown.vote_participation}
            maxScore={30}
          />
          <ScoreBar
            label="Campaign Finance"
            score={breakdown.campaign_finance}
            maxScore={20}
          />
          <ScoreBar
            label="Financial Disclosure"
            score={breakdown.financial_disclosure}
            maxScore={20}
          />
        </div>
      )}

      <button
        onClick={() => setShowExplanation(!showExplanation)}
        className="text-xs text-blue-600 hover:text-blue-800 mt-4 underline cursor-pointer w-full text-center"
      >
        {showExplanation ? 'Hide scoring methodology' : 'How is this score calculated?'}
      </button>

      {showExplanation && (
        <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
          <h4 className="font-medium text-gray-800 text-sm">Transparency Score Methodology</h4>
          <p className="text-xs text-gray-600">
            The score is calculated from 0-100 based on four categories of transparency metrics:
          </p>

          {Object.entries(SCORE_EXPLANATIONS).map(([key, explanation]) => (
            <div key={key} className="bg-gray-50 p-3 rounded-lg">
              <h5 className="font-medium text-gray-800 text-xs">{explanation.title}</h5>
              <p className="text-xs text-gray-600 mt-1">{explanation.description}</p>
              <ul className="mt-2 space-y-1">
                {explanation.criteria.map((criterion, idx) => (
                  <li key={idx} className="text-xs text-gray-600">
                    <span className="font-medium text-gray-700">{criterion.label}:</span> {criterion.condition}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-gray-500 italic mt-2">{explanation.note}</p>
            </div>
          ))}

          <p className="text-xs text-gray-500 text-center mt-3">
            Data sources: Congress.gov, FEC, Capitol Trades, and official government disclosure sites.
          </p>
        </div>
      )}
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
