# PolitiTrack Codebase Review

## Executive Summary

PolitiTrack is a well-architected political transparency platform with solid foundations. However, there are significant opportunities for simplification and improvement across the backend, frontend, and testing infrastructure.

**Key Findings:**
- 7 DRY violations with duplicated code patterns
- 4 critical N+1 query performance issues
- Zero test coverage (fixtures exist, no tests)
- Inconsistent patterns between modules
- Several over-engineered or unused components

---

## Critical Issues (Fix First)

### 1. N+1 Query Problems

**Location:** `backend/app/api/votes.py:46-74`
```python
# Current: N+1 queries - one for each vote's bill
votes = db.execute(query).scalars().all()
for vote in votes:
    if vote.bill_id:
        bill = db.get(Bill, vote.bill_id)  # N+1 query!
```

**Fix:** Use eager loading with `joinedload()`
```python
from sqlalchemy.orm import joinedload

query = select(Vote).options(joinedload(Vote.bill)).where(...)
votes = db.execute(query).scalars().unique().all()
# Now vote.bill is already loaded - no extra queries
```

**Similar issues in:**
- `backend/app/tasks/refresh_stocks.py:58-63` - existence check per trade
- `backend/app/api/politicians.py:156-158` - stock trades query in transparency calculation

---

### 2. Five Separate Count Queries

**Location:** `backend/app/api/votes.py:95-122`
```python
# Current: 5 separate database round-trips
total_votes = db.execute(select(func.count()).where(...)).scalar()
yes_votes = db.execute(select(func.count()).where(...)).scalar()
no_votes = db.execute(select(func.count()).where(...)).scalar()
not_voting = db.execute(select(func.count()).where(...)).scalar()
present = db.execute(select(func.count()).where(...)).scalar()
```

**Fix:** Single aggregation query
```python
from sqlalchemy import case

summary = db.execute(
    select(
        func.count().label('total'),
        func.sum(case((Vote.position == 'yes', 1), else_=0)).label('yes'),
        func.sum(case((Vote.position == 'no', 1), else_=0)).label('no'),
        func.sum(case((Vote.position == 'not_voting', 1), else_=0)).label('not_voting'),
        func.sum(case((Vote.position == 'present', 1), else_=0)).label('present'),
    ).where(Vote.politician_id == politician_id)
).first()
```

---

### 3. Inefficient Bill Lookup

**Location:** `backend/app/tasks/refresh_votes.py:41`
```python
# Current: ILIKE with wildcards for what should be exact match
bill = db.query(Bill).filter(Bill.bill_id.ilike(f"%{bill_slug}%")).first()
```

**Fix:** Use exact match
```python
bill = db.execute(select(Bill).where(Bill.bill_id == bill_id_str)).scalar_one_or_none()
```

---

## DRY Violations (Consolidate)

### 1. Politician Existence Check (Repeated 10+ times)

**Locations:**
- `backend/app/api/finance.py:27-29, 58-60, 88-90`
- `backend/app/api/votes.py:26-28, 88-90`
- `backend/app/api/stocks.py:27-29`

**Current:**
```python
politician = db.get(Politician, politician_id)
if not politician:
    raise HTTPException(status_code=404, detail="Politician not found")
```

**Fix:** Create a FastAPI dependency
```python
# backend/app/api/dependencies.py
from fastapi import Depends, HTTPException
from uuid import UUID

async def get_politician_or_404(
    politician_id: UUID,
    db: Session = Depends(get_db)
) -> Politician:
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    return politician

# Usage in endpoints:
@router.get("/by-politician/{politician_id}")
async def get_votes(politician: Politician = Depends(get_politician_or_404)):
    # politician is guaranteed to exist
```

### 2. Model Update Pattern (Repeated 6+ times)

**Locations:**
- `backend/app/tasks/refresh_politicians.py:44-46, 87-89`
- `backend/app/tasks/refresh_finance.py:57-59`
- `backend/app/api/admin.py:64, 117, 1167`

**Current:**
```python
for key, value in data.items():
    if value is not None:
        setattr(existing, key, value)
```

