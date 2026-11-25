import os
import unittest
from datetime import datetime, timedelta
from app import app
from database import get_db, init_db, check_and_expire_bookings
from seed_data import seed

class KosNestTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        seed() # Re-seed fresh test database
        self.client = app.test_client()

    def test_01_root_redirects_to_login(self):
        """Halaman awal berupa menu login jika belum login"""
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_02_register_auto_role_user(self):
        """Pendaftaran akun baru otomatis berperan user"""
        response = self.client.post('/register', data={
            'full_name': 'Budi Santoso',
            'username': 'budi_santoso',
            'email': 'budi_santoso@gmail.com',
            'phone': '081299998888',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = 'budi_santoso'")
            user = cursor.fetchone()
            self.assertIsNotNone(user)
            self.assertEqual(user['role'], 'user')

    def test_03_login_user_and_katalog_access(self):
        """Login Titut dan akses katalog kamar serta slot status"""
        # Login
        response = self.client.post('/login', data={
            'identifier': 'titut',
            'password': 'titut123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Katalog'.encode(), response.data)
        self.assertIn('Slot Kosong'.encode(), response.data)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM rooms WHERE status = 'kosong' LIMIT 1")
            room = cursor.fetchone()
            room_id = room['id']

        # Akses detail kamar kosong
        res_detail = self.client.get(f'/kamar/{room_id}')
        self.assertEqual(res_detail.status_code, 200)
        self.assertIn('Booking Kamar Ini Sekarang'.encode(), res_detail.data)

    def test_04_booking_flow_and_lock_room(self):
        """Booking kamar kosong -> status kamar berubah menjadi 'dipesan' dan tidak bisa dipesan orang lain"""
        # Login sebagai Titut
        self.client.post('/login', data={'identifier': 'titut', 'password': 'titut123'})

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM rooms WHERE status = 'kosong' LIMIT 1")
            room_id = cursor.fetchone()['id']
            cursor.execute("SELECT id FROM users WHERE username = 'titut'")
            titut_id = cursor.fetchone()['id']

        # Lakukan booking kamar
        res_book = self.client.post(f'/booking/{room_id}', data={'bank_name': 'BCA'}, follow_redirects=True)
        self.assertEqual(res_book.status_code, 200)
        self.assertIn('Instruksi Pembayaran E-Banking'.encode(), res_book.data)

        # Cek status kamar di database harus menjadi 'dipesan'
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM rooms WHERE id = ?", (room_id,))
            room = cursor.fetchone()
            self.assertEqual(room['status'], 'dipesan')

            # Ambil booking yang baru dibuat
            cursor.execute("SELECT id, status, booking_code FROM bookings WHERE room_id = ? AND user_id = ?", (room_id, titut_id))
            booking = cursor.fetchone()
            self.assertIsNotNone(booking)
            self.assertEqual(booking['status'], 'menunggu_pembayaran')

        # Percobaan booking lagi ke kamar yang sama harus ditolak
        res_repeat = self.client.post(f'/booking/{room_id}', data={'bank_name': 'Mandiri'}, follow_redirects=True)
        self.assertIn('tidak dapat dipesan'.encode(), res_repeat.data)

    def test_05_admin_verification_approve(self):
        """Admin memverifikasi pembayaran -> booking disetujui dan kamar otomatis berstatus 'terisi'"""
        # Login admin
        self.client.post('/login', data={'identifier': 'admin', 'password': 'admin123'})

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, room_id FROM bookings WHERE status = 'menunggu_verifikasi' LIMIT 1")
            b = cursor.fetchone()
            self.assertIsNotNone(b)
            booking_id = b['id']
            room_id = b['room_id']

        # Approve booking
        res_approve = self.client.post(f'/admin/verifikasi/{booking_id}/proses', data={'action': 'approve'}, follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM bookings WHERE id = ?", (booking_id,))
            b_updated = cursor.fetchone()
            self.assertEqual(b_updated['status'], 'disetujui')

            cursor.execute("SELECT status FROM rooms WHERE id = ?", (room_id,))
            r_updated = cursor.fetchone()
            self.assertEqual(r_updated['status'], 'terisi')

    def test_06_admin_verification_reject(self):
        """Admin menolak pembayaran dengan alasan -> status booking 'ditolak', kamar dibuka kembali menjadi 'kosong'"""
        self.client.post('/login', data={'identifier': 'admin', 'password': 'admin123'})

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, room_id FROM bookings WHERE status = 'menunggu_verifikasi' LIMIT 1")
            b = cursor.fetchone()
            booking_id = b['id']
            room_id = b['room_id']

        # Reject booking
        rejection_reason = "Nominal transfer kurang Rp 50.000"
        res_reject = self.client.post(
            f'/admin/verifikasi/{booking_id}/proses', 
            data={'action': 'reject', 'rejection_reason': rejection_reason}, 
            follow_redirects=True
        )
        self.assertEqual(res_reject.status_code, 200)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, rejection_reason FROM bookings WHERE id = ?", (booking_id,))
            b_updated = cursor.fetchone()
            self.assertEqual(b_updated['status'], 'ditolak')
            self.assertEqual(b_updated['rejection_reason'], rejection_reason)

            cursor.execute("SELECT status FROM rooms WHERE id = ?", (room_id,))
            r_updated = cursor.fetchone()
            self.assertEqual(r_updated['status'], 'kosong')

    def test_07_auto_expire_24_hours(self):
        """Aturan alur: booking tidak dibayar dalam 24 jam otomatis kedaluwarsa dan kamar dibuka lagi (kembali kosong)"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = 'titut'")
            titut_id = cursor.fetchone()['id']
            cursor.execute("SELECT id FROM rooms WHERE status = 'kosong' LIMIT 1")
            room_id = cursor.fetchone()['id']

            # Buat booking palsu yang dibuat 25 jam yang lalu
            past_time = datetime.now() - timedelta(hours=25)
            exp_time = past_time + timedelta(hours=24) # sudah lewat 1 jam lalu
            cursor.execute('''
                INSERT INTO bookings (
                    booking_code, user_id, room_id, amount, bank_name,
                    bank_account_number, bank_account_holder, status,
                    expires_at, created_at
                )
                VALUES ('KN-EXPIRED-TEST', ?, ?, 1500000, 'BCA', '123', 'Owner', 'menunggu_pembayaran', ?, ?)
            ''', (titut_id, room_id, exp_time.strftime('%Y-%m-%d %H:%M:%S'), past_time.strftime('%Y-%m-%d %H:%M:%S')))
            cursor.execute("UPDATE rooms SET status = 'dipesan' WHERE id = ?", (room_id,))
            conn.commit()

        # Jalankan pengecekan expired
        check_and_expire_bookings()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM bookings WHERE booking_code = 'KN-EXPIRED-TEST'")
            b = cursor.fetchone()
            self.assertEqual(b['status'], 'kedaluwarsa')

            # Kamar terkait harus dibuka kembali menjadi 'kosong'
            cursor.execute("SELECT status FROM rooms WHERE id = ?", (room_id,))
            r = cursor.fetchone()
            self.assertEqual(r['status'], 'kosong')

if __name__ == '__main__':
    unittest.main()
