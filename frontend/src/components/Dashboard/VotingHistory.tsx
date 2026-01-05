import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import type { VotingSummary } from '../../api/types'

interface VotingHistoryProps {
  summary: VotingSummary | null
  bioguideId?: string
  fullName?: string
}

export default function VotingHistory({ summary, bioguideId, fullName }: VotingHistoryProps) {
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

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
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

      <div className="grid grid-cols-4 gap-2 mt-4 text-center text-xs">
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
    </div>
  )
}
