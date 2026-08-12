#!/usr/bin/env python3
# =====================================================
# PSYCHOPATHMC - DEBUG VERSION
# Har request ka status print karega
# =====================================================

import os
import asyncio
import aiohttp
import psycopg2
from datetime import datetime
from psycopg2.extras import execute_values

DATABASE_URL = "postgresql://neondb_owner:npg_wzV5qXtDANb7@ep-wild-breeze-azdi9w7w-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
API_URL = "https://number-info-api-2.vercel.app/number?num={}"
CONCURRENT = 10  # 🔥 Slow mode for debugging

# Sirf 100 numbers test ke liye
START = 9883114000
END = 9883114099

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

async def fetch(session, num):
    try:
        print(f"🔍 Checking {num}...", end=" ")
        async with session.get(API_URL.format(num), timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('found', 0) > 0 and data.get('data'):
                    print(f"✅ Found {len(data['data'])} records")
                    return data['data']
                else:
                    print("❌ No data")
            else:
                print(f"⚠️ HTTP {resp.status}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return None

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
    except Exception as e:
        print(f"⚠️ DB Error: {e}")
        cur.close()
        return 0

async def main():
    init_db()
    conn = psycopg2.connect(DATABASE_URL)
    
    total_saved = 0
    start_time = datetime.now()
    
    print(f"🔄 Test Range: {START} to {END}")
    print(f"📊 Total numbers: {END - START + 1}")
    print(f"⚡ Concurrent: {CONCURRENT}")
    
    connector = aiohttp.TCPConnector(limit=CONCURRENT)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for i in range(START, END + 1, CONCURRENT):
            batch = list(range(i, min(i + CONCURRENT, END + 1)))
            tasks = [fetch(session, str(n)) for n in batch]
            results = await asyncio.gather(*tasks)
            
            all_records = []
            for res in results:
                if res:
                    all_records.extend(res)
            
            if all_records:
                saved = save_bulk(all_records, conn)
                total_saved += saved
                print(f"💾 Saved batch: {saved} records")
    
    conn.close()
    
    # Final check
    conn2 = psycopg2.connect(DATABASE_URL)
    cur = conn2.cursor()
    cur.execute("SELECT COUNT(*) FROM number_records")
    count = cur.fetchone()[0]
    cur.close()
    conn2.close()
    
    print(f"\n✅ Total records saved: {total_saved}")
    print(f"📊 Database total: {count}")

if __name__ == "__main__":
    asyncio.run(main())
