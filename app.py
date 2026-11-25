from dotenv import load_dotenv
load_dotenv()
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import (
    get_db, init_db, check_and_expire_bookings,
    BANK_ACCOUNTS, ALL_FACILITIES, UPLOAD_FOLDER
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-sementara")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Filter format rupiah untuk Jinja template
@app.template_filter('rupiah')
def rupiah_filter(value):
    try:
        val = int(value)
        return f"Rp {val:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return f"Rp {value}"

# Context processor untuk data global
@app.context_processor
def inject_global_data():
    user = None
    if 'user_id' in session:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, full_name, role, phone FROM users WHERE id = ?", (session['user_id'],))
            user = cursor.fetchone()
    return {
        'current_user': user,
        'bank_accounts': BANK_ACCOUNTS,
        'now': datetime.now()
    }

# Otomatis periksa booking expired pada setiap request
@app.before_request
def auto_check_expired():
    # Pastikan database ada dan lakukan pengecekan expired
    check_and_expire_bookings()

# Decorator untuk otentikasi
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Silakan masuk terlebih dahulu untuk mengakses halaman ini.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# Decorator khusus admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Silakan masuk dengan akun admin.", "warning")
            return redirect(url_for('login', next=request.path))
        if session.get('role') != 'admin':
            flash("Akses ditolak. Halaman ini khusus untuk pemilik kos (Admin).", "danger")
            return redirect(url_for('katalog'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def index():
    """Halaman login sebagai halaman awal sesuai flowchart & spesifikasi."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('katalog'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('katalog'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()

        if not identifier or not password:
            flash("Harap isi username/email dan password.", "danger")
            return render_template('auth/login.html')

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?", 
                (identifier, identifier)
            )
            user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f"Selamat datang kembali, {user['full_name']}!", "success")

            next_page = request.args.get('next')
            if next_page and not next_page.startswith('//'):
                return redirect(next_page)

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('katalog'))
        else:
            flash("Data tidak sesuai. Periksa kembali username/email dan password Anda.", "danger")

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('katalog'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not all([full_name, username, email, phone, password]):
            flash("Semua bidang formulir pendaftaran wajib diisi.", "danger")
            return render_template('auth/register.html')

        if password != confirm_password:
            flash("Konfirmasi password tidak cocok.", "danger")
            return render_template('auth/register.html')

        if len(password) < 6:
            flash("Password minimal harus 6 karakter.", "danger")
            return render_template('auth/register.html')

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash("Username tersebut sudah digunakan. Silakan pilih username lain.", "danger")
                return render_template('auth/register.html')

            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash("Email tersebut sudah terdaftar.", "danger")
                return render_template('auth/register.html')

            password_hash = generate_password_hash(password)
            # Pendaftaran otomatis berperan 'user' (calon penghuni)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, full_name, phone, role)
                VALUES (?, ?, ?, ?, ?, 'user')
            ''', (username, email, password_hash, full_name, phone))
            conn.commit()

        flash("Pendaftaran akun berhasil! Silakan masuk dengan akun baru Anda.", "success")
        return redirect(url_for('login'))

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah berhasil keluar dari sistem.", "info")
    return redirect(url_for('login'))

# ==========================================
# PENGHUNI (USER) ROUTES
# ==========================================

@app.route('/katalog')
@login_required
def katalog():
    """Halaman beranda penghuni: papan slot kamar, foto kos, dan filter kamar."""
    # Filter parameter
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('q', '').strip()

    with get_db() as conn:
        cursor = conn.cursor()

        # Statistik slot kamar untuk papan info
        cursor.execute("SELECT COUNT(*) as total FROM rooms")
        total_rooms = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as kosong FROM rooms WHERE status = 'kosong'")
        total_kosong = cursor.fetchone()['kosong']

        cursor.execute("SELECT COUNT(*) as dipesan FROM rooms WHERE status = 'dipesan'")
        total_dipesan = cursor.fetchone()['dipesan']

        cursor.execute("SELECT COUNT(*) as terisi FROM rooms WHERE status = 'terisi'")
        total_terisi = cursor.fetchone()['terisi']

        # Galeri foto kos bersama
        cursor.execute("SELECT * FROM kos_images ORDER BY id ASC")
        kos_images = cursor.fetchall()

        # Query daftar kamar dengan filter
        query = "SELECT * FROM rooms WHERE 1=1"
        params = []

        if min_price is not None:
            query += " AND price >= ?"
            params.append(min_price)
        if max_price is not None:
            query += " AND price <= ?"
            params.append(max_price)
        if status_filter in ['kosong', 'dipesan', 'terisi']:
            query += " AND status = ?"
            params.append(status_filter)
        if search_query:
            query += " AND (name LIKE ? OR room_number LIKE ? OR type LIKE ? OR facilities LIKE ?)"
            wildcard = f"%{search_query}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])

        query += " ORDER BY floor ASC, room_number ASC"
        cursor.execute(query, params)
        rooms = cursor.fetchall()

    return render_template(
        'user/katalog.html',
        rooms=rooms,
        kos_images=kos_images,
        slot_stats={
            'total': total_rooms,
            'kosong': total_kosong,
            'dipesan': total_dipesan,
            'terisi': total_terisi
        },
        current_filters={
            'min_price': min_price or '',
            'max_price': max_price or '',
            'status': status_filter,
            'q': search_query
        }
    )

@app.route('/kamar/<int:room_id>')
@login_required
def detail_kamar(room_id):
    """Detail kamar: foto galeri lengkap, spesifikasi, dan fasilitas berbeda tiap kamar."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
        room = cursor.fetchone()

        if not room:
            flash("Kamar tidak ditemukan.", "danger")
            return redirect(url_for('katalog'))

        cursor.execute("SELECT * FROM room_images WHERE room_id = ?", (room_id,))
        gallery_images = cursor.fetchall()

        # Pisahkan fasilitas menjadi list
        facilities_list = [f.strip() for f in (room['facilities'] or '').split(',') if f.strip()]

        # Cek apakah user sedang punya booking aktif untuk kamar ini
        cursor.execute('''
            SELECT id, booking_code, status, expires_at 
            FROM bookings 
            WHERE user_id = ? AND room_id = ? AND status IN ('menunggu_pembayaran', 'menunggu_verifikasi')
            ORDER BY id DESC LIMIT 1
        ''', (session['user_id'], room_id))
        user_active_booking = cursor.fetchone()

    return render_template(
        'user/detail_kamar.html',
        room=room,
        gallery_images=gallery_images,
        facilities_list=facilities_list,
        user_active_booking=user_active_booking
    )

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking_kamar(room_id):
    """Proses booking kamar oleh penghuni & pemilihan metode bank transfer."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
        room = cursor.fetchone()

        if not room:
            flash("Kamar tidak ditemukan.", "danger")
            return redirect(url_for('katalog'))

        # Aturan alur: kamar yang dipesan tidak bisa dipesan orang lain
        if room['status'] != 'kosong':
            flash(f"Maaf, kamar {room['room_number']} saat ini berstatus {room['status'].upper()} dan tidak dapat dipesan.", "warning")
            return redirect(url_for('detail_kamar', room_id=room_id))

        if request.method == 'POST':
            selected_bank = request.form.get('bank_name', 'BCA')
            if selected_bank not in BANK_ACCOUNTS:
                selected_bank = 'BCA'

            bank_info = BANK_ACCOUNTS[selected_bank]

            # Generate unique booking code
            now = datetime.now()
            booking_code = f"KN-{now.strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"
            
            # Batas waktu pembayaran 24 jam dari sekarang
            expires_at = now + timedelta(hours=24)

            # Insert booking
            cursor.execute('''
                INSERT INTO bookings (
                    booking_code, user_id, room_id, amount, bank_name,
                    bank_account_number, bank_account_holder, status,
                    expires_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'menunggu_pembayaran', ?, ?)
            ''', (
                booking_code,
                session['user_id'],
                room_id,
                room['price'],
                selected_bank,
                bank_info['account_number'],
                bank_info['account_holder'],
                expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                now.strftime('%Y-%m-%d %H:%M:%S')
            ))
            booking_id = cursor.lastrowid

            # Ubah status kamar menjadi 'dipesan' sehingga tidak bisa dipesan orang lain
            cursor.execute("UPDATE rooms SET status = 'dipesan' WHERE id = ?", (room_id,))
            conn.commit()

            flash("Booking berhasil dibuat! Silakan selesaikan pembayaran dan unggah bukti transfer dalam 24 jam.", "success")
            return redirect(url_for('upload_bukti', booking_id=booking_id))

    return render_template('user/booking.html', room=room, banks=BANK_ACCOUNTS)

@app.route('/booking/bayar/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def upload_bukti(booking_id):
    """Unggah bukti transfer e-banking untuk verifikasi pemilik kos."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, r.room_number, r.name as room_name, r.price, u.full_name, u.phone
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            JOIN users u ON b.user_id = u.id
            WHERE b.id = ?
        ''', (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            flash("Data booking tidak ditemukan.", "danger")
            return redirect(url_for('riwayat'))

        # Pastikan user pemilik booking atau admin
        if booking['user_id'] != session['user_id'] and session.get('role') != 'admin':
            flash("Anda tidak memiliki akses ke pesanan ini.", "danger")
            return redirect(url_for('riwayat'))

        if request.method == 'POST':
            # Cek apakah sudah expired
            exp_date = datetime.strptime(booking['expires_at'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > exp_date and booking['status'] == 'menunggu_pembayaran':
                cursor.execute("UPDATE bookings SET status = 'kedaluwarsa' WHERE id = ?", (booking_id,))
                cursor.execute("UPDATE rooms SET status = 'kosong' WHERE id = ?", (booking['room_id'],))
                conn.commit()
                flash("Maaf, batas waktu pembayaran 24 jam telah kedaluwarsa. Kamar dibuka kembali untuk pemesanan lain.", "danger")
                return redirect(url_for('katalog'))

            if 'payment_proof' not in request.files:
                flash("File bukti transfer belum dipilih.", "danger")
                return redirect(request.url)

            file = request.files['payment_proof']
            if file.filename == '':
                flash("Harap pilih gambar bukti transfer yang valid.", "danger")
                return redirect(request.url)

            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                safe_name = f"proof_{booking['booking_code']}_{int(datetime.now().timestamp())}.{ext}"
                target_path = os.path.join(UPLOAD_FOLDER, 'proofs', safe_name)
                file.save(target_path)
                proof_url = f"/static/uploads/proofs/{safe_name}"

                # Update status booking menjadi 'menunggu_verifikasi'
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    UPDATE bookings 
                    SET payment_proof = ?, payment_uploaded_at = ?, status = 'menunggu_verifikasi', rejection_reason = NULL
                    WHERE id = ?
                ''', (proof_url, now_str, booking_id))
                conn.commit()

                flash("Bukti transfer berhasil diunggah! Status saat ini: Menunggu verifikasi pemilik kos.", "success")
                return redirect(url_for('riwayat'))
            else:
                flash("Format file tidak didukung. Harap unggah gambar format JPG, PNG, atau WEBP.", "danger")

    return render_template('user/upload_bukti.html', booking=booking)

@app.route('/riwayat')
@login_required
def riwayat():
    """Halaman riwayat pembayaran dan status pemesanan kamar penghuni."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, r.room_number, r.name as room_name, r.type as room_type, r.main_image
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        ''', (session['user_id'],))
        bookings = cursor.fetchall()

    return render_template('user/riwayat.html', bookings=bookings)

# ==========================================
# ADMIN (PEMILIK KOS) ROUTES
# ==========================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Dashboard admin dengan ringkasan statistik dan verifikasi pending."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Statistik kamar
        cursor.execute("SELECT COUNT(*) as total FROM rooms")
        total_rooms = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as kosong FROM rooms WHERE status = 'kosong'")
        total_kosong = cursor.fetchone()['kosong']

        cursor.execute("SELECT COUNT(*) as dipesan FROM rooms WHERE status = 'dipesan'")
        total_dipesan = cursor.fetchone()['dipesan']

        cursor.execute("SELECT COUNT(*) as terisi FROM rooms WHERE status = 'terisi'")
        total_terisi = cursor.fetchone()['terisi']

        # Statistik verifikasi pembayaran
        cursor.execute("SELECT COUNT(*) as pending FROM bookings WHERE status = 'menunggu_verifikasi'")
        pending_verifications = cursor.fetchone()['pending']

        cursor.execute("SELECT COUNT(*) as lunas, SUM(amount) as total_nominal FROM bookings WHERE status = 'disetujui'")
        income_row = cursor.fetchone()
        total_lunas = income_row['lunas'] or 0
        total_income = income_row['total_nominal'] or 0

        # Booking yang membutuhkan tindakan verifikasi segera
        cursor.execute('''
            SELECT b.*, r.room_number, r.name as room_name, u.full_name as user_name, u.phone as user_phone
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            JOIN users u ON b.user_id = u.id
            WHERE b.status = 'menunggu_verifikasi'
            ORDER BY b.payment_uploaded_at ASC
        ''')
        pending_bookings = cursor.fetchall()

    return render_template(
        'admin/dashboard.html',
        stats={
            'total_rooms': total_rooms,
            'kosong': total_kosong,
            'dipesan': total_dipesan,
            'terisi': total_terisi,
            'pending_verifications': pending_verifications,
            'total_lunas': total_lunas,
            'total_income': total_income
        },
        pending_bookings=pending_bookings
    )

@app.route('/admin/kamar')
@admin_required
def admin_kamar_list():
    """Daftar kamar untuk dikelola oleh admin."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms ORDER BY floor ASC, room_number ASC")
        rooms = cursor.fetchall()
    return render_template('admin/kamar_list.html', rooms=rooms)

@app.route('/admin/kamar/tambah', methods=['GET', 'POST'])
@admin_required
def admin_kamar_tambah():
    """Tambah kamar baru beserta foto utama, galeri foto, dan fasilitasnya."""
    if request.method == 'POST':
        room_number = request.form.get('room_number', '').strip().upper()
        name = request.form.get('name', '').strip()
        room_type = request.form.get('type', 'Standar').strip()
        price = request.form.get('price', 0, type=int)
        size = request.form.get('size', '').strip()
        floor = request.form.get('floor', 1, type=int)
        description = request.form.get('description', '').strip()
        
        # Fasilitas (checkbox list + optional custom comma list)
        facilities_selected = request.form.getlist('facilities')
        custom_facilities = request.form.get('custom_facilities', '').strip()
        if custom_facilities:
            facilities_selected.extend([f.strip() for f in custom_facilities.split(',') if f.strip()])
        facilities_str = ", ".join(dict.fromkeys(facilities_selected))

        # Upload foto utama
        main_image_url = "/static/uploads/rooms/default_room.svg"
        if 'main_image' in request.files:
            file = request.files['main_image']
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                safe_name = f"room_{room_number}_{int(datetime.now().timestamp())}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, 'rooms', safe_name))
                main_image_url = f"/static/uploads/rooms/{safe_name}"

        with get_db() as conn:
            cursor = conn.cursor()
            # Cek keunikan nomor kamar
            cursor.execute("SELECT id FROM rooms WHERE room_number = ?", (room_number,))
            if cursor.fetchone():
                flash(f"Nomor kamar '{room_number}' sudah ada. Gunakan nomor lain.", "danger")
                return render_template('admin/kamar_form.html', all_facilities=ALL_FACILITIES, action='tambah', room=None)

            cursor.execute('''
                INSERT INTO rooms (room_number, name, type, price, size, floor, description, facilities, main_image, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'kosong')
            ''', (room_number, name, room_type, price, size, floor, description, facilities_str, main_image_url))
            new_room_id = cursor.lastrowid

            # Upload galeri foto tambahan jika ada
            gallery_files = request.files.getlist('gallery_images')
            for gfile in gallery_files:
                if gfile and allowed_file(gfile.filename):
                    ext = gfile.filename.rsplit('.', 1)[1].lower()
                    gname = f"room_gal_{new_room_id}_{uuid.uuid4().hex[:6]}.{ext}"
                    gfile.save(os.path.join(UPLOAD_FOLDER, 'rooms', gname))
                    gurl = f"/static/uploads/rooms/{gname}"
                    cursor.execute('''
                        INSERT INTO room_images (room_id, image_url, caption)
                        VALUES (?, ?, ?)
                    ''', (new_room_id, gurl, f"Foto fasilitas {room_number}"))

            conn.commit()

        flash(f"Kamar {room_number} berhasil ditambahkan!", "success")
        return redirect(url_for('admin_kamar_list'))

    return render_template('admin/kamar_form.html', all_facilities=ALL_FACILITIES, action='tambah', room=None, room_facilities=[])

@app.route('/admin/kamar/edit/<int:room_id>', methods=['GET', 'POST'])
@admin_required
def admin_kamar_edit(room_id):
    """Ubah data kamar, status, foto utama, galeri foto, dan fasilitas."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
        room = cursor.fetchone()

        if not room:
            flash("Kamar tidak ditemukan.", "danger")
            return redirect(url_for('admin_kamar_list'))

        cursor.execute("SELECT * FROM room_images WHERE room_id = ?", (room_id,))
        gallery_images = cursor.fetchall()

        if request.method == 'POST':
            room_number = request.form.get('room_number', '').strip().upper()
            name = request.form.get('name', '').strip()
            room_type = request.form.get('type', 'Standar').strip()
            price = request.form.get('price', 0, type=int)
            size = request.form.get('size', '').strip()
            floor = request.form.get('floor', 1, type=int)
            description = request.form.get('description', '').strip()
            status = request.form.get('status', room['status'])

            facilities_selected = request.form.getlist('facilities')
            custom_facilities = request.form.get('custom_facilities', '').strip()
            if custom_facilities:
                facilities_selected.extend([f.strip() for f in custom_facilities.split(',') if f.strip()])
            facilities_str = ", ".join(dict.fromkeys(facilities_selected))

            main_image_url = room['main_image']
            if 'main_image' in request.files:
                file = request.files['main_image']
                if file and allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    safe_name = f"room_{room_number}_{int(datetime.now().timestamp())}.{ext}"
                    file.save(os.path.join(UPLOAD_FOLDER, 'rooms', safe_name))
                    main_image_url = f"/static/uploads/rooms/{safe_name}"

            cursor.execute('''
                UPDATE rooms 
                SET room_number = ?, name = ?, type = ?, price = ?, size = ?, floor = ?,
                    description = ?, facilities = ?, main_image = ?, status = ?
                WHERE id = ?
            ''', (room_number, name, room_type, price, size, floor, description, facilities_str, main_image_url, status, room_id))

            # Tambahkan foto galeri baru jika diunggah
            gallery_files = request.files.getlist('gallery_images')
            for gfile in gallery_files:
                if gfile and allowed_file(gfile.filename):
                    ext = gfile.filename.rsplit('.', 1)[1].lower()
                    gname = f"room_gal_{room_id}_{uuid.uuid4().hex[:6]}.{ext}"
                    gfile.save(os.path.join(UPLOAD_FOLDER, 'rooms', gname))
                    gurl = f"/static/uploads/rooms/{gname}"
                    cursor.execute('''
                        INSERT INTO room_images (room_id, image_url, caption)
                        VALUES (?, ?, ?)
                    ''', (room_id, gurl, f"Foto fasilitas {room_number}"))

            conn.commit()
            flash(f"Data kamar {room_number} berhasil diperbarui!", "success")
            return redirect(url_for('admin_kamar_list'))

    room_facilities = [f.strip() for f in (room['facilities'] or '').split(',') if f.strip()]
    return render_template(
        'admin/kamar_form.html',
        all_facilities=ALL_FACILITIES,
        action='edit',
        room=room,
        room_facilities=room_facilities,
        gallery_images=gallery_images
    )

@app.route('/admin/kamar/hapus-foto/<int:image_id>', methods=['POST'])
@admin_required
def admin_hapus_foto_kamar(image_id):
    """Hapus satu foto dari galeri kamar."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT room_id FROM room_images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        if row:
            room_id = row['room_id']
            cursor.execute("DELETE FROM room_images WHERE id = ?", (image_id,))
            conn.commit()
            flash("Foto galeri kamar berhasil dihapus.", "success")
            return redirect(url_for('admin_kamar_edit', room_id=room_id))
    flash("Foto tidak ditemukan.", "danger")
    return redirect(url_for('admin_kamar_list'))

@app.route('/admin/kamar/hapus/<int:room_id>', methods=['POST'])
@admin_required
def admin_kamar_hapus(room_id):
    """Hapus kamar."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT room_number FROM rooms WHERE id = ?", (room_id,))
        room = cursor.fetchone()
        if room:
            cursor.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
            conn.commit()
            flash(f"Kamar {room['room_number']} berhasil dihapus dari sistem.", "success")
        else:
            flash("Kamar tidak ditemukan.", "danger")
    return redirect(url_for('admin_kamar_list'))

@app.route('/admin/foto-kos', methods=['GET', 'POST'])
@admin_required
def admin_galeri_kos():
    """Kelola galeri foto umum lingkungan kos (tampak depan, dapur, parkir, dll)."""
    with get_db() as conn:
        cursor = conn.cursor()

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()

            if not title:
                flash("Judul foto kos wajib diisi.", "danger")
                return redirect(url_for('admin_galeri_kos'))

            if 'image' not in request.files:
                flash("File gambar belum dipilih.", "danger")
                return redirect(url_for('admin_galeri_kos'))

            file = request.files['image']
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                safe_name = f"kos_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:4]}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, 'kos', safe_name))
                image_url = f"/static/uploads/kos/{safe_name}"

                cursor.execute('''
                    INSERT INTO kos_images (title, description, image_url)
                    VALUES (?, ?, ?)
                ''', (title, description, image_url))
                conn.commit()
                flash("Foto kos berhasil ditambahkan ke galeri!", "success")
                return redirect(url_for('admin_galeri_kos'))
            else:
                flash("Format file gambar tidak valid.", "danger")

        cursor.execute("SELECT * FROM kos_images ORDER BY id DESC")
        kos_images = cursor.fetchall()

    return render_template('admin/galeri_kos.html', kos_images=kos_images)

@app.route('/admin/foto-kos/hapus/<int:image_id>', methods=['POST'])
@admin_required
def admin_hapus_foto_kos(image_id):
    """Hapus foto fasilitas kos dari galeri umum."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kos_images WHERE id = ?", (image_id,))
        conn.commit()
    flash("Foto fasilitas kos berhasil dihapus.", "success")
    return redirect(url_for('admin_galeri_kos'))

@app.route('/admin/verifikasi')
@admin_required
def admin_verifikasi_list():
    """Daftar verifikasi pembayaran booking kos."""
    filter_status = request.args.get('status', 'menunggu_verifikasi')

    with get_db() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT b.*, r.room_number, r.name as room_name, r.type as room_type,
                   u.full_name as user_name, u.email as user_email, u.phone as user_phone
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            JOIN users u ON b.user_id = u.id
        '''
        params = []
        if filter_status and filter_status != 'semua':
            query += " WHERE b.status = ?"
            params.append(filter_status)

        query += " ORDER BY b.created_at DESC"
        cursor.execute(query, params)
        bookings = cursor.fetchall()

    return render_template('admin/verifikasi_list.html', bookings=bookings, current_status=filter_status)

@app.route('/admin/verifikasi/<int:booking_id>/proses', methods=['POST'])
@admin_required
def admin_proses_verifikasi(booking_id):
    """Verifikasi pembayaran: setujui (kamar jadi 'terisi') atau tolak dengan alasan."""
    action = request.form.get('action') # 'approve' atau 'reject'
    rejection_reason = request.form.get('rejection_reason', '').strip()

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            flash("Booking tidak ditemukan.", "danger")
            return redirect(url_for('admin_verifikasi_list'))

        if action == 'approve':
            # 1. Update status booking jadi 'disetujui'
            cursor.execute('''
                UPDATE bookings 
                SET status = 'disetujui', verified_at = ?
                WHERE id = ?
            ''', (now_str, booking_id))

            # 2. Status kamar otomatis berubah menjadi 'terisi'
            cursor.execute("UPDATE rooms SET status = 'terisi' WHERE id = ?", (booking['room_id'],))
            conn.commit()

            flash(f"Pembayaran kode {booking['booking_code']} BERHASIL DISETUJUI. Kamar otomatis berubah status menjadi TERISI.", "success")

        elif action == 'reject':
            if not rejection_reason:
                rejection_reason = "Bukti transfer tidak valid atau dana belum masuk ke rekening pemilik kos."

            # Update status booking jadi 'ditolak' dengan alasan
            cursor.execute('''
                UPDATE bookings 
                SET status = 'ditolak', rejection_reason = ?, verified_at = ?
                WHERE id = ?
            ''', (rejection_reason, now_str, booking_id))

            # Kamar dibuka kembali menjadi 'kosong'
            cursor.execute("UPDATE rooms SET status = 'kosong' WHERE id = ?", (booking['room_id'],))
            conn.commit()

            flash(f"Pembayaran kode {booking['booking_code']} DITOLAK dengan alasan: '{rejection_reason}'. Kamar dibuka kembali menjadi KOSONG.", "warning")

    return redirect(url_for('admin_verifikasi_list'))

# ==========================================
# RUN SERVER
# ==========================================

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=True)