**Fix:** Create utility function
```python
# backend/app/utils/db.py
def update_model(instance, data: dict, exclude: set = None):
    """Update model instance with non-None values from dict."""
    exclude = exclude or set()
    for key, value in data.items():
        if value is not None and key not in exclude:
            setattr(instance, key, value)
    return instance
```

### 3. Pagination Calculation (Repeated in 5 files)

**Locations:** `votes.py`, `finance.py`, `politicians.py`, `bills.py`, `stocks.py`

**Current:** `total_pages = (total + page_size - 1) // page_size`

**Fix:** Create pagination utility
```python
# backend/app/utils/pagination.py
from dataclasses import dataclass

@dataclass
class PaginationResult:
    items: list
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size
```

### 4. Party Badge Logic (Frontend - 4 files)

**Locations:**
- `frontend/src/components/Politicians/PoliticianCard.tsx:10-21`
- `frontend/src/pages/PoliticianPage.tsx:64-75`
- `frontend/src/pages/SearchPage.tsx:109-117`
- `frontend/src/pages/StatePage.tsx:106-116`

**Fix:** Extract to shared utility
```typescript
// frontend/src/utils/party.ts
export const PARTY_NAMES: Record<string, string> = {
  D: 'Democrat',
  R: 'Republican',
  I: 'Independent',
  ID: 'Independent',
}

export const getPartyBadgeClass = (party: string) =>
  clsx('party-badge', {
    'party-badge-d': party === 'D',
    'party-badge-r': party === 'R',
    'party-badge-i': party === 'I' || party === 'ID',
  })

export const getPartyName = (party: string) =>
  PARTY_NAMES[party] || 'Unknown'
```

---

## Simplification Opportunities

### 1. Remove Duplicate Endpoints

**Location:** `backend/app/api/admin.py:21-31 and 83-132`

`populate_politicians` and `populate_politicians_sync` have nearly identical logic. Keep only one (the sync version) since background tasks handle async work.

### 2. Consolidate SQLAlchemy API Usage

The codebase mixes deprecated `db.query()` with modern `select()` API inconsistently.

**Files using deprecated `db.query()`:**
- `backend/app/tasks/refresh_votes.py`
- `backend/app/tasks/refresh_politicians.py`
- `backend/app/tasks/refresh_finance.py`
- `backend/app/api/admin.py` (extensively)

**Fix:** Migrate all to modern `select()` API for consistency:
```python
# Instead of:
politician = db.query(Politician).filter(Politician.bioguide_id == bioguide_id).first()

# Use:
politician = db.execute(
    select(Politician).where(Politician.bioguide_id == bioguide_id)
).scalar_one_or_none()
```

### 3. Extract Transparency Score Thresholds

**Location:** `backend/app/api/politicians.py:173-180, 206-220`

Scoring thresholds are hardcoded throughout the function.

**Fix:** Move to configuration
```python
# backend/app/config.py
TRANSPARENCY_SCORE_CONFIG = {
    "stock_disclosure": {
        "max_points": 30,
        "thresholds": [(30, 30), (45, 20), (60, 10)],  # (days, points)
    },
    "vote_participation": {"max_points": 20},
    "campaign_finance": {"max_points": 20},
    "financial_disclosure": {"max_points": 30},
}
```

### 4. Remove Incomplete/Dead Code

**Location:** `backend/app/api/admin.py:1544-1550`
```python
async def run_full_population():
    """Background task to run all population steps."""
    print("Starting full data population...")
    # Note: These would need to be called as actual functions
    print("Full population complete!")
```

This stub provides no value and should be removed or properly implemented.

### 5. Move Imports to Module Level

**Location:** `backend/app/api/admin.py` - Lines 163, 205, 244, 659, 711-712

Imports like `import httpx` and `import xml.etree.ElementTree as ET` are inside function bodies. Move to module top for clarity and minor performance benefit.

---

## Overly Complex Functions (Split)

### 1. `_calculate_transparency_breakdown` (73 lines)

**Location:** `backend/app/api/politicians.py:148-220`

**Issues:**
- 6 separate database queries
- Nested loops with complex scoring logic
- Bare `except:` clause (line 169)
- Hardcoded thresholds throughout

