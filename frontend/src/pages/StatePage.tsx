import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPoliticiansByState, getStateDistricts } from '../api/politicians'
import PoliticianList from '../components/Politicians/PoliticianList'
import Loading from '../components/common/Loading'

// Full state names
const STATE_NAMES: Record<string, string> = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
  CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
  HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa',
  KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland',
  MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri',
  MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey',
  NM: 'New Mexico', NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio',
  OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
  SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont',
  VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming',
  DC: 'District of Columbia',
}

export default function StatePage() {
  const { stateCode } = useParams<{ stateCode: string }>()
  const state = stateCode?.toUpperCase() || ''

  const { data: politicians, isLoading: loadingPoliticians } = useQuery({
    queryKey: ['politicians', state],
    queryFn: () => getPoliticiansByState(state),
    enabled: !!state,
  })

  const { data: districtData, isLoading: loadingDistricts } = useQuery({
    queryKey: ['districts', state],
    queryFn: () => getStateDistricts(state),
    enabled: !!state,
  })

  if (loadingPoliticians || loadingDistricts) {
    return <Loading message={`Loading ${STATE_NAMES[state] || state} data...`} />
  }

  const senators = politicians?.filter(p => p.chamber === 'senate') || []
  const representatives = politicians?.filter(p => p.chamber === 'house') || []

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <Link to="/" className="text-blue-600 hover:text-blue-800">
          ← Back to Map
        </Link>
      </div>

      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          {STATE_NAMES[state] || state}
        </h1>
        <p className="text-gray-600 mt-2">
          {senators.length} Senators • {representatives.length} Representatives
        </p>
      </div>

      {/* Senators Section */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
          <span className="mr-2">🏛️</span> Senators
        </h2>
        {senators.length > 0 ? (
          <PoliticianList politicians={senators} />
        ) : (
          <p className="text-gray-500">No senator data available</p>
        )}
      </div>

      {/* Representatives Section */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
          <span className="mr-2">🏠</span> Representatives
        </h2>
        {representatives.length > 0 ? (
          <PoliticianList politicians={representatives} />
        ) : (
          <p className="text-gray-500">No representative data available</p>
        )}
      </div>

      {/* Districts Overview */}
      {districtData && districtData.districts.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Congressional Districts
          </h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {districtData.districts.map((district) => (
              <Link
                key={`${district.state}-${district.district}`}
                to={`/politician/${district.representative_id}`}
                className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <p className="font-semibold text-gray-900">
                  District {district.district}
                </p>
                <p className="text-sm text-gray-600">
                  {district.representative_name || 'Vacant'}
                </p>
                <div className="flex items-center justify-between mt-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      district.party === 'D'
                        ? 'bg-blue-100 text-blue-800'
                        : district.party === 'R'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {district.party || 'N/A'}
                  </span>
                  {district.transparency_score !== null && (
                    <span className="text-xs text-gray-500">
                      Score: {district.transparency_score.toFixed(0)}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
