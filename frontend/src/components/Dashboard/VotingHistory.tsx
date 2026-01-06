import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import type { VotingSummary, Vote } from '../../api/types'
import clsx from 'clsx'

interface VotingHistoryProps {
  summary: VotingSummary | null
  votes?: Vote[]
  bioguideId?: string
  fullName?: string
}

export default function VotingHistory({ summary, votes = [], bioguideId, fullName }: VotingHistoryProps) {
  // Congress.gov URL for member's votes
  const congressGovUrl = bioguideId
    ? `https://www.congress.gov/member/${fullName?.toLowerCase().replace(/\s+/g, '-') || 'member'}/${bioguideId}?q=%7B%22bill-status%22%3A%22floor-vote%22%7D`
    : 'https://www.congress.gov/members'

  if (!summary || summary.total_votes === 0) {
    return (
      <div className="card">
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Voting Record</h3>
          <a
            href={congressGovUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            View on Congress.gov
          </a>
        </div>
        <p className="text-gray-500">No voting data available yet. Check Congress.gov for the latest records.</p>
      </div>
    )
  }

  const data = [
    { name: 'Yes', value: summary.yes_votes, color: '#22c55e' },
    { name: 'No', value: summary.no_votes, color: '#ef4444' },
    { name: 'Not Voting', value: summary.not_voting, color: '#6b7280' },
    { name: 'Present', value: summary.present, color: '#3b82f6' },
  ].filter(d => d.value > 0)

  const getPositionStyle = (position: string) => {
    return clsx('px-2 py-0.5 rounded text-xs font-medium', {
      'bg-green-100 text-green-800': position === 'yes',
      'bg-red-100 text-red-800': position === 'no',
      'bg-gray-100 text-gray-800': position === 'not_voting',
      'bg-blue-100 text-blue-800': position === 'present',
    })
  }

  const formatPosition = (position: string) => {
    return position === 'not_voting' ? 'Not Voting' : position.charAt(0).toUpperCase() + position.slice(1)
  }

  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Voting Record</h3>
        <a
          href={congressGovUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          View all votes on Congress.gov
        </a>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <p className="text-2xl font-bold text-gray-900">{summary.total_votes}</p>
          <p className="text-sm text-gray-500">Total Votes</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <p className="text-2xl font-bold text-green-600">
            {summary.participation_rate.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-500">Participation</p>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={70}
              paddingAngle={5}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [value, 'Votes']}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-4 gap-2 mt-2 text-center text-xs">
        <div>
          <p className="font-semibold text-green-600">{summary.yes_votes}</p>
          <p className="text-gray-500">Yes</p>
        </div>
        <div>
          <p className="font-semibold text-red-600">{summary.no_votes}</p>
          <p className="text-gray-500">No</p>
        </div>
        <div>
          <p className="font-semibold text-gray-600">{summary.not_voting}</p>
          <p className="text-gray-500">Not Voting</p>
        </div>
        <div>
          <p className="font-semibold text-blue-600">{summary.present}</p>
          <p className="text-gray-500">Present</p>
        </div>
      </div>

      {/* Recent Votes List */}
      {votes.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <h4 className="font-medium text-gray-700 mb-3">Recent Votes</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {votes.slice(0, 10).map((vote) => (
              <div
                key={vote.id}
                className="p-3 bg-gray-50 rounded text-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0 mr-2">
                    {vote.bill ? (
                      <a
                        href={`https://www.congress.gov/bill/119th-congress/${vote.bill.bill_id.replace(/(\d+)-\d+$/, '$1')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                        title={vote.bill.title}
                      >
                        {vote.bill.bill_id.split('-')[0].toUpperCase()}
                      </a>
                    ) : (
                      <p className="text-gray-900 font-medium truncate" title={vote.question || 'Vote'}>
                        {vote.question || 'Vote'}
                      </p>
                    )}
                  </div>
                  <span className={getPositionStyle(vote.vote_position)}>
                    {formatPosition(vote.vote_position)}
                  </span>
                </div>
                {vote.bill && (
                  <p className="text-gray-700 text-xs mt-1 line-clamp-2">
                    {vote.bill.title}
                  </p>
                )}
                {vote.bill?.summary_ai && (
                  <p className="text-gray-500 text-xs mt-1 line-clamp-2 italic">
                    {vote.bill.summary_ai}
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(vote.vote_date).toLocaleDateString()} • {vote.result || 'Pending'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
