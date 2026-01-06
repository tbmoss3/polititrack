import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface NetWorthChartProps {
  disclosureUrl?: string
  capitolTradesUrl?: string
  fullName?: string
}

export default function NetWorthChart({ disclosureUrl, capitolTradesUrl, fullName }: NetWorthChartProps) {
  // Placeholder data - in future this would come from parsed disclosure PDFs
  // Net worth data requires manual extraction from annual financial disclosures
  const hasData = false

  // Example data structure for when we have real data
  const sampleData = [
    { year: '2020', netWorth: 1200000 },
    { year: '2021', netWorth: 1450000 },
    { year: '2022', netWorth: 1380000 },
    { year: '2023', netWorth: 1620000 },
    { year: '2024', netWorth: 1850000 },
  ]

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`
    }
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`
    }
    return `$${value}`
  }

  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Financial Disclosures</h3>
        {disclosureUrl && (
          <a
            href={disclosureUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            View Official Filings
          </a>
        )}
      </div>

      {hasData ? (
        <>
          <div className="h-48 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sampleData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis tickFormatter={formatCurrency} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Line
                  type="monotone"
                  dataKey="netWorth"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6' }}
                  name="Estimated Net Worth"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-gray-500 text-center">
            Estimated from annual financial disclosure reports
          </p>
        </>
      ) : (
        <div className="text-center py-8">
          <p className="text-gray-500 mb-4">
            Net worth data is compiled from annual financial disclosure reports filed with Congress.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {disclosureUrl && (
              <a
                href={disclosureUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary text-sm"
              >
                View Financial Disclosures
              </a>
            )}
            {capitolTradesUrl && (
              <a
                href={capitolTradesUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-sm"
              >
                View Stock Trades on Capitol Trades
              </a>
            )}
          </div>
        </div>
      )}

      <div className="mt-4 pt-4 border-t">
        <h4 className="font-medium text-gray-700 mb-2 text-sm">About Financial Disclosures</h4>
        <p className="text-xs text-gray-500">
          Members of Congress are required to file annual financial disclosure reports under the Ethics in Government Act.
          These reports include assets, liabilities, income sources, and transactions over $1,000.
          The STOCK Act of 2012 requires disclosure of stock trades within 45 days.
        </p>
      </div>
    </div>
  )
}
