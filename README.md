# KlipMuse

Pipeline clipping YouTube Shorts yang digerakkan AI: dari video panjang
menjadi klip vertikal 9:16 dengan caption word-by-word, hook overlay,
tracking wajah/pembicara, thumbnail standar CTR, dan paket SEO —
dengan pemilihan momen yang **bisa diaudit** (scorecard tertulis,
bukan potongan asal).

Dibangun dan dipakai dalam produksi nyata sejak Nov 2026: 5 produksi
selesai (4 klip tunggal podcast & wawancara olahraga + 1 kompilasi
ranking Top 5), termasuk satu klip ujian dengan skor viral 89/100
dan paket SEO 100/100. **Format produksi saat ini: kompilasi ranking**
dengan target kapasitas 20+ video/hari — lihat `docs/CAPACITY-PLAN.md`.

> **Untuk agen AI (Muse dan sejenisnya): baca [`MUSE.md`](MUSE.md)
> terlebih dahulu.** Di sana ada keadaan terbaru proyek, aturan keras
> produksi, dan aturan presedensi dokumen (versi terbaru menimpa yang
> lama bila ada isi dobel/bertentangan).

## Cara kerja (5 tahap)

1. **Radar sumber** — cari video yang sedang meledak (ViralMint
   `find_breakouts`, radar Douyin via Evil0ctal, Reddit Rising).
2. **Validasi keyword** — `score_keyword` / `trend_velocity` /
   autocomplete YouTube US sebelum memotong.
3. **Pemilihan momen** — transkrip penuh dibaca, semua kandidat
   dinilai dengan scorecard viral 7 faktor (0–100): ≥75 render
   duluan, 60–74 cadangan, <60 lewati. Lihat `docs/VIRAL-SCORECARD.md`.
4. **Produksi** — recipe JSON per klip → tracking v2 (layout per
   adegan + pembicara aktif) → hook → caption word-by-word →
   **QA sinkron** (transkrip ulang klip final, offset caption ≈ 0).
5. **Paket rilis** — thumbnail segar per klip (tidak templated) +
   paket SEO yang diskor (judul/tags/hashtag/komentar pin).

Blueprint lengkap: `docs/ORCHESTRATION.md`.

## Struktur

```
pipeline/   Modul inti (saling impor secara flat — jalankan dari folder ini)
  clip_recipe.py   Recipe JSON -> momen (indeks kata + anchor) + ASS caption/hook
  compile_ranking.py  Penggabung kompilasi ranking Top 5 (badge, intro, xfade) — format berjalan
  hook_overlay.py  Hook overlay ASS, 6 preset animasi, default produksi teruji
  tracking.py      Tracking v1: mode face / motion / full
  tracking_v2.py   Deteksi adegan, layout per adegan, pembicara aktif (gerakan mulut)
  thumbnail.py     Thumbnail standar CTR: YuNet + skor ekspresi + cut-out
  seo_package.py   Paket SEO dari autocomplete YouTube + skor paket 0-100
  models/          Tempat model ONNX/Task (tidak di-commit, lihat models/README.md)
docs/       Standar tertulis: produksi, scorecard, SEO, thumbnail, recipe, orkestrasi,
            kompilasi ranking, rencana kapasitas 20+/hari, catatan dukungan downloader
examples/   Contoh recipe JSON dari klip produksi nyata
tools/      radar_hot.py — snapshot papan hot-search Douyin (butuh checkout Evil0ctal v4)
            tiktokapi_probe.py — probe sesi TikTok-Api (butuh venv TikTokApi + Playwright)
assets/     Font Anton (tidak di-commit, lihat assets/fonts/README.md)
```

## Kebutuhan

- Python 3.12, FFmpeg (dengan libass), yt-dlp + faster-whisper untuk
  unduh & transkrip (lihat `requirements.txt`)
- Modul vision (thumbnail/tracking): `requirements-vision.txt`
  (OpenCV, MediaPipe, Pillow, rembg, onnxruntime) + file model di
  `pipeline/models/`
- Standar produksi: 1080×1920, 9:16, 30–60 detik, H.264 30 fps,
  teks di area tengah frame — `docs/PRODUCTION-STANDARD.md`

## Mulai cepat

```bash
pip install -r requirements.txt
cd pipeline
python3 clip_recipe.py ../examples/como-president.recipe.json
```

## Catatan kejujuran

- Klip **tidak dijamin viral** — scorecard adalah penilaian
  terstruktur atas transkrip dan sinyal tren, bukan data performa
  channel. Analitik channel (OAuth) adalah lapis umpan balik yang
  dirancang di `docs/ORCHESTRATION.md`.
- Paket SEO memakai bukti autocomplete YouTube; volume keyword asli
  membutuhkan DataForSEO aktif.
- Kode ini adalah pipeline produksinya; layanan pihak ketiga yang
  dipakai bersama (ViralMint, Evil0ctal, DataForSEO MCP,
  youtube-marketing-skills) adalah repo masing-masing dan tidak
  termasuk di sini.

## Lisensi

MIT — lihat `LICENSE`.
