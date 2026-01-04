import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import type { VotingSummary } from '../../api/types'

interface VotingHistoryProps {
  summary: VotingSummary | null
}

export default function VotingHistory({ summary }: VotingHistoryProps) {
  if (!summary) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Voting Record</h3>
        <p className="text-gray-500">No voting data available</p>
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
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Voting Record</h3>

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
