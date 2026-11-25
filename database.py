import os
import re
import urllib.request, urllib.parse
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

BANK_ACCOUNTS = {
    'BCA': {
        'bank_name': 'Bank BCA',
        'account_number': '8735-0921-44',
        'account_holder': 'KosNest Management (Ibu Hj. Rahmawati)'
    },
    'Mandiri': {
        'bank_name': 'Bank Mandiri',
        'account_number': '137-00-2983741-2',
        'account_holder': 'KosNest Management (Ibu Hj. Rahmawati)'
    },
    'BRI': {
        'bank_name': 'Bank BRI',
        'account_number': '0341-01-089234-50-8',
        'account_holder': 'KosNest Management (Ibu Hj. Rahmawati)'
    },
    'BNI': {
        'bank_name': 'Bank BNI',
        'account_number': '098-442-1205',
        'account_holder': 'KosNest Management (Ibu Hj. Rahmawati)'
    }
}

ALL_FACILITIES = [
    "AC",
    "Kamar Mandi Dalam",
    "Kamar Mandi Luar",
    "Kasur Springbed (Queen)",
    "Kasur Single",
    "WiFi Kecepatan Tinggi (100 Mbps)",
    "Meja & Kursi Belajar",
    "Lemari Pakaian 2 Pintu",
    "Water Heater",
    "Ventilasi & Jendela Luar",
    "Token Listrik Mandiri",
    "Smart TV",
    "Kulkas Mini"
]


# ---------------------------------------------------------------
# Pembungkus agar kode gaya SQLite tetap jalan di PostgreSQL
# ---------------------------------------------------------------

def upload_to_storage(file_storage, bucket, filename):
    """Upload file ke Supabase Storage, kembalikan URL publik."""
    base = os.environ["SUPABASE_URL"].rstrip('/')
    key = os.environ["SUPABASE_SERVICE_KEY"]
    data = file_storage.read()
    path = urllib.parse.quote(filename)
    req = urllib.request.Request(
        f"{base}/storage/v1/object/{bucket}/{path}",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": file_storage.mimetype or "application/octet-stream",
            "x-upsert": "true",
        },
    )
    urllib.request.urlopen(req)
    return f"{base}/storage/v1/object/public/{bucket}/{path}"

def _convert_sql(sql):
    sql = sql.replace('%', '%%')
    sql = sql.replace('?', '%s')
    sql = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT',
                 'SERIAL PRIMARY KEY', sql, flags=re.I)
    sql = re.sub(r'\bAUTOINCREMENT\b', '', sql, flags=re.I)
    sql = re.sub(r'INSERT\s+OR\s+IGNORE', 'INSERT', sql, flags=re.I)
    return sql


class PGCursor:
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=None):
        sql = _convert_sql(sql)
        if params is None or params == ():
            self._cur.execute(sql.replace('%%', '%'))
        else:
            self._cur.execute(sql, params)
        return self

    def executescript(self, script):
        for stmt in script.split(';'):
            if stmt.strip():
                self.execute(stmt)

    def __iter__(self):
        return iter(self._cur)

    def __getattr__(self, name):
        return getattr(self._cur, name)


class PGConn:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PGCursor(self._conn.cursor())

    def execute(self, sql, params=None):
        return self.cursor().execute(sql, params)

    def executescript(self, script):
        self.cursor().executescript(script)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
        finally:
            self._conn.close()


def get_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)
    return PGConn(conn)


# ---------------------------------------------------------------
# Membuat tabel
# ---------------------------------------------------------------
def init_db():
    try:
        os.makedirs(os.path.join(UPLOAD_FOLDER, 'proofs'), exist_ok=True)
    except OSError:
        pass  # Vercel read-only, abaikan

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id SERIAL PRIMARY KEY,
                room_number TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                price INTEGER NOT NULL,
                size TEXT NOT NULL,
                floor INTEGER NOT NULL DEFAULT 1,
                description TEXT,
                facilities TEXT,
                main_image TEXT,
                status TEXT NOT NULL DEFAULT 'kosong',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS room_images (
                id SERIAL PRIMARY KEY,
                room_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                caption TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kos_images (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                image_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                booking_code TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                bank_name TEXT NOT NULL,
                bank_account_number TEXT NOT NULL,
                bank_account_holder TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'menunggu_pembayaran',
                payment_proof TEXT,
                payment_uploaded_at TIMESTAMP,
                rejection_reason TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()


# ---------------------------------------------------------------
# Booking kedaluwarsa
# ---------------------------------------------------------------
def check_and_expire_bookings():
    """
    Booking 'menunggu_pembayaran' yang melewati expires_at otomatis
    jadi 'kedaluwarsa', dan kamar dibuka lagi bila tidak ada booking aktif lain.
    """
    now = datetime.now()
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, room_id, booking_code, status, expires_at
            FROM bookings
            WHERE status = 'menunggu_pembayaran' AND expires_at < ?
        ''', (now,))

        expired_bookings = cursor.fetchall()
        for b in expired_bookings:
            cursor.execute('''
                UPDATE bookings SET status = 'kedaluwarsa' WHERE id = ?
            ''', (b['id'],))

            cursor.execute('''
                SELECT COUNT(*) AS active_count
                FROM bookings
                WHERE room_id = ?
                  AND status IN ('menunggu_pembayaran', 'menunggu_verifikasi', 'disetujui')
                  AND id != ?
            ''', (b['room_id'], b['id']))
            active = cursor.fetchone()
            if active and active['active_count'] == 0:
                cursor.execute("UPDATE rooms SET status = 'kosong' WHERE id = ?", (b['room_id'],))

        conn.commit()