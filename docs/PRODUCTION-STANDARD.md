# Standar Produksi Video — ditetapkan pengguna 2026-11-10

Berlaku untuk SEMUA klip proyek clipper, semua platform.

| Aspek | Standar |
|---|---|
| Resolusi | 1080 × 1920 piksel (1080p) |
| Rasio aspek | 9:16 |
| Durasi | 30–60 detik (paling ideal untuk algoritma semua platform) |
| Format | MP4, codec H.264, 30 fps |
| Teks/elemen penting | Di area TENGAH frame — tidak tertutup UI aplikasi mana pun |

## Zona aman teks (turunan dari baris terakhir standar)

Frame 1080×1920. UI Shorts/platform menutupi tepi atas (±100px: ikon cari/
menu), kolom kanan (tombol like/komen/share), dan bawah (±350px: nama
channel, judul, deskripsi). Maka pita aman teks = **y 480 s.d. 1440**
(25%–75% tinggi frame), diwujudkan dalam gaya ASS kita sebagai:

- **Hook overlay**: Alignment 8, MarginV **560** (blok hook ±y 560–730).
  Diatur di hook_overlay.py (HOOK_STYLE_LINE) — SUDAH DIPERBAIKI 2026-11-10
  dari nilai lama 300 (sepertiga atas).
- **Caption word-by-word**: Alignment 2, MarginV **560** dari bawah (blok
  caption berakhir di y 1360). Skrip make_clip berikutnya WAJIB memakai
  nilai ini — diperbaiki dari nilai lama 420.

## Hasil cek kepatuhan 3 klip yang sudah jadi (ffprobe, 2026-11-10)

| Klip | Resolusi | Codec | fps | Durasi | Status |
|---|---|---|---|---|---|
| first-clip/clip.mp4 | 1080×1920 ✓ | H.264 ✓ | 30 ✓ | 37,07 dtk ✓ | LULUS teknis |
| second-clip/clip2.mp4 | 1080×1920 ✓ | H.264 ✓ | 30 ✓ | 30,07 dtk ✓ | LULUS teknis |
| podcast-pape/clip.mp4 | 1080×1920 ✓ | H.264 ✓ | 30 ✓ | 42,97 dtk ✓ | LULUS teknis |

Satu-satunya kekurangan ditemukan = **posisi teks**: ketiga klip dirender
SEBELUM standar ini ada, dengan caption MarginV 420 (di bawah pita aman).
Perbaikannya sudah diterapkan di modul (hook_overlay.py) dan aturan di
dokumen ini untuk semua render berikutnya. Ketiga klip lama TIDAK di-render
ulang kecuali pengguna memintanya — keputusan pengguna (ditawarkan
2026-11-10).

## Aturan render (cek sebelum menyerahkan klip)

1. ffprobe: 1080×1920, h264, r_frame_rate 30/1, durasi 30–60 dtk.
2. ASS: style Hook dari hook_overlay.py; style Cap MarginV 560.
3. Frame cek di detik awal (hook terlihat), tengah, akhir — teks di pita
   tengah, tidak menabrak UI kanan/bawah.
