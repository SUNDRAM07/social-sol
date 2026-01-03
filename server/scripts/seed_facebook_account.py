"""
Seed a facebook page credential into social_media_accounts for testing.

Usage:
    python seed_facebook_account.py \
        --user-id <UUID> \
        --page-id <ID> \
        --page-name "My Page" \
        --access-token <TOKEN> \
        --facebook-user-id <FB_USER_ID> \
        [--expires-in-days 60]
"""

import argparse
import asyncio
from datetime import datetime, timedelta
import os

try:
    import asyncpg
except ImportError as exc:
    raise SystemExit(
        "asyncpg is required for this script. Install it with 'pip install asyncpg'."
    ) from exc


async def insert_account(
    dsn: str,
    user_id: str,
    page_id: str,
    page_name: str,
    access_token: str,
    facebook_user_id: str,
    expires_in_days: int,
):
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None

    metadata = {
        "facebook_user_id": facebook_user_id,
        "page_id": page_id,
        "page_access_token": access_token,
    }

    scopes = ["pages_show_list", "pages_read_engagement", "pages_manage_posts"]

    query = """
        INSERT INTO social_media_accounts (
            user_id,
            platform,
            account_id,
            display_name,
            access_token,
            refresh_token,
            token_type,
            expires_at,
            metadata,
            scopes,
            is_active,
            is_primary,
            created_at,
            updated_at
        )
        VALUES (
            $1,
            'facebook',
            $2,
            $3,
            $4,
            NULL,
            'Bearer',
            $5,
            $6::jsonb,
            $7,
            TRUE,
            TRUE,
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id, platform, account_id)
        DO UPDATE SET
            display_name = EXCLUDED.display_name,
            access_token = EXCLUDED.access_token,
            expires_at = EXCLUDED.expires_at,
            metadata = EXCLUDED.metadata,
            scopes = EXCLUDED.scopes,
            is_active = TRUE,
            is_primary = EXCLUDED.is_primary,
            updated_at = NOW();
    """

    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute(
            query,
            user_id,
            page_id,
            page_name,
            access_token,
            expires_at,
            metadata,
            scopes,
        )
        print(f"✅ Seeded Facebook page {page_id} for user {user_id}")
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="Seed a Facebook account into social_media_accounts.")
    parser.add_argument("--user-id", required=True, help="UUID of the local user")
    parser.add_argument("--page-id", required=True, help="Facebook Page ID")
    parser.add_argument("--page-name", required=True, help="Display name of the page")
    parser.add_argument("--access-token", required=True, help="Page access token")
    parser.add_argument("--facebook-user-id", required=True, help="Facebook user ID that owns the page")
    parser.add_argument("--expires-in-days", type=int, default=60, help="Days until token expiry (default 60)")
    parser.add_argument(
        "--dsn",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/socialanywhere",
        ),
        help="PostgreSQL DSN; defaults to DATABASE_URL or local dev connection.",
    )

    args = parser.parse_args()

    asyncio.run(
        insert_account(
            dsn=args.dsn,
            user_id=args.user_id,
            page_id=args.page_id,
            page_name=args.page_name,
            access_token=args.access_token,
            facebook_user_id=args.facebook_user_id,
            expires_in_days=args.expires_in_days,
        )
    )


if __name__ == "__main__":
    main()

