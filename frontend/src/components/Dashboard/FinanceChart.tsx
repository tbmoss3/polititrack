import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { CampaignFinance, TopDonor } from '../../api/types'

interface FinanceChartProps {
  finances: CampaignFinance[]
  topDonors: TopDonor[]
}

export default function FinanceChart({ finances, topDonors }: FinanceChartProps) {
  // Format currency
  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`
    }
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`
    }
    return `$${value}`
  }

  // Prepare chart data
  const chartData = finances
    .sort((a, b) => a.cycle - b.cycle)
    .map((f) => ({
      cycle: f.cycle.toString(),
      raised: f.total_raised || 0,
      spent: f.total_spent || 0,
      pacs: f.total_from_pacs || 0,
      individuals: f.total_from_individuals || 0,
    }))

  const currentFinance = finances[0]

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Campaign Finance</h3>

      {currentFinance && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <p className="text-xl font-bold text-blue-700">
              {formatCurrency(currentFinance.total_raised || 0)}
            </p>
            <p className="text-xs text-gray-600">Total Raised</p>
          </div>
          <div className="text-center p-3 bg-red-50 rounded-lg">
            <p className="text-xl font-bold text-red-700">
              {formatCurrency(currentFinance.total_spent || 0)}
            </p>
            <p className="text-xs text-gray-600">Total Spent</p>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <p className="text-xl font-bold text-green-700">
              {formatCurrency(currentFinance.cash_on_hand || 0)}
            </p>
            <p className="text-xs text-gray-600">Cash on Hand</p>
          </div>
        </div>
      )}

      {chartData.length > 0 && (
        <div className="h-64 mb-6">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="cycle" />
              <YAxis tickFormatter={formatCurrency} />
              <Tooltip
                formatter={(value: number) => formatCurrency(value)}
              />
              <Legend />
              <Bar dataKey="raised" name="Raised" fill="#3b82f6" />
              <Bar dataKey="spent" name="Spent" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {topDonors.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-3">Top Donors</h4>
          <div className="space-y-2">
            {topDonors.slice(0, 5).map((donor) => (
              <div
                key={donor.id}
                className="flex justify-between items-center p-2 bg-gray-50 rounded"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {donor.donor_name}
                  </p>
                  <p className="text-xs text-gray-500 capitalize">
                    {donor.donor_type || 'Unknown'}
                  </p>
                </div>
                <p className="text-sm font-semibold text-gray-900 ml-4">
                  {formatCurrency(donor.total_amount || 0)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {finances.length === 0 && topDonors.length === 0 && (
        <p className="text-gray-500">No campaign finance data available</p>
      )}
    </div>
  )
}
