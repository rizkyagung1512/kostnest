from dotenv import load_dotenv
load_dotenv()
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from database import get_db, init_db, BANK_ACCOUNTS, UPLOAD_FOLDER


def generate_svg_banner(filename, folder, title, subtitle, bg_color="#1e3a8a", icon="🏢"):
    target_dir = os.path.join(UPLOAD_FOLDER, folder)
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, filename)
    gid = filename.replace('.', '_')

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="100%" height="100%">
  <defs>
    <linearGradient id="grad_{gid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{bg_color};stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0f172a;stop-opacity:0.95" />
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="800" height="500" fill="url(#grad_{gid})"/>
  <rect width="800" height="500" fill="url(#grid)"/>
  <circle cx="700" cy="80" r="140" fill="rgba(255,255,255,0.06)"/>
  <circle cx="100" cy="420" r="160" fill="rgba(255,255,255,0.04)"/>
  <text x="400" y="210" font-family="'Segoe UI', Roboto, sans-serif" font-size="80" text-anchor="middle" fill="#ffffff" opacity="0.9">{icon}</text>
  <text x="400" y="290" font-family="'Segoe UI', Roboto, sans-serif" font-size="34" font-weight="bold" text-anchor="middle" fill="#ffffff">{title}</text>
  <text x="400" y="340" font-family="'Segoe UI', Roboto, sans-serif" font-size="18" text-anchor="middle" fill="#94a3b8">{subtitle}</text>
  <rect x="250" y="380" width="300" height="38" rx="19" fill="rgba(255,255,255,0.15)"/>
  <text x="400" y="405" font-family="'Segoe UI', Roboto, sans-serif" font-size="14" font-weight="600" text-anchor="middle" fill="#38bdf8">KosNest Exclusive Residence</text>
