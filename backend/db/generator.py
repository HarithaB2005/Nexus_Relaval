# db/generator.py (Admin Utility - Run once per new client)
import secrets
import string
import hashlib
import asyncpg
import os
from dotenv import load_dotenv
import asyncio

load_dotenv() # Load the DATABASE_URL

DB_URL = os.getenv("DATABASE_URL")

def generate_random_key(client_id: str) -> str:
    """Generates a secure, unique API key with a client-specific prefix."""
    random_part = secrets.token_urlsafe(32) 
    return f"APO_{client_id.upper().replace('-', '_')}_{random_part}"

def hash_key(key: str) -> str:
    """Uses the same SHA-256 hash function as in auth.py."""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

async def create_new_client_key(client_id: str):
    """Generates a new key, hashes it, and stores the hash in PostgreSQL."""
    if not DB_URL:
        print("❌ ERROR: DATABASE_URL not set in .env file.")
        return

    plain_key = generate_random_key(client_id)
    hashed_key = hash_key(plain_key)
    
    conn = None
    try:
        # Connect to the database
        conn = await asyncpg.connect(DB_URL)
        
        # Insert the HASHED key and client metadata. Must match your SQL schema!
        await conn.execute(
            """
            INSERT INTO client_credentials (client_id, api_key_hash, status) 
            VALUES ($1, $2, $3)
            """,
            client_id, hashed_key, 'active'
        )
        
        print("\n" + "="*70)
        print(f"✅ Key successfully created and hash stored for: {client_id}")
        print("🚨🚨 PLAIN API KEY (GIVE TO CLIENT - SHOW ONLY ONCE):")
        print(f"   {plain_key}")
        print("="*70 + "\n")
        
    except asyncpg.exceptions.UniqueViolationError:
        print(f"❌ ERROR: Client ID '{client_id}' already exists or the generated hash conflicted.")
    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    client_name = input("Enter NEW client ID (e.g., Fintech-Corp-A): ")
    if client_name:
        asyncio.run(create_new_client_key(client_name))
    else:
        print("Client ID cannot be empty.")