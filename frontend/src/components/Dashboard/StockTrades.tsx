import { format } from 'date-fns'
import type { StockTrade } from '../../api/types'
import clsx from 'clsx'

interface StockTradesProps {
  trades: StockTrade[]
  total: number
}

export default function StockTrades({ trades, total }: StockTradesProps) {
  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Recent Stock Trades</h3>
        <span className="text-sm text-gray-500">{total} total trades</span>
      </div>

      {trades.length === 0 ? (
        <p className="text-gray-500">No stock trade data available</p>
      ) : (
        <div className="space-y-3">
          {trades.slice(0, 10).map((trade) => (
            <TradeRow key={trade.id} trade={trade} />
          ))}
        </div>
      )}
    </div>
  )
}

interface TradeRowProps {
  trade: StockTrade
}

function TradeRow({ trade }: TradeRowProps) {
  const typeClass = clsx('text-xs font-medium px-2 py-0.5 rounded', {
    'bg-green-100 text-green-800': trade.transaction_type === 'purchase',
    'bg-red-100 text-red-800': trade.transaction_type === 'sale',
    'bg-gray-100 text-gray-800': trade.transaction_type === 'exchange',
  })

  const delayClass = clsx('text-xs', {
    'text-green-600': trade.disclosure_delay_days <= 30,
    'text-yellow-600': trade.disclosure_delay_days > 30 && trade.disclosure_delay_days <= 45,
    'text-red-600': trade.disclosure_delay_days > 45,
  })

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          {trade.ticker ? (
            <span className="font-mono font-semibold text-gray-900">{trade.ticker}</span>
          ) : (
            <span className="text-gray-500 italic">No ticker</span>
          )}
          <span className={typeClass}>
            {trade.transaction_type?.toUpperCase() || 'N/A'}
          </span>
        </div>
        <p className="text-sm text-gray-600 truncate mt-1">
          {trade.asset_description || 'No description'}
        </p>
        <p className="text-xs text-gray-400 mt-1">
          {format(new Date(trade.transaction_date), 'MMM d, yyyy')}
        </p>
      </div>

      <div className="text-right ml-4">
        <p className="text-sm font-medium text-gray-900">{trade.amount_range || 'N/A'}</p>
        <p className={delayClass}>
          Disclosed in {trade.disclosure_delay_days} days
        </p>
        {trade.filing_url && (
          <a
            href={trade.filing_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline"
          >
            View Filing →
          </a>
        )}
      </div>
    </div>
  )
}
