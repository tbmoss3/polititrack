import { useQuery } from '@tanstack/react-query'
import { getStatesAggregation } from '../api/politicians'
import USMap from '../components/Map/USMap'
import Loading from '../components/common/Loading'

export default function HomePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['statesAggregation'],
    queryFn: getStatesAggregation,
  })

  if (isLoading) {
    return <Loading message="Loading map data..." />
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load map data. Please try again.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Political Transparency Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Click on any state to view its representatives and senators
        </p>
      </div>

      <div className="card !p-0 overflow-hidden" style={{ height: '600px' }}>
        <USMap statesData={data?.states || []} />
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">🏛️</span>
            <div>
              <p className="text-2xl font-bold text-gray-900">535</p>
              <p className="text-sm text-gray-600">Congress Members</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">📊</span>
            <div>
              <p className="text-2xl font-bold text-gray-900">100</p>
              <p className="text-sm text-gray-600">Senators</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">🏠</span>
            <div>
              <p className="text-2xl font-bold text-gray-900">435</p>
              <p className="text-sm text-gray-600">Representatives</p>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">About This Project</h2>
        <p className="text-gray-600 leading-relaxed">
          PolitiTrack is an open-source platform that makes political data accessible to average voters.
          We aggregate data from official sources including the ProPublica Congress API, FEC campaign
          finance records, and House/Senate stock trade disclosures. Our transparency score helps you
          understand how promptly your representatives disclose their financial activities.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">Non-Partisan</span>
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">Open Source</span>
          <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">Updated Weekly</span>
        </div>
      </div>
    </div>
  )
}
