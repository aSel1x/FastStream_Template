"""Stop storing user secrets in readable form.

Reset tokens and email-verification tokens become SHA-256 digests (looked up by hash, so both
columns are indexed); recovery codes become digests; the TOTP seed becomes ciphertext, since it
has to stay recoverable to verify a code.

DESTRUCTIVE. The old values cannot be converted in SQL — hashing needs the same digest the
application uses, and encrypting needs the application key — so they are dropped:

  * pending password resets and unverified email tokens are invalidated (both expire within
    24 hours anyway, and the user can simply request another);
  * enrolled 2FA is cleared, so affected users must re-enrol.

Deliberately a clean cutover rather than a read-time plaintext fallback: a fallback path in a
*template* gets copied into every project derived from it and never removed.

Revision ID: hash_and_encrypt_user_secrets
Revises: add_outbox_retry
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'hash_and_encrypt_user_secrets'
down_revision: Union[str, None] = 'add_outbox_retry'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # --- email verification ---------------------------------------------------
    op.drop_column('users', 'email_verification_token')
    op.add_column(
        'users',
        sa.Column('email_verification_token_hash', sa.LargeBinary(), nullable=True),
    )
    op.create_index(
        'ix_users_email_verification_token_hash',
        'users',
        ['email_verification_token_hash'],
    )

    # --- password reset -------------------------------------------------------
    op.drop_column('users', 'password_reset_token')
    op.add_column('users', sa.Column('password_reset_token_hash', sa.LargeBinary(), nullable=True))
    op.create_index('ix_users_password_reset_token_hash', 'users', ['password_reset_token_hash'])

    # --- two-factor -----------------------------------------------------------
    op.drop_column('users', 'two_factor_secret')
    op.add_column('users', sa.Column('two_factor_secret', sa.LargeBinary(), nullable=True))
    op.drop_column('users', 'two_factor_backup_codes')
    op.add_column(
        'users',
        sa.Column(
            'two_factor_backup_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.execute(
        sa.text(
            'UPDATE users SET two_factor_enabled_at = NULL WHERE two_factor_enabled_at IS NOT NULL'
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'two_factor_backup_codes')
    op.add_column('users', sa.Column('two_factor_backup_codes', sa.JSON(), nullable=True))
    op.drop_column('users', 'two_factor_secret')
    op.add_column('users', sa.Column('two_factor_secret', sa.String(), nullable=True))

    op.drop_index('ix_users_password_reset_token_hash', table_name='users')
    op.drop_column('users', 'password_reset_token_hash')
    op.add_column('users', sa.Column('password_reset_token', sa.String(), nullable=True))

    op.drop_index('ix_users_email_verification_token_hash', table_name='users')
    op.drop_column('users', 'email_verification_token_hash')
    op.add_column('users', sa.Column('email_verification_token', sa.String(), nullable=True))
