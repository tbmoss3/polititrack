import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPartyBreakdown } from '../../api/politicians'
import clsx from 'clsx'

export default function Sidebar() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentParty = searchParams.get('party')

  const { data: breakdown } = useQuery({
    queryKey: ['partyBreakdown'],
    queryFn: getPartyBreakdown,
  })

  const senate = breakdown?.senate || { D: 0, R: 0, I: 0 }
  const house = breakdown?.house || { D: 0, R: 0, I: 0 }

  const handlePartyFilter = (party: string | null) => {
    if (party) {
      navigate(`/search?party=${party}`)
    } else {
      navigate('/search')
    }
  }

  return (
    <aside className="hidden lg:block w-64 bg-white border-r border-gray-200 min-h-screen p-6">
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Congress Overview
          </h3>
          <div className="space-y-4">
            <div className="card !p-4">
              <h4 className="font-medium text-gray-700 mb-2">Senate</h4>
              <div className="flex items-center space-x-2 text-sm">
                <span className="party-badge party-badge-d">D: {senate.D ?? 0}</span>
                <span className="party-badge party-badge-r">R: {senate.R ?? 0}</span>
                <span className="party-badge party-badge-i">I: {senate.I ?? 0}</span>
              </div>
            </div>

            <div className="card !p-4">
              <h4 className="font-medium text-gray-700 mb-2">House</h4>
              <div className="flex items-center space-x-2 text-sm">
                <span className="party-badge party-badge-d">D: {house.D ?? 0}</span>
                <span className="party-badge party-badge-r">R: {house.R ?? 0}</span>
                <span className="party-badge party-badge-i">I: {house.I ?? 0}</span>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Quick Filters
          </h3>
          <div className="space-y-2">
            <button
              onClick={() => handlePartyFilter('R')}
              className={clsx(
                'w-full text-left px-3 py-2 text-sm rounded-md transition-colors',
                currentParty === 'R' ? 'bg-red-100 text-red-800' : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              🔴 Republicans
            </button>
            <button
              onClick={() => handlePartyFilter('D')}
              className={clsx(
                'w-full text-left px-3 py-2 text-sm rounded-md transition-colors',
                currentParty === 'D' ? 'bg-blue-100 text-blue-800' : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              🔵 Democrats
            </button>
            <button
              onClick={() => handlePartyFilter('I')}
              className={clsx(
                'w-full text-left px-3 py-2 text-sm rounded-md transition-colors',
                currentParty === 'I' ? 'bg-purple-100 text-purple-800' : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              🟣 Independents
            </button>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Resources
          </h3>
          <div className="space-y-2">
            <Link
              to="/about"
              className="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              About PolitiTrack
            </Link>
            <a
              href="https://github.com/tbmoss3/polititrack"
              target="_blank"
              rel="noopener noreferrer"
              className="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              GitHub Repository
            </a>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Data Sources
          </h3>
          <ul className="text-xs text-gray-500 space-y-1">
            <li>Congress.gov API</li>
            <li>FEC Campaign Finance</li>
            <li>Capitol Trades</li>
          </ul>
        </div>
      </div>
    </aside>
  )
}
