"""Initial schema with all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Politicians table
    op.create_table(
        'politicians',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bioguide_id', sa.String(10), unique=True, nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('party', sa.String(50)),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('district', sa.Integer),
        sa.Column('chamber', sa.String(10), nullable=False),
        sa.Column('in_office', sa.Boolean, default=True),
        sa.Column('twitter_handle', sa.String(50)),
        sa.Column('website_url', sa.String(255)),
        sa.Column('photo_url', sa.String(255)),
        sa.Column('transparency_score', sa.Numeric(5, 2)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_politicians_state', 'politicians', ['state'])
    op.create_index('idx_politicians_chamber', 'politicians', ['chamber'])
    op.create_index('idx_politicians_party', 'politicians', ['party'])
    op.create_index('idx_politicians_bioguide', 'politicians', ['bioguide_id'])

    # Bills table
    op.create_table(
        'bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bill_id', sa.String(50), unique=True, nullable=False),
        sa.Column('congress', sa.Integer, nullable=False),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('summary_official', sa.Text),
        sa.Column('summary_ai', sa.Text),
        sa.Column('sponsor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id')),
        sa.Column('introduced_date', sa.Date),
        sa.Column('latest_action', sa.Text),
        sa.Column('latest_action_date', sa.Date),
        sa.Column('subjects', postgresql.ARRAY(sa.String)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_bills_bill_id', 'bills', ['bill_id'])
    op.create_index('idx_bills_congress', 'bills', ['congress'])
    op.create_index('idx_bills_sponsor', 'bills', ['sponsor_id'])

    # Votes table
    op.create_table(
        'votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vote_id', sa.String(50), unique=True, nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bills.id')),
        sa.Column('politician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id'), nullable=False),
        sa.Column('vote_position', sa.String(20), nullable=False),
        sa.Column('vote_date', sa.Date, nullable=False),
        sa.Column('chamber', sa.String(10), nullable=False),
        sa.Column('question', sa.Text),
        sa.Column('result', sa.String(50)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_votes_politician', 'votes', ['politician_id'])
    op.create_index('idx_votes_date', 'votes', ['vote_date'])
    op.create_index('idx_votes_bill', 'votes', ['bill_id'])

    # Campaign Finance table
    op.create_table(
        'campaign_finance',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('politician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id'), nullable=False),
        sa.Column('cycle', sa.Integer, nullable=False),
        sa.Column('total_raised', sa.Numeric(15, 2)),
        sa.Column('total_spent', sa.Numeric(15, 2)),
        sa.Column('cash_on_hand', sa.Numeric(15, 2)),
        sa.Column('total_from_pacs', sa.Numeric(15, 2)),
        sa.Column('total_from_individuals', sa.Numeric(15, 2)),
        sa.Column('last_filed', sa.Date),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_unique_constraint('uq_campaign_finance_politician_cycle', 'campaign_finance', ['politician_id', 'cycle'])
    op.create_index('idx_campaign_finance_politician', 'campaign_finance', ['politician_id'])
    op.create_index('idx_campaign_finance_cycle', 'campaign_finance', ['cycle'])

    # Top Donors table
    op.create_table(
        'top_donors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('politician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id'), nullable=False),
        sa.Column('cycle', sa.Integer, nullable=False),
        sa.Column('donor_name', sa.String(255), nullable=False),
        sa.Column('donor_type', sa.String(50)),
        sa.Column('total_amount', sa.Numeric(15, 2)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_top_donor_politician_cycle_name', 'top_donors', ['politician_id', 'cycle', 'donor_name'])
    op.create_index('idx_top_donors_politician', 'top_donors', ['politician_id'])

    # Stock Trades table
    op.create_table(
        'stock_trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('politician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id'), nullable=False),
        sa.Column('transaction_date', sa.Date, nullable=False),
        sa.Column('disclosure_date', sa.Date, nullable=False),
        sa.Column('ticker', sa.String(10)),
        sa.Column('asset_description', sa.Text),
        sa.Column('transaction_type', sa.String(20)),
        sa.Column('amount_range', sa.String(50)),
        sa.Column('amount_min', sa.Integer),
        sa.Column('amount_max', sa.Integer),
        sa.Column('filing_url', sa.String(255)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_stock_trades_politician', 'stock_trades', ['politician_id'])
    op.create_index('idx_stock_trades_date', 'stock_trades', ['transaction_date'])
    op.create_index('idx_stock_trades_ticker', 'stock_trades', ['ticker'])


def downgrade() -> None:
    op.drop_table('stock_trades')
    op.drop_table('top_donors')
    op.drop_table('campaign_finance')
    op.drop_table('votes')
    op.drop_table('bills')
    op.drop_table('politicians')
