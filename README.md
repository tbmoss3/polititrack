# PolitiTrack 🏛️

**Political Transparency Platform** - Making complex political data accessible to average voters.

[![CI](https://github.com/yourusername/polititrack/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/polititrack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

PolitiTrack is an open-source, non-partisan web application that provides accessible political transparency data through an interactive U.S. map interface. The platform aggregates data from official sources to help voters understand their representatives' voting records, campaign finances, and stock trades.

### Features

- 🗺️ **Interactive US Map** - Drill down from national → state → district level
- 👤 **Politician Profiles** - Comprehensive data on all 535 Congress members
- 📊 **Voting Records** - Historical voting data with AI-generated bill summaries
- 💰 **Campaign Finance** - FEC data on fundraising, spending, and top donors
- 📈 **Stock Trades** - Financial disclosures from House and Senate Stock Watcher
- ⭐ **Transparency Score** - Calculated metric based on disclosure timeliness

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy |
| Database | PostgreSQL 16 |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Map | Mapbox GL JS |
| Background Tasks | Celery, Redis |
| Deployment | Railway.app, Docker |
| CI/CD | GitHub Actions |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16+ (or use Docker)

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/yourusername/polititrack.git
cd polititrack

# Copy environment files
cp backend/.env.example backend/.env

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/api/docs
```

### Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Environment Variables

### Required API Keys

| Variable | Source | Description |
|----------|--------|-------------|
| `PROPUBLICA_API_KEY` | [ProPublica](https://www.propublica.org/datastore/api/propublica-congress-api) | Congress members, votes, bills |
| `FEC_API_KEY` | [FEC API](https://api.data.gov/signup/) | Campaign finance data |
| `OPENAI_API_KEY` | [OpenAI](https://platform.openai.com/api-keys) | Bill summarization (or use Anthropic) |
| `MAPBOX_ACCESS_TOKEN` | [Mapbox](https://account.mapbox.com/access-tokens/) | Interactive maps |

## Data Sources

| Source | Data Provided | Update Frequency |
|--------|---------------|------------------|
| [ProPublica Congress API](https://www.propublica.org/datastore/api/propublica-congress-api) | Members, votes, bills | Weekly |
| [FEC API](https://www.fec.gov/data/) | Campaign finance | Weekly |
| [House Stock Watcher](https://housestockwatcher.com/) | House stock trades | Daily |
| [Senate Stock Watcher](https://senatestockwatcher.com/) | Senate stock trades | Daily |
| OpenAI/Anthropic | Bill summaries | On-demand |

## Transparency Score

The Transparency Score (0-100) is calculated based on:

| Component | Points | Criteria |
|-----------|--------|----------|
| Financial Disclosure | 30 | Timeliness of required filings |
| Stock Trade Disclosure | 30 | Speed of stock trade reporting (law requires 45 days) |
| Voting Participation | 20 | Percentage of votes attended |
| Campaign Finance | 20 | Completeness of FEC reporting |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/politicians` | List all politicians with filters |
| `GET /api/politicians/{id}` | Get politician details |
| `GET /api/map/states` | State-level aggregations |
| `GET /api/votes/by-politician/{id}` | Voting history |
| `GET /api/finance/by-politician/{id}` | Campaign finance |
| `GET /api/stocks/by-politician/{id}` | Stock trades |

Full API documentation available at `/api/docs` when running the backend.

## Deployment

### Railway.app

1. Create a new project on [Railway](https://railway.app)
2. Add PostgreSQL and Redis services
3. Connect your GitHub repository
4. Set environment variables in Railway dashboard
5. Deploy!

### Manual Deployment

```bash
# Build Docker images
docker build -t polititrack-backend ./backend
docker build -t polititrack-frontend ./frontend

# Push to your registry
docker push your-registry/polititrack-backend
docker push your-registry/polititrack-frontend
```

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ProPublica](https://www.propublica.org/) for their excellent Congress API
- [House Stock Watcher](https://housestockwatcher.com/) & [Senate Stock Watcher](https://senatestockwatcher.com/) for stock trade data
- [FEC](https://www.fec.gov/) for campaign finance transparency

---

**Disclaimer**: This is a non-partisan transparency tool. Data is sourced from official government and established third-party sources. The Transparency Score is a calculated metric and should not be interpreted as an endorsement or criticism of any politician.
