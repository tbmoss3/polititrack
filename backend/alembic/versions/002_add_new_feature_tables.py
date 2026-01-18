"""Add new feature tables for committees, users, alerts, and conflicts.

Revision ID: 002_add_new_features
Revises: 001_initial_schema
Create Date: 2026-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create committees table
    op.create_table(
        'committees',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('committee_code', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('chamber', sa.String(10), nullable=False),
        sa.Column('committee_type', sa.String(50), default='standing'),
        sa.Column('url', sa.String(255)),
        sa.Column('jurisdiction', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_committees_chamber', 'committees', ['chamber'])

    # Create committee_assignments table
    op.create_table(
        'committee_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('politician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id'), nullable=False),
        sa.Column('committee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('committees.id'), nullable=False),
        sa.Column('role', sa.String(50), default='member'),
        sa.Column('is_subcommittee', sa.Boolean, default=False),
        sa.Column('subcommittee_name', sa.String(255)),
        sa.Column('congress', sa.Integer),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_committee_assignments_politician', 'committee_assignments', ['politician_id'])
    op.create_index('idx_committee_assignments_committee', 'committee_assignments', ['committee_id'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('email_verified', sa.Boolean, default=False),
        sa.Column('notification_frequency', sa.String(20), default='weekly'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create user_follow_politicians table
    op.create_table(
        'user_follow_politicians',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('politician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id'), nullable=False),
        sa.Column('notify_votes', sa.Boolean, default=True),
        sa.Column('notify_trades', sa.Boolean, default=True),
        sa.Column('notify_finance', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_user_follow_politicians_user', 'user_follow_politicians', ['user_id'])
    op.create_index('idx_user_follow_politicians_politician', 'user_follow_politicians', ['politician_id'])

    # Create user_follow_bills table
    op.create_table(
        'user_follow_bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bills.id'), nullable=False),
        sa.Column('notify_votes', sa.Boolean, default=True),
        sa.Column('notify_status', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_user_follow_bills_user', 'user_follow_bills', ['user_id'])
    op.create_index('idx_user_follow_bills_bill', 'user_follow_bills', ['bill_id'])

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('reference_type', sa.String(50)),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True)),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('is_emailed', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_alerts_user', 'alerts', ['user_id'])
    op.create_index('idx_alerts_created', 'alerts', ['created_at'])
    op.create_index('idx_alerts_unread', 'alerts', ['user_id', 'is_read'])

    # Create conflicts_of_interest table
    op.create_table(
        'conflicts_of_interest',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('politician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('politicians.id'), nullable=False),
        sa.Column('stock_trade_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stock_trades.id'), nullable=False),
        sa.Column('vote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('votes.id')),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bills.id')),
        sa.Column('ticker', sa.String(20), nullable=False),
        sa.Column('company_name', sa.String(255)),
        sa.Column('sector', sa.String(100)),
        sa.Column('trade_date', sa.Date, nullable=False),
        sa.Column('vote_date', sa.Date),
        sa.Column('days_between', sa.Integer),
        sa.Column('severity_score', sa.Numeric(5, 2)),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('status', sa.String(20), default='detected'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_conflicts_politician', 'conflicts_of_interest', ['politician_id'])
    op.create_index('idx_conflicts_ticker', 'conflicts_of_interest', ['ticker'])
    op.create_index('idx_conflicts_severity', 'conflicts_of_interest', ['severity_score'])
    op.create_index('idx_conflicts_status', 'conflicts_of_interest', ['status'])


def downgrade() -> None:
    op.drop_table('conflicts_of_interest')
    op.drop_table('alerts')
    op.drop_table('user_follow_bills')
    op.drop_table('user_follow_politicians')
    op.drop_table('users')
    op.drop_table('committee_assignments')
    op.drop_table('committees')
