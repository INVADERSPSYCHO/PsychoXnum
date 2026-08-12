#!/usr/bin/env python3
# =====================================================
# PSYCHOPATHMC - KABOOM MODE (3000 CONCURRENT)
# Isme VPS ki full power use karo
# =====================================================

import os
import asyncio
import aiohttp
import psycopg2
from datetime import datetime
from psycopg2.extras import execute_values

# ========== CONFIG ==========
DATABASE_URL = "postgresql://neondb_owner:npg_wzV5qXtDANb7@ep-wild-breeze-azdi9w7w-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
API_URL = "https://number-info-api-2.vercel.app/number?num={}"
CONCURRENT = 3000  # 🔥🔥🔥 3000 parallel - FULL POWER

# 🔥 FULL 9 SERIES (100 crore)
START = 9000000000
END = 9999999999

# ========== DATABASE SETUP ==========
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS number_records (
            id SERIAL PRIMARY KEY,
            number VARCHAR(10) UNIQUE,
            name VARCHAR(255), fname VARCHAR(255), aadhar VARCHAR(12),
            address TEXT, circle VARCHAR(100), alt VARCHAR(15), email VARCHAR(255),
            found BOOLEAN DEFAULT FALSE,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_number ON number_records(number);
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database ready")

# ========== RESUME ==========
def get_last_scraped():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT MAX(number) FROM number_records WHERE found = true AND number BETWEEN %s AND %s", (START, END))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return int(row[0]) if row[0] else START - 1
    except:
        return START - 1

# ========== FETCH ==========
async def fetch(session, num):
    try:
        async with session.get(API_URL.format(num), timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('found', 0) > 0 and data.get('data'):
                    return data['data']
    except:
        pass
    return None

# ========== BULK SAVE ==========
def save_bulk(records, conn):
    if not records:
        return 0
    cur = conn.cursor()
    data = []
    for rec in records:
        data.append((
            rec.get('num'), rec.get('name'), rec.get('fname'),
            rec.get('aadhar'), rec.get('address'), rec.get('circle'),
            rec.get('alt'), rec.get('email'), True
        ))
    try:
        execute_values(cur, """
            INSERT INTO number_records (number, name, fname, aadhar, address, circle, alt, email, found)
            VALUES %s
            ON CONFLICT (number) DO UPDATE SET
                name=EXCLUDED.name, fname=EXCLUDED.fname,
                aadhar=EXCLUDED.aadhar, address=EXCLUDED.address,
                circle=EXCLUDED.circle, alt=EXCLUDED.alt,
                email=EXCLUDED.email, found=EXCLUDED.found,
                scraped_at=CURRENT_TIMESTAMP;
        """, data)
        conn.commit()
        cur.close()
        return len(data)
    except:
        cur.close()
        return 0

# ========== MAIN ==========
async def main():
    init_db()
    conn = psycopg2.connect(DATABASE_URL)
    
    start = get_last_scraped() + 1
    end = END
    total_saved = 0
    start_time = datetime.now()
    
    print(f"🔄 Full 9 Series: {START} to {END}")
    print(f"📊 Total numbers: {END - START + 1}")
    print(f"⚡ Concurrent: {CONCURRENT} (KABOOM MODE)")
    print(f"🔄 Resuming from: {start}")
    
    # Increase limits for high concurrency
    connector = aiohttp.TCPConnector(limit=CONCURRENT, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=15)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for i in range(start, end + 1, CONCURRENT):
            batch = list(range(i, min(i + CONCURRENT, end + 1)))
            tasks = [fetch(session, str(n)) for n in batch]
            results = await asyncio.gather(*tasks)
            
            all_records = []
            for res in results:
                if res:
                    all_records.extend(res)
            
            if all_records:
                saved = save_bulk(all_records, conn)
                total_saved += saved
            
            # Progress every 100,000 numbers
            if i % 100000 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (i - start) / elapsed if elapsed > 0 else 0
                remaining = (end - i) / rate if rate > 0 else 0
                print(f"📊 Progress: {i} | Saved: {total_saved} | Rate: {rate:.1f}/sec | Remaining: {remaining/3600:.1f}h")
    
    conn.close()
    print(f"\n✅ Complete! Total records saved: {total_saved}")

if __name__ == "__main__":
    asyncio.run(main())
