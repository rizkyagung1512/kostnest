import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'kosnest.db')

def view_database():
    if not os.path.exists(DB_PATH):
        print(f"File database tidak ditemukan di: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 70)
    print(" 🗄️  ISI DATABASE KOSNEST (SQLite: kosnest.db)")
    print("=" * 70)

    # 1. TABEL USERS
    print("\n--- [1] TABEL USERS (Akun Penghuni & Admin) ---")
    cursor.execute("SELECT id, username, email, full_name, phone, role FROM users")
    users = cursor.fetchall()
    for u in users:
        print(f" • ID: {u['id']:<2} | Role: {u['role']:<6} | User: {u['username']:<8} | Nama: {u['full_name']}")

    # 2. TABEL ROOMS
    print("\n--- [2] TABEL ROOMS (Daftar Kamar Kos) ---")
    cursor.execute("SELECT id, room_number, name, type, price, size, floor, status FROM rooms ORDER BY floor, room_number")
    rooms = cursor.fetchall()
    for r in rooms:
        status_icon = "🟢" if r['status'] == 'kosong' else ("🟡" if r['status'] == 'dipesan' else "🔴")
        print(f" • {status_icon} Kamar {r['room_number']:<6} | {r['type']:<10} | Lt.{r['floor']} ({r['size']}) | Rp {r['price']:>9,d}/bln | Status: {r['status'].upper()}")

    # 3. TABEL BOOKINGS
    print("\n--- [3] TABEL BOOKINGS (Riwayat & Transaksi Pemesanan) ---")
    cursor.execute('''
        SELECT b.id, b.booking_code, u.full_name, r.room_number, b.amount, b.bank_name, b.status, b.created_at, b.rejection_reason
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.id DESC
    ''')
    bookings = cursor.fetchall()
    if bookings:
        for b in bookings:
            note = f" (Alasan tolak: {b['rejection_reason']})" if b['rejection_reason'] else ""
            print(f" • Kode: {b['booking_code']} | Kamar: {b['room_number']} | Penyewa: {b['full_name']} | Rp {b['amount']:,d} via {b['bank_name']} | Status: {b['status'].upper()}{note}")
    else:
        print(" (Belum ada data booking)")

    # 4. TABEL FOTO KOS
    print("\n--- [4] TABEL KOS_IMAGES (Galeri Fasilitas Bersama Kos) ---")
    cursor.execute("SELECT id, title, description FROM kos_images")
    kos_imgs = cursor.fetchall()
    for k in kos_imgs:
        print(f" • ID: {k['id']} | {k['title']} ({k['description'][:40]}...)")

    print("\n" + "=" * 70)
    conn.close()

if __name__ == '__main__':
    view_database()
