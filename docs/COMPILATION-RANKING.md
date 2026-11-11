# Format Kompilasi Ranking — Level Selanjutnya (2026-11-11)

Konsep dari pengguna: cari beberapa video durasi pendek → cari momen viral
di masing-masing → gabungkan jadi satu video dengan ranking.

## Jawaban kelayakan: BISA, dengan 1 modul baru

Yang sudah ada dan langsung dipakai ulang:
- Pencarian sumber: yt-dlp search + ViralMint `find_breakouts` (radar)
- Transkrip per video: faster-whisper (video pendek = cepat, tidak ada risiko OOM potong 10 menit)
- Pemilihan momen + skor: VIRAL-SCORECARD.md (0–100, 7 faktor)
- Render per momen: clip_recipe.py + tracking_v2.py + hook_overlay.py, caption word-by-word, 1080×1920
- SEO + thumbnail: seo_package.py + thumbnail.py (thumbnail kompilasi: teks "TOP 5 ..." + wajah/karakter momen #1)

Yang BELUM ada dan perlu dibangun (1 modul):
- `compile_ranking.py` — penggabung:
  1. Terima daftar klip hasil render (semua sudah 1080×1920, 30fps, H.264 — format seragam, jadi concat aman)
  2. Overlay ranking per segmen: badge angka besar (#5 … #1), label sumber/judul momen, muncul 0–2 dtk tiap segmen lalu mengecil ke pojok
  3. Transisi antar segmen: xfade 0,3 dtk (FFmpeg terverifikasi punya filter concat + xfade)
  4. Intro hook 2–3 dtk: "TOP 5 [tema] — #1-nya gila" (teks saja, gaya hook standar: mulai 0 dtk, fade_scale)
  5. Urutan countdown: skor terendah dulu (#5) → tertinggi terakhir (#1) untuk retensi; penonton menunggu #1
  6. QA gabungan: ffprobe + transkrip ulang utuh untuk cek sinkron caption tiap segmen (prosedur QA yang sama seperti klip tunggal)

## Alur kerja

1. **Tentukan 1 tema dulu** — ranking hanya masuk akal dalam satu tema
   (mis. "pengakuan mengejutkan di podcast", "gol/momen bola paling absurd",
   "reaksi streamer paling lucu"). Campur tema acak = ranking terasa asal-asalan.
2. **Cari 8–12 video pendek** (usulan: durasi 1–10 menit) dalam tema itu —
   dari link pengguna dan/atau radar ViralMint/yt-dlp.
3. **Transkrip + skor semua** — ambil 1 momen terbaik per video, skor scorecard.
4. **Pilih 5 terbaik** (ambang sama: ≥75 masuk; sisanya cadangan terdokumentasi).
   Skor di sini dibandingkan ANTAR video — inilah dasar ranking-nya, bukan urutan asal.
5. **Render 5 klip pendek** per momen: target 10–20 dtk per momen agar total pas.
6. **Gabung countdown #5 → #1**, total target:
   - Shorts: ≤60 dtk (5 × ±12 dtk) atau ≤3 menit (batas Shorts sekarang)
   - Di atas itu: jadi video reguler, bukan Short
7. **Paket SEO kompilasi**: judul pola "Top 5 ..." + thumbnail kompilasi.

## Batasan jujur

- Dasar ranking = skor scorecard (penilaian terstruktur dari transkrip), BUKAN data performa nyata — sama seperti klip tunggal, belum ada analitik channel untuk kalibrasi.
- Hak cipta: kompilasi dari banyak sumber = risiko klaim Content ID lebih tinggi daripada 1 klip; durasi per sumber dibuat pendek (10–20 dtk) dan transformatif (ranking + komentar visual), tapi risiko tidak nol. Upload tetap manual oleh pengguna.
- Video "pendek" perlu definisi pasti sebelum jalan pertama: rentang durasi + apakah sumber dari link pengguna, hasil pencarian, atau campuran.

## Keputusan yang dibutuhkan untuk run pertama

1. Tema/niche kompilasi pertama
2. Jumlah ranking: Top 5 (pas Shorts) atau Top 7/Top 10 (video lebih panjang)
3. Sumber video: link dari pengguna / Muse cari sendiri / campuran
