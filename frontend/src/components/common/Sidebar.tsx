import { useQuery } from '@tanstack/react-query'
import { getPartyBreakdown } from '../../api/politicians'

export default function Sidebar() {
  const { data: breakdown } = useQuery({
    queryKey: ['partyBreakdown'],
    queryFn: getPartyBreakdown,
  })

  return (
    <aside className="hidden lg:block w-64 bg-white border-r border-gray-200 min-h-screen p-6">
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Congress Overview
          </h3>
          {breakdown && (
            <div className="space-y-4">
              <div className="card !p-4">
                <h4 className="font-medium text-gray-700 mb-2">Senate</h4>
                <div className="flex items-center space-x-2 text-sm">
                  <span className="party-badge party-badge-d">D: {breakdown.senate.D}</span>
                  <span className="party-badge party-badge-r">R: {breakdown.senate.R}</span>
                  <span className="party-badge party-badge-i">I: {breakdown.senate.I}</span>
                </div>
              </div>

              <div className="card !p-4">
                <h4 className="font-medium text-gray-700 mb-2">House</h4>
                <div className="flex items-center space-x-2 text-sm">
                  <span className="party-badge party-badge-d">D: {breakdown.house.D}</span>
                  <span className="party-badge party-badge-r">R: {breakdown.house.R}</span>
                  <span className="party-badge party-badge-i">I: {breakdown.house.I}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Quick Filters
          </h3>
          <div className="space-y-2">
            <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors">
              🔴 Republicans
            </button>
            <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors">
              🔵 Democrats
            </button>
            <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors">
              🟣 Independents
            </button>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Data Sources
          </h3>
          <ul className="text-xs text-gray-500 space-y-1">
            <li>ProPublica Congress API</li>
            <li>FEC Campaign Finance</li>
            <li>House/Senate Stock Watcher</li>
          </ul>
        </div>
      </div>
    </aside>
  )
}
