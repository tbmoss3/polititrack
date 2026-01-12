import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  getPolitician,
  getVotingSummary,
  getPoliticianVotes,
  getPoliticianFinance,
  getTopDonors,
} from '../api/politicians'
import TransparencyScore from '../components/Dashboard/TransparencyScore'
import VotingHistory from '../components/Dashboard/VotingHistory'
import FinanceChart from '../components/Dashboard/FinanceChart'
import Loading from '../components/common/Loading'
import { getPartyBadgeClass, getPartyName } from '../utils'

export default function PoliticianPage() {
  const { id } = useParams<{ id: string }>()

  const { data: politician, isLoading: loadingPolitician } = useQuery({
    queryKey: ['politician', id],
    queryFn: () => getPolitician(id!),
    enabled: !!id,
  })

  const { data: votingSummary } = useQuery({
    queryKey: ['votingSummary', id],
    queryFn: () => getVotingSummary(id!),
    enabled: !!id,
  })

  const { data: votesData } = useQuery({
    queryKey: ['votes', id],
    queryFn: () => getPoliticianVotes(id!, { page_size: 10 }),
    enabled: !!id,
  })

  const { data: financeData } = useQuery({
    queryKey: ['finance', id],
    queryFn: () => getPoliticianFinance(id!),
    enabled: !!id,
  })

  const { data: donorsData } = useQuery({
    queryKey: ['donors', id],
    queryFn: () => getTopDonors(id!),
    enabled: !!id,
  })

  if (loadingPolitician) {
    return <Loading message="Loading politician data..." />
  }

  if (!politician) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Politician not found</p>
        <Link to="/" className="text-blue-600 hover:underline mt-4 inline-block">
          Return to Map
        </Link>
      </div>
    )
  }

  const partyClass = getPartyBadgeClass(politician.party, 'text-lg')

  return (
    <div className="space-y-6">
      <Link to={`/state/${politician.state}`} className="text-blue-600 hover:text-blue-800">
        ← Back to {politician.state}
      </Link>

      {/* Header */}
      <div className="card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center text-3xl">
              {politician.chamber === 'senate' ? '🏛️' : '🏠'}
            </div>
            <div>
              <div className="flex items-center space-x-3">
                <h1 className="text-3xl font-bold text-gray-900">{politician.full_name}</h1>
                <span className={partyClass}>{politician.party}</span>
              </div>
              <p className="text-lg text-gray-600">
                {politician.title} • {politician.state}
                {politician.district && ` District ${politician.district}`}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {getPartyName(politician.party)} • {politician.chamber === 'senate' ? 'U.S. Senate' : 'U.S. House of Representatives'}
              </p>
            </div>
          </div>

          <div className="mt-4 md:mt-0 flex flex-wrap gap-2">
            {politician.website_url && (
              <a
                href={politician.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-sm"
              >
                🌐 Website
              </a>
            )}
            {politician.twitter_handle && (
              <a
                href={`https://twitter.com/${politician.twitter_handle}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-sm"
              >
                𝕏 @{politician.twitter_handle}
              </a>
            )}
            {politician.official_disclosures && (
              <>
                <a
                  href={politician.official_disclosures.capitol_trades_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary text-sm"
                >
                  📈 Stock Trades
                </a>
                <a
                  href={politician.official_disclosures.financial_disclosure_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary text-sm"
                >
                  📄 Official Filings
                </a>
              </>
            )}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">{politician.total_votes}</p>
            <p className="text-sm text-gray-500">Total Votes</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">{politician.total_bills_sponsored}</p>
            <p className="text-sm text-gray-500">Bills Sponsored</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">
              {politician.vote_participation_rate?.toFixed(0) || 'N/A'}%
            </p>
            <p className="text-sm text-gray-500">Vote Participation</p>
          </div>
        </div>
      </div>

      {/* Dashboard Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        <TransparencyScore
          score={politician.transparency_score ? Number(politician.transparency_score) : null}
          breakdown={politician.transparency_breakdown}
        />

        <VotingHistory
          summary={votingSummary || null}
          votes={votesData?.items || []}
          bioguideId={politician.bioguide_id}
          fullName={politician.full_name}
        />

        <FinanceChart
          finances={financeData?.items || []}
          topDonors={donorsData?.items || []}
          fullName={politician.full_name}
        />
      </div>

      {/* Disclaimer */}
      <div className="card bg-gray-50">
        <p className="text-xs text-gray-500 text-center">
          Data sourced from Congress.gov API, FEC, and Capitol Trades.
          Last updated: {new Date(politician.updated_at).toLocaleDateString()}.
          This is a non-partisan transparency tool.
        </p>
      </div>
    </div>
  )
}
