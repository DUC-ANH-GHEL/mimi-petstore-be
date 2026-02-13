"""add_order_status_enum

Revision ID: 2cfee97a15b7
Revises: create_tables_without_fk
Create Date: 2025-06-17 22:29:13.411039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2cfee97a15b7'
down_revision: Union[str, None] = 'create_tables_without_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create ENUM type first
    orderstatus = postgresql.ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled', name='orderstatus')
    orderstatus.create(op.get_bind())

    # Convert existing data to lowercase
    op.execute("UPDATE orders SET status = LOWER(status)")

    # Alter status column with USING clause
    op.execute('ALTER TABLE orders ALTER COLUMN status TYPE orderstatus USING status::orderstatus')

    # Create order_items table without foreign keys
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('order_id', sa.Integer()),
        sa.Column('product_id', sa.Integer()),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now())
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop order_items table
    op.drop_table('order_items')

    # Revert status column to VARCHAR
    op.execute('ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(50)')

    # Drop ENUM type
    postgresql.ENUM(name='orderstatus').drop(op.get_bind())