**Fix:** Split into service layer
```python
# backend/app/services/transparency_score.py
class TransparencyScoreCalculator:
    def __init__(self, db: Session, politician_id: UUID):
        self.db = db
        self.politician_id = politician_id

    def calculate_stock_score(self) -> float:
        """Calculate stock disclosure score (0-30 points)."""

    def calculate_vote_score(self) -> float:
        """Calculate vote participation score (0-20 points)."""

    def calculate_finance_score(self) -> float:
        """Calculate campaign finance score (0-20 points)."""

    def calculate(self) -> TransparencyBreakdown:
        """Calculate full transparency breakdown."""
```

### 2. `populate_senate_votes` (192 lines)

**Location:** `backend/app/api/admin.py:698-890`

**Issues:**
- XML parsing mixed with business logic
- Complex senator matching logic
- Multiple nested loops and conditionals

**Fix:** Split into:
1. Senate vote XML fetcher (service)
2. Vote parser (service)
3. Senator matcher (service)
4. Thin admin endpoint that orchestrates

### 3. `get_stock_trade_analysis` (94 lines)

**Location:** `backend/app/api/stocks.py:54-147`

**Issues:**
- Manual aggregations should be SQL
- Cumulative calculations in Python loop
- Business logic in endpoint

**Fix:** Move aggregations to SQL, calculations to service layer.

---

## Error Handling Improvements

### 1. Replace Bare Except Clauses

**Location:** `backend/app/api/politicians.py:169`
```python
except:
    pass
```

**Fix:** Catch specific exceptions
```python
except (ValueError, TypeError) as e:
    logger.warning(f"Failed to calculate stock score: {e}")
```

### 2. Replace Print Statements with Logging

**Locations:** Throughout `backend/app/api/admin.py` and `backend/app/tasks/refresh_*.py`

```python
# Current:
print(f"Fetching members from Congress {congress}...")

# Fix:
import logging
logger = logging.getLogger(__name__)
logger.info(f"Fetching members from Congress {congress}...")
```

### 3. Add Error Handling to Frontend Pages

**Location:** `frontend/src/pages/PoliticianPage.tsx:19-47`

Multiple queries without error checking:
```typescript
const { data: votingSummary } = useQuery({...})  // No error handling
const { data: financeData } = useQuery({...})    // No error handling
```

**Fix:** Add error states and display
```typescript
const { data: votingSummary, error: votesError } = useQuery({...})

if (votesError) {
  return <ErrorCard message="Failed to load voting data" />
}
```

---

## Frontend Improvements

### 1. Add React.memo to List Items

**Location:** `frontend/src/components/Politicians/PoliticianCard.tsx`

```typescript
// Current:
export function PoliticianCard({ politician }: Props) {...}

// Fix:
export const PoliticianCard = React.memo(function PoliticianCard({ politician }: Props) {
  // ... component body
})
```

### 2. Combine Duplicate Map Event Handlers

**Location:** `frontend/src/components/Map/USMap.tsx:187-191 and 206-231`

Two separate `mousemove` handlers on `'states-fill'` layer. Combine into one.

### 3. Remove Console Logs

**Files with console.log statements:**
- `frontend/src/pages/HomePage.tsx:12-13`
- `frontend/src/api/client.ts:14-22, 28`
- `frontend/src/components/Map/USMap.tsx:89-90, 96, 116`

Remove or wrap in `process.env.NODE_ENV === 'development'` check.

### 4. Extract formatCurrency Utility

**Location:** `frontend/src/components/Dashboard/FinanceChart.tsx:26-34`

```typescript
// Move to frontend/src/utils/format.ts
export const formatCurrency = (value: number): string => {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`
  return `$${value}`
}
```

### 5. Create Custom Hook for Politician Page Queries

**Location:** `frontend/src/pages/PoliticianPage.tsx`

```typescript
// frontend/src/hooks/usePoliticianData.ts
export function usePoliticianData(id: string) {
  const politician = useQuery({...})
  const votingSummary = useQuery({...})
  const financeData = useQuery({...})

  return {
    data: { politician, votingSummary, financeData },
    isLoading: politician.isLoading || votingSummary.isLoading,
    error: politician.error || votingSummary.error,
  }
}
```

---

## Testing Recommendations

### Current State: ZERO Tests

The codebase has test fixtures (`backend/tests/conftest.py`) but no actual test files.

### Priority Test Files to Create

```
backend/tests/
├── test_api_politicians.py    # ~50 tests
├── test_api_votes.py          # ~40 tests
├── test_api_finance.py        # ~30 tests
├── test_api_stocks.py         # ~30 tests
├── test_services_congress.py  # ~40 tests (with mocking)
├── test_services_fec.py       # ~30 tests (with mocking)
└── test_transparency_score.py # ~25 tests
```

### Example Test Structure

```python
# backend/tests/test_api_politicians.py
import pytest
from fastapi.testclient import TestClient

class TestListPoliticians:
    def test_returns_200(self, client):
        response = client.get("/api/politicians")
        assert response.status_code == 200

    def test_filters_by_state(self, client, populated_db):
        response = client.get("/api/politicians?state=CA")
        assert all(p["state"] == "CA" for p in response.json()["items"])

    def test_pagination(self, client, populated_db):
        response = client.get("/api/politicians?page=1&page_size=10")
        assert len(response.json()["items"]) <= 10

    def test_invalid_state_returns_empty(self, client):
        response = client.get("/api/politicians?state=ZZ")
        assert response.json()["items"] == []

class TestGetPolitician:
    def test_not_found_returns_404(self, client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/politicians/{fake_uuid}")
        assert response.status_code == 404

    def test_includes_transparency_breakdown(self, client, populated_db):
        # ...
```

---

## Architecture Improvements

### 1. Service Layer Separation

Currently, business logic is mixed into API endpoints. Create proper service classes:

```
backend/app/services/
├── politicians.py      # Politician business logic
├── voting.py           # Vote aggregation and analysis
├── finance.py          # Campaign finance calculations
├── stocks.py           # Stock trade analysis
└── transparency.py     # Transparency score calculation
```

### 2. Repository Pattern for Data Access

Encapsulate database queries:

```python
# backend/app/repositories/politician_repository.py
class PoliticianRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, politician_id: UUID) -> Politician | None:
        return self.db.get(Politician, politician_id)

    def get_by_bioguide(self, bioguide_id: str) -> Politician | None:
        return self.db.execute(
            select(Politician).where(Politician.bioguide_id == bioguide_id)
        ).scalar_one_or_none()

    def list_by_state(self, state: str, page: int, page_size: int):
        # ...
```

### 3. Configuration Management

Extract all magic numbers and hardcoded values:

```python
# backend/app/config.py
class Settings(BaseSettings):
    # Current congress number
    current_congress: int = 119

    # API rate limits (requests per minute)
    congress_gov_rate_limit: int = 100
    fec_rate_limit: int = 120

    # Transparency score configuration
    stock_disclosure_max_points: int = 30
    vote_participation_max_points: int = 20

    # Pagination defaults
    default_page_size: int = 50
    max_page_size: int = 100
```

---

## Quick Wins (Low Effort, High Impact)

1. **Add `joinedload()` to votes query** - Eliminates N+1, single line change
2. **Create `get_politician_or_404` dependency** - Reduces 30+ lines of duplicate code
3. **Add `React.memo` to PoliticianCard** - Single line, improves list rendering
4. **Remove console.log statements** - Find and delete, cleaner production logs
5. **Replace bare `except:` with specific exceptions** - Better error visibility
6. **Extract party utilities to shared file** - Reduces 60+ lines of duplicate frontend code

---

## Summary Priority Matrix

| Priority | Category | Effort | Impact |
|----------|----------|--------|--------|
| P0 | N+1 queries | Low | High |
| P0 | Test coverage | High | Critical |
| P1 | DRY violations | Medium | High |
| P1 | Error handling | Low | Medium |
| P2 | Complex functions | Medium | Medium |
| P2 | Frontend performance | Low | Medium |
| P3 | Architecture improvements | High | Long-term |
| P3 | SQLAlchemy API consistency | Medium | Low |

---

*Generated: 2026-01-12*
