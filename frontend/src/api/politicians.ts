import { apiClient } from './client'
import type {
  Politician,
  PoliticianDetail,
  PoliticianListResponse,
  VoteListResponse,
  VotingSummary,
  CampaignFinance,
  TopDonor,
  StockTradeListResponse,
  StatesMapResponse,
  DistrictInfo,
} from './types'

// Politicians
export async function getPoliticians(params?: {
  state?: string
  party?: string
  chamber?: string
  page?: number
  page_size?: number
}): Promise<PoliticianListResponse> {
  const { data } = await apiClient.get('/politicians', { params })
  return data
}

export async function getPoliticiansByState(state: string): Promise<Politician[]> {
  const { data } = await apiClient.get(`/politicians/by-state/${state}`)
  return data
}

export async function getPolitician(id: string): Promise<PoliticianDetail> {
  const { data } = await apiClient.get(`/politicians/${id}`)
  return data
}

// Votes
export async function getPoliticianVotes(
  politicianId: string,
  params?: { page?: number; page_size?: number }
): Promise<VoteListResponse> {
  const { data } = await apiClient.get(`/votes/by-politician/${politicianId}`, { params })
  return data
}

export async function getVotingSummary(politicianId: string): Promise<VotingSummary> {
  const { data } = await apiClient.get(`/votes/summary/${politicianId}`)
  return data
}

// Finance
export async function getPoliticianFinance(politicianId: string): Promise<{
  items: CampaignFinance[]
  total_raised_all_cycles: number | null
  total_spent_all_cycles: number | null
}> {
  const { data } = await apiClient.get(`/finance/by-politician/${politicianId}`)
  return data
}

export async function getTopDonors(
  politicianId: string,
  params?: { cycle?: number; limit?: number }
): Promise<{ items: TopDonor[]; cycle: number; total: number }> {
  const { data } = await apiClient.get(`/finance/donors/${politicianId}`, { params })
  return data
}

// Stock Trades
export async function getPoliticianStockTrades(
  politicianId: string,
  params?: { page?: number; page_size?: number }
): Promise<StockTradeListResponse> {
  const { data } = await apiClient.get(`/stocks/by-politician/${politicianId}`, { params })
  return data
}

// Map Data
export async function getStatesAggregation(): Promise<StatesMapResponse> {
  const { data } = await apiClient.get('/map/states')
  return data
}

export async function getStateDistricts(state: string): Promise<{
  state: string
  districts: DistrictInfo[]
  senators: Array<{
    id: string
    name: string
    party: string | null
    transparency_score: number | null
  }>
}> {
  const { data } = await apiClient.get(`/map/districts/${state}`)
  return data
}

export async function getPartyBreakdown(): Promise<{
  house: { D: number; R: number; I: number }
  senate: { D: number; R: number; I: number }
  total: { D: number; R: number; I: number }
}> {
  const { data } = await apiClient.get('/map/party-breakdown')
  return data
}
