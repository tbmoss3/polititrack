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
  fullName?: string
}

export default function FinanceChart({ finances, topDonors, fullName }: FinanceChartProps) {
  // FEC URL for candidate search
  const fecUrl = fullName
    ? `https://www.fec.gov/data/candidates/?q=${encodeURIComponent(fullName)}&is_active_candidate=true`
    : 'https://www.fec.gov/data/candidates/'

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
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Campaign Finance</h3>
        <a
          href={fecUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          View on FEC.gov
        </a>
      </div>

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
        <p className="text-gray-500">No campaign finance data available yet. Check the FEC website for the latest filings.</p>
      )}

      {/* PAC vs Individual breakdown for current cycle */}
      {currentFinance && (currentFinance.total_from_pacs || currentFinance.total_from_individuals) && (
        <div className="mt-4 pt-4 border-t">
          <h4 className="font-medium text-gray-700 mb-3">Funding Sources</h4>
          <div className="flex gap-4">
            <div className="flex-1 p-3 bg-purple-50 rounded-lg text-center">
              <p className="text-lg font-bold text-purple-700">
                {currentFinance.pac_percentage?.toFixed(0) || 0}%
              </p>
              <p className="text-xs text-gray-600">From PACs</p>
            </div>
            <div className="flex-1 p-3 bg-teal-50 rounded-lg text-center">
              <p className="text-lg font-bold text-teal-700">
                {currentFinance.total_from_individuals && currentFinance.total_raised
                  ? ((currentFinance.total_from_individuals / currentFinance.total_raised) * 100).toFixed(0)
                  : 0}%
              </p>
              <p className="text-xs text-gray-600">From Individuals</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
