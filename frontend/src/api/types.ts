// API Response Types

export interface Politician {
  id: string
  bioguide_id: string
  first_name: string
  last_name: string
  party: string | null
  state: string
  district: number | null
  chamber: 'house' | 'senate'
  in_office: boolean
  twitter_handle: string | null
  website_url: string | null
  photo_url: string | null
  transparency_score: number | null
  full_name: string
  title: string
  created_at: string
  updated_at: string
}

export interface PoliticianDetail extends Politician {
  transparency_breakdown: TransparencyBreakdown | null
  total_votes: number
  total_bills_sponsored: number
  vote_participation_rate: number | null
  latest_stock_trade_date: string | null
  total_stock_trades: number
}

export interface TransparencyBreakdown {
  financial_disclosure: number
  stock_disclosure: number
  vote_participation: number
  campaign_finance: number
  total_score: number
}

export interface PoliticianListResponse {
  items: Politician[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface Bill {
  id: string
  bill_id: string
  congress: number
  title: string
  summary_official: string | null
  summary_ai: string | null
  sponsor_id: string | null
  introduced_date: string | null
  latest_action: string | null
  latest_action_date: string | null
  subjects: string[] | null
  created_at: string
  updated_at: string
}

export interface Vote {
  id: string
  vote_id: string
  vote_position: 'yes' | 'no' | 'not_voting' | 'present'
  vote_date: string
  chamber: string
  question: string | null
  result: string | null
  bill_id: string | null
  politician_id: string
  bill: {
    id: string
    bill_id: string
    title: string
    summary_ai: string | null
  } | null
}

export interface VoteListResponse {
  items: Vote[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface VotingSummary {
  total_votes: number
  yes_votes: number
  no_votes: number
  not_voting: number
  present: number
  participation_rate: number
}

export interface CampaignFinance {
  id: string
  politician_id: string
  cycle: number
  total_raised: number | null
  total_spent: number | null
  cash_on_hand: number | null
  total_from_pacs: number | null
  total_from_individuals: number | null
  last_filed: string | null
  pac_percentage: number | null
}

export interface TopDonor {
  id: string
  politician_id: string
  cycle: number
  donor_name: string
  donor_type: string | null
  total_amount: number | null
}

export interface StockTrade {
  id: string
  politician_id: string
  transaction_date: string
  disclosure_date: string
  ticker: string | null
  asset_description: string | null
  transaction_type: 'purchase' | 'sale' | 'exchange' | null
  amount_range: string | null
  amount_min: number | null
  amount_max: number | null
  filing_url: string | null
  disclosure_delay_days: number
  amount_midpoint: number | null
}

export interface StockTradeListResponse {
  items: StockTrade[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface StateAggregation {
  state: string
  total_politicians: number
  democrats: number
  republicans: number
  independents: number
  avg_transparency_score: number | null
  senators: number
  representatives: number
}

export interface StatesMapResponse {
  states: StateAggregation[]
}

export interface DistrictInfo {
  state: string
  district: number
  representative_id: string | null
  representative_name: string | null
  party: string | null
  transparency_score: number | null
}
