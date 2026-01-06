import { Link } from 'react-router-dom'

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">About PolitiTrack</h1>
        <p className="text-gray-600 mt-2">
          Making political transparency accessible to everyone
        </p>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Our Mission</h2>
        <p className="text-gray-600 leading-relaxed">
          PolitiTrack is an open-source, non-partisan platform that aggregates publicly available data
          about members of the United States Congress. Our goal is to make political transparency
          accessible to average voters by presenting complex government data in an easy-to-understand format.
        </p>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Data Sources</h2>
        <div className="space-y-4">
          <div className="border-l-4 border-blue-500 pl-4">
            <h3 className="font-medium text-gray-800">Congress.gov API</h3>
            <p className="text-sm text-gray-600">
              Official source for member information, voting records, and sponsored legislation.
              Data is updated regularly to reflect the latest congressional activity.
            </p>
            <a
              href="https://api.congress.gov"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline"
            >
              api.congress.gov
            </a>
          </div>

          <div className="border-l-4 border-green-500 pl-4">
            <h3 className="font-medium text-gray-800">Federal Election Commission (FEC)</h3>
            <p className="text-sm text-gray-600">
              Campaign finance data including contributions, expenditures, and donor information.
              All candidates for federal office are required to file these reports.
            </p>
            <a
              href="https://www.fec.gov/data/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline"
            >
              fec.gov/data
            </a>
          </div>

          <div className="border-l-4 border-purple-500 pl-4">
            <h3 className="font-medium text-gray-800">Capitol Trades</h3>
            <p className="text-sm text-gray-600">
              Aggregated stock trading data from congressional financial disclosures.
              The STOCK Act requires members to disclose trades within 45 days.
            </p>
            <a
              href="https://www.capitoltrades.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline"
            >
              capitoltrades.com
            </a>
          </div>

          <div className="border-l-4 border-orange-500 pl-4">
            <h3 className="font-medium text-gray-800">Official Disclosure Sites</h3>
            <p className="text-sm text-gray-600">
              Financial disclosures from the House Clerk and Senate Office of Public Records
              contain annual reports on assets, liabilities, and outside income.
            </p>
            <div className="flex gap-4 mt-1">
              <a
                href="https://disclosures-clerk.house.gov"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline"
              >
                House Disclosures
              </a>
              <a
                href="https://efdsearch.senate.gov"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline"
              >
                Senate Disclosures
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Transparency Score</h2>
        <p className="text-gray-600 mb-4">
          Our transparency score (0-100) is calculated based on four categories:
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-gray-800">Stock Disclosure Speed (30 pts)</h3>
            <p className="text-sm text-gray-600">
              How quickly stock trades are disclosed. The STOCK Act requires 45-day disclosure.
            </p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-gray-800">Vote Participation (30 pts)</h3>
            <p className="text-sm text-gray-600">
              Percentage of votes where the member cast a yes or no vote.
            </p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-gray-800">Campaign Finance (20 pts)</h3>
            <p className="text-sm text-gray-600">
              Whether FEC campaign finance filings are available.
            </p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-gray-800">Financial Disclosure (20 pts)</h3>
            <p className="text-sm text-gray-600">
              General availability of financial information and disclosures.
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Open Source</h2>
        <p className="text-gray-600 mb-4">
          PolitiTrack is fully open source. We believe transparency tools should themselves be transparent.
          You can view our code, report issues, or contribute on GitHub.
        </p>
        <a
          href="https://github.com/tbmoss3/polititrack"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary inline-block"
        >
          View on GitHub
        </a>
      </div>

      <div className="card bg-yellow-50 border-yellow-200">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Disclaimer</h2>
        <p className="text-gray-600 text-sm">
          PolitiTrack is a non-partisan educational tool. We do not endorse any candidate, party, or political position.
          All data is sourced from official government records and third-party aggregators. While we strive for accuracy,
          we recommend verifying important information through official sources. This project is not affiliated with
          the U.S. government.
        </p>
      </div>

      <div className="text-center py-4">
        <Link to="/" className="text-blue-600 hover:text-blue-800 hover:underline">
          ← Back to Map
        </Link>
      </div>
    </div>
  )
}