</svg>'''

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    return f"/static/uploads/{folder}/{filename}"


def insert_room(cursor, room, images):
    """Simpan 1 kamar + foto galerinya, kembalikan id kamar."""
    cursor.execute('''
        INSERT INTO rooms (room_number, name, type, price, size, floor,
                           description, facilities, main_image, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    ''', room)
    room_id = cursor.fetchone()['id']
    for url, caption in images:
        cursor.execute(
            'INSERT INTO room_images (room_id, image_url, caption) VALUES (?, ?, ?)',
            (room_id, url, caption)
        )
    return room_id


def seed():
    init_db()

    # 1. Gambar
    img_kos_front = generate_svg_banner("kos_depan.svg", "kos", "Tampak Depan KosNest", "Gedung 3 Lantai Asri & Keamanan CCTV 24 Jam", "#0f766e", "🏡")
    img_kos_kitchen = generate_svg_banner("kos_dapur.svg", "kos", "Dapur Bersama Lengkap", "Kulkas Bersama, Kompor Gas & Dispenser Air Minum", "#0369a1", "🍳")
    img_kos_parkir = generate_svg_banner("kos_parkir.svg", "kos", "Area Parkir Motor & Mobil", "Aman Berpagar Otomatis & Terlindung Kanopi", "#4338ca", "🛵")
    img_kos_rooftop = generate_svg_banner("kos_rooftop.svg", "kos", "Rooftop & Jemuran", "Tempat Bersantai Sore & Area Jemur Pakaian Luas", "#6d28d9", "🌇")

    r1_main = generate_svg_banner("kamar_a101_main.svg", "rooms", "Kamar A-101 (Deluxe)", "Lantai 1 - Kasur Springbed & AC Sejuk", "#047857", "🛏️")
    r1_g1 = generate_svg_banner("kamar_a101_km.svg", "rooms", "Kamar Mandi A-101", "Kamar Mandi Dalam & Water Heater", "#0e7490", "🚿")
    r1_g2 = generate_svg_banner("kamar_a101_meja.svg", "rooms", "Area Belajar A-101", "Meja Ergonomis & WiFi 100 Mbps", "#1d4ed8", "💻")

    r2_main = generate_svg_banner("kamar_a102_main.svg", "rooms", "Kamar A-102 (Standar)", "Lantai 1 - Nyaman, Tenang & Hemat", "#b45309", "🛌")
    r2_g1 = generate_svg_banner("kamar_a102_lemari.svg", "rooms", "Interior A-102", "Lemari 2 Pintu & Ventilasi Luas", "#c2410c", "🚪")

    r3_main = generate_svg_banner("kamar_b201_main.svg", "rooms", "Kamar B-201 (Superior)", "Lantai 2 - Balkon Pribadi & Smart TV", "#7c3aed", "✨")
    r3_g1 = generate_svg_banner("kamar_b201_tv.svg", "rooms", "Smart TV & Kulkas B-201", "Hiburan Lengkap & Fasilitas Mewah", "#9333ea", "📺")
    r3_g2 = generate_svg_banner("kamar_b201_balkon.svg", "rooms", "Balkon B-201", "Pemandangan Hijau & Udara Segar", "#059669", "🌿")

    r4_main = generate_svg_banner("kamar_b202_main.svg", "rooms", "Kamar B-202 (Deluxe)", "Lantai 2 - AC, Meja Kerja Luas & Queen Bed", "#be185d", "🛏️")
    r4_g1 = generate_svg_banner("kamar_b202_km.svg", "rooms", "Kamar Mandi B-202", "Kamar Mandi Dalam Bersih & Kloset Duduk", "#0284c7", "🚿")

    r5_main = generate_svg_banner("kamar_c301_main.svg", "rooms", "Kamar C-301 (VIP Suite)", "Lantai 3 - Luas 4x5m, AC, Kulkas Mini & Pantry", "#4338ca", "👑")
    r5_g1 = generate_svg_banner("kamar_c301_view.svg", "rooms", "Pemandangan C-301", "Pemandangan Kota dari Lantai 3", "#1e40af", "🌆")

    sample_proof = generate_svg_banner("sample_transfer_proof.svg", "proofs", "Bukti Transfer M-Banking BCA", "Nominal Rp 1.500.000 - BERHASIL", "#15803d", "🧾")

    with get_db() as conn:
        cursor = conn.cursor()

        # Kosongkan semua tabel + reset nomor ID
        cursor.execute(
            "TRUNCATE TABLE bookings, room_images, kos_images, rooms, users RESTART IDENTITY CASCADE"
        )

        # Users
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, phone, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@kosnest.com', generate_password_hash("admin123"),
              'Ibu Hj. Rahmawati (Pemilik Kos)', '081234567890', 'admin'))

        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, phone, role)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
        ''', ('titut', 'titut@student.ac.id', generate_password_hash("titut123"),
              'Titut Khoirunnisa', '089876543210', 'user'))
        titut_id = cursor.fetchone()['id']

        # Foto kos
        kos_images = [
            (img_kos_front, "Tampak Depan KosNest", "Bangunan modern minimalis 3 lantai dengan sistem akses gerbang smart card dan CCTV 24 jam."),
            (img_kos_kitchen, "Dapur Bersama & Ruang Makan", "Dilengkapi kompor gas, peralatan masak, kulkas bersama, dan air minum galon gratis."),
            (img_kos_parkir, "Area Parkir Kendaraan", "Parkiran dalam berpagar kanopi, muat untuk 20 motor dan 4 mobil penghuni kos."),
            (img_kos_rooftop, "Rooftop & Area Jemur", "Area santai lantai atas dengan angin sepoi-sepoi dan jemuran pakaian yang terlindung kanopi transparan.")
        ]
        for img, title, desc in kos_images:
            cursor.execute(
                'INSERT INTO kos_images (image_url, title, description) VALUES (?, ?, ?)',
                (img, title, desc)
            )

        # Kamar
        insert_room(cursor, (
            'A-101', 'Kamar Tipe Deluxe Lantai 1', 'Deluxe', 1500000, '3 x 4 Meter', 1,
            'Kamar tipe deluxe di lantai 1 dekat akses gerbang utama. Sirkulasi udara sangat baik dengan jendela menghadap taman kecil.',
            'AC, Kamar Mandi Dalam, Kasur Springbed (Queen), WiFi Kecepatan Tinggi (100 Mbps), Meja & Kursi Belajar, Lemari Pakaian 2 Pintu, Water Heater',
            r1_main, 'kosong'
        ), [
            (r1_g1, 'Kamar Mandi Dalam dengan Shower & Water Heater'),
            (r1_g2, 'Meja Belajar Ergonomis & Koneksi WiFi Super Cepat'),
        ])

        insert_room(cursor, (
            'A-102', 'Kamar Tipe Standar Hemat Lantai 1', 'Standar', 950000, '3 x 3 Meter', 1,
            'Kamar ekonomis yang cocok bagi mahasiswi yang mengutamakan ketenangan belajar dengan harga terjangkau.',
            'Kamar Mandi Luar, Kasur Single, WiFi Kecepatan Tinggi (100 Mbps), Meja & Kursi Belajar, Lemari Pakaian 2 Pintu, Ventilasi & Jendela Luar',
            r2_main, 'kosong'
        ), [
            (r2_g1, 'Lemari Pakaian Kayu 2 Pintu & Ventilasi Luas'),
        ])

        r3_id = insert_room(cursor, (
            'B-201', 'Kamar Tipe Superior Lantai 2', 'Superior', 1850000, '3.5 x 4 Meter', 2,
            'Kamar mewah dengan balkon pribadi di lantai 2. Dilengkapi Smart TV 32 inch dan kulkas mini pribadi.',
            'AC, Kamar Mandi Dalam, Kasur Springbed (Queen), WiFi Kecepatan Tinggi (100 Mbps), Meja & Kursi Belajar, Lemari Pakaian 2 Pintu, Water Heater, Smart TV, Kulkas Mini',
            r3_main, 'dipesan'
        ), [
            (r3_g1, 'Smart TV 32 inch & Kulkas Mini Pribadi'),
            (r3_g2, 'Balkon Pribadi Lantai 2 Menghadap Pepohonan'),
        ])

        insert_room(cursor, (
            'B-202', 'Kamar Tipe Deluxe Lantai 2', 'Deluxe', 1550000, '3 x 4 Meter', 2,
            'Kamar deluxe lantai 2 dengan pencahayaan alami yang melimpah. Sudah dihuni oleh penghuni jangka panjang.',
            'AC, Kamar Mandi Dalam, Kasur Springbed (Queen), WiFi Kecepatan Tinggi (100 Mbps), Meja & Kursi Belajar, Lemari Pakaian 2 Pintu, Water Heater',
            r4_main, 'terisi'
        ), [
            (r4_g1, 'Kamar Mandi Dalam Keramik Bersih'),
        ])

        insert_room(cursor, (
            'C-301', 'Kamar VIP Suite Rooftop Lantai 3', 'VIP Suite', 2100000, '4 x 5 Meter', 3,
            'Kamar paling luas di KosNest dengan pemandangan kota langsung dari lantai 3, dekat area rooftop.',
            'AC, Kamar Mandi Dalam, Kasur Springbed (Queen), WiFi Kecepatan Tinggi (100 Mbps), Meja & Kursi Belajar, Lemari Pakaian 2 Pintu, Water Heater, Smart TV, Kulkas Mini, Token Listrik Mandiri',
            r5_main, 'kosong'
        ), [
            (r5_g1, 'Pemandangan Jendela Menghadap Suasana Kota'),
        ])

        # 1 booking contoh (menunggu verifikasi) untuk B-201
        now = datetime.now()
        cursor.execute('''
            INSERT INTO bookings (
                booking_code, user_id, room_id, amount, bank_name,
                bank_account_number, bank_account_holder, status,
                payment_proof, payment_uploaded_at, expires_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"KN-{now.strftime('%Y%m%d')}-001",
            titut_id,
            r3_id,
            1850000,
            'BCA',
            BANK_ACCOUNTS['BCA']['account_number'],
            BANK_ACCOUNTS['BCA']['account_holder'],
            'menunggu_verifikasi',
            sample_proof,
            now,
            now + timedelta(hours=22),
            now
        ))

        conn.commit()
        print("Database seeded successfully with users, rooms, kos images, and sample booking!")


if __name__ == '__main__':
    seed()