// KosNest Main JavaScript — GSAP + Lenis + Motion One

// ─────────────────────────────────────────────────────────────────────────────
// 1. Quick Fill Login (global, dipanggil dari onclick — tidak dipakai lagi tapi disimpan)
// ─────────────────────────────────────────────────────────────────────────────
window.fillLogin = function (role) {
  const identInput = document.getElementById('identifier');
  const passInput  = document.getElementById('password');
  if (!identInput || !passInput) return;
  if (role === 'admin') {
    identInput.value = 'admin';
    passInput.value  = 'admin123';
  } else if (role === 'titut') {
    identInput.value = 'titut';
    passInput.value  = 'titut123';
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// 2. Lenis — Smooth Scroll
// ─────────────────────────────────────────────────────────────────────────────
let lenis;
if (typeof Lenis !== 'undefined') {
  lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smooth: true,
  });

  if (typeof gsap !== 'undefined') {
    gsap.ticker.add((time) => lenis.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);
  } else {
    function lenisRaf(time) {
      lenis.raf(time);
      requestAnimationFrame(lenisRaf);
    }
    requestAnimationFrame(lenisRaf);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. DOMContentLoaded
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {

  // ── GSAP Animasi Load ──
  if (typeof gsap !== 'undefined') {
    gsap.from('.navbar', {
      y: -60, opacity: 0, duration: 0.7, ease: 'power3.out',
    });
    gsap.from('main h2, main h3, .auth-card', {
      y: 40, opacity: 0, duration: 0.8, ease: 'power3.out', delay: 0.15, stagger: 0.1,
    });
    gsap.from('.alert', {
      x: 40, opacity: 0, duration: 0.45, ease: 'power2.out', stagger: 0.08,
    });
  }

  // ── Motion One — Hover efek ──
  if (typeof Motion !== 'undefined' && typeof Motion.animate === 'function') {
    const motionAnimate = Motion.animate;

    document.querySelectorAll('.btn-primary, .btn-outline-primary').forEach((btn) => {
      btn.addEventListener('mouseenter', () => motionAnimate(btn, { scale: 1.04 }, { duration: 0.15, easing: 'ease-out' }));
      btn.addEventListener('mouseleave', () => motionAnimate(btn, { scale: 1 }, { duration: 0.15, easing: 'ease-in' }));
    });

    document.querySelectorAll('.room-card').forEach((card) => {
      card.addEventListener('mouseenter', () => motionAnimate(card, { y: -6 }, { duration: 0.2, easing: 'ease-out' }));
      card.addEventListener('mouseleave', () => motionAnimate(card, { y: 0 }, { duration: 0.2, easing: 'ease-in' }));
    });

    document.querySelectorAll('.stat-slot-card').forEach((card) => {
      card.addEventListener('mouseenter', () => motionAnimate(card, { scale: 1.03 }, { duration: 0.18, easing: 'ease-out' }));
      card.addEventListener('mouseleave', () => motionAnimate(card, { scale: 1 }, { duration: 0.18, easing: 'ease-in' }));
    });
  }

  // ── Toggle Password Visibility ──
  const togglePasswordBtn  = document.getElementById('togglePassword');
  const togglePasswordIcon = document.getElementById('togglePasswordIcon');
  const passwordInput      = document.getElementById('password');
  if (togglePasswordBtn && passwordInput) {
    togglePasswordBtn.addEventListener('click', function () {
      const isHidden = passwordInput.type === 'password';
      passwordInput.type = isHidden ? 'text' : 'password';
      togglePasswordIcon.className = isHidden ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
  }

  // ── Countdown Timer Booking 24 jam ──
  document.querySelectorAll('[data-countdown]').forEach((el) => {
    const expireTimeStr = el.getAttribute('data-countdown');
    if (!expireTimeStr) return;
    const parts      = expireTimeStr.split(/[- :]/);
    const expireDate = new Date(parts[0], parts[1] - 1, parts[2], parts[3] || 0, parts[4] || 0, parts[5] || 0);

    function updateTimer() {
      const diff = expireDate - new Date();
      if (diff <= 0) {
        el.innerHTML = '<span class="text-danger fw-bold"><i class="bi bi-clock-history me-1"></i>Waktu Pembayaran Habis (Kedaluwarsa)</span>';
        return;
      }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      el.innerHTML = `
        <span class="badge bg-warning text-dark px-3 py-2 fs-6">
          <i class="bi bi-stopwatch me-1"></i>Sisa Waktu:
          <strong>${h} jam ${m} menit ${s} detik</strong>
        </span>`;
    }
    updateTimer();
    setInterval(updateTimer, 1000);
  });

  // ── Image Modal Preview ──
  const previewModalEl = document.getElementById('imagePreviewModal');
  if (previewModalEl) {
    const previewModal = new bootstrap.Modal(previewModalEl);
    const modalImage   = document.getElementById('previewModalImg');
    const modalTitle   = document.getElementById('previewModalTitle');
    document.querySelectorAll('[data-preview-img]').forEach((trigger) => {
      trigger.addEventListener('click', function (e) {
        e.preventDefault();
        const imgUrl = this.getAttribute('data-preview-img');
        const title  = this.getAttribute('data-preview-title') || 'Pratinjau Foto';
        if (modalImage && imgUrl) {
          modalImage.src = imgUrl;
          if (modalTitle) modalTitle.textContent = title;
          previewModal.show();
        }
      });
    });
  }

  // ── Room Detail Thumbnail Switcher ──
  const mainDetailImg = document.getElementById('mainDetailImage');
  const thumbnails    = document.querySelectorAll('.gallery-thumbnail');
  if (mainDetailImg && thumbnails.length > 0) {
    thumbnails.forEach((thumb) => {
      thumb.addEventListener('click', function () {
        thumbnails.forEach((t) => t.classList.remove('active'));
        this.classList.add('active');
        if (typeof gsap !== 'undefined') {
          gsap.to(mainDetailImg, {
            opacity: 0, duration: 0.15, onComplete: () => {
              mainDetailImg.src = this.getAttribute('src');
              gsap.to(mainDetailImg, { opacity: 1, duration: 0.25 });
            }
          });
        } else {
          mainDetailImg.src = this.getAttribute('src');
        }
      });
    });
  }

});
