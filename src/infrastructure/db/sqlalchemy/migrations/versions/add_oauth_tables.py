"""Add OAuth and signing keys tables

Revision ID: add_oauth_tables
Revises: add_audit_logs
Create Date: 2026-04-18 18:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_oauth_tables'
down_revision: Union[str, None] = 'add_audit_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'oauth_clients',
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('client_secret_hash', sa.LargeBinary, nullable=True),
        sa.Column('client_secret_salt', sa.LargeBinary, nullable=True),
        sa.Column('client_name', sa.String(128), nullable=False),
        sa.Column('client_uri', sa.String(256), nullable=True),
        sa.Column('logo_uri', sa.String(256), nullable=True),
        sa.Column('redirect_uris', sa.JSON, nullable=False),
        sa.Column('grant_types', sa.JSON, nullable=False),
        sa.Column('response_types', sa.JSON, nullable=False),
        sa.Column('scopes', sa.JSON, nullable=False),
        sa.Column('is_confidential', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('require_auth_time', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('client_id', name=op.f('pk_oauth_clients')),
    )

    op.create_table(
        'authorization_codes',
        sa.Column('code', sa.String(128), nullable=False),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('redirect_uri', sa.String(256), nullable=False),
        sa.Column('scopes', sa.JSON, nullable=False),
        sa.Column('nonce', sa.String(256), nullable=True),
        sa.Column('auth_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('code_challenge', sa.String(256), nullable=True),
        sa.Column('code_challenge_method', sa.String(8), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('code', name=op.f('pk_authorization_codes')),
    )
    op.create_index('ix_authorization_codes_client_id', 'authorization_codes', ['client_id'])

    op.create_table(
        'signing_keys',
        sa.Column('kid', sa.String(64), nullable=False),
        sa.Column('algorithm', sa.String(8), nullable=False),
        sa.Column('private_key_pem', sa.Text, nullable=False),
        sa.Column('public_key_pem', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('kid', name=op.f('pk_signing_keys')),
    )
    op.create_index('ix_signing_keys_is_active', 'signing_keys', ['is_active'])


def downgrade() -> None:
    op.drop_table('signing_keys')
    op.drop_table('authorization_codes')
    op.drop_table('oauth_clients')
