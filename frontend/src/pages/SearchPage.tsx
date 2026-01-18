import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listPoliticians } from '../api/politicians'
import Loading from '../components/common/Loading'
import clsx from 'clsx'

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const party = searchParams.get('party')
  const chamber = searchParams.get('chamber')
  const state = searchParams.get('state')
  const q = searchParams.get('q')
  const page = parseInt(searchParams.get('page') || '1')

  const { data, isLoading } = useQuery({
    queryKey: ['politicians', { party, chamber, state, q, page }],
    queryFn: () => listPoliticians({
      party: party || undefined,
      chamber: chamber || undefined,
      state: state || undefined,
      q: q || undefined,
      page,
      page_size: 50
    }),
  })

  const partyLabels: Record<string, string> = {
    D: 'Democrats',
    R: 'Republicans',
    I: 'Independents',
  }

  const handleFilterChange = (key: string, value: string | null) => {
    const newParams = new URLSearchParams(searchParams)
    if (value) {
      newParams.set(key, value)
    } else {
      newParams.delete(key)
    }
    newParams.set('page', '1')
    setSearchParams(newParams)
  }

  if (isLoading) {
    return <Loading message="Loading politicians..." />
  }

  const getTitle = () => {
    if (q) return `Search: "${q}"`
    if (party) return partyLabels[party] || 'All Politicians'
    return 'All Politicians'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          {getTitle()}
        </h1>
        <p className="text-gray-600 mt-2">
          {data?.total || 0} members found
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Party</label>
            <select
              value={party || ''}
              onChange={(e) => handleFilterChange('party', e.target.value || null)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Parties</option>
              <option value="D">Democrats</option>
              <option value="R">Republicans</option>
              <option value="I">Independents</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Chamber</label>
            <select
              value={chamber || ''}
              onChange={(e) => handleFilterChange('chamber', e.target.value || null)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Chambers</option>
              <option value="senate">Senate</option>
              <option value="house">House</option>
            </select>
          </div>

          {(party || chamber || state || q) && (
            <div className="flex items-end">
              <button
                onClick={() => setSearchParams({})}
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                Clear {q ? 'search' : 'filters'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.items.map((politician) => (
          <Link
            key={politician.id}
            to={`/politician/${politician.id}`}
            className="card hover:shadow-md transition-shadow"
          >
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center text-xl">
                {politician.chamber === 'senate' ? '🏛️' : '🏠'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <h3 className="font-semibold text-gray-900 truncate">{politician.full_name}</h3>
                  <span
                    className={clsx('party-badge text-xs', {
                      'party-badge-d': politician.party === 'D',
                      'party-badge-r': politician.party === 'R',
                      'party-badge-i': politician.party === 'I' || politician.party === 'ID',
                    })}
                  >
                    {politician.party}
                  </span>
                </div>
                <p className="text-sm text-gray-600">
                  {politician.title} - {politician.state}
                  {politician.district && ` District ${politician.district}`}
                </p>
                {politician.transparency_score && (
                  <p className="text-xs text-gray-500 mt-1">
                    Transparency Score: {politician.transparency_score.toFixed(0)}
                  </p>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex justify-center space-x-2">
          <button
            onClick={() => handleFilterChange('page', String(page - 1))}
            disabled={page <= 1}
            className={clsx(
              'px-4 py-2 rounded-md text-sm',
              page <= 1 ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            )}
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Page {page} of {data.total_pages}
          </span>
          <button
            onClick={() => handleFilterChange('page', String(page + 1))}
            disabled={page >= data.total_pages}
            className={clsx(
              'px-4 py-2 rounded-md text-sm',
              page >= data.total_pages ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            )}
          >
            Next
          </button>
        </div>
      )}

      {data?.items.length === 0 && (
        <div className="card text-center py-8">
          <p className="text-gray-500">No politicians found matching your criteria.</p>
          <button
            onClick={() => setSearchParams({})}
            className="text-blue-600 hover:underline mt-2"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  )
}
