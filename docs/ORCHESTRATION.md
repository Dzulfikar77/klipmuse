# Orkestrasi ViralMint — Blueprint (2026-11-11)

Tujuan: ViralMint tidak dipakai sendirian. Ia jadi **satu lapis** dalam
sistem yang lebih kuat — kekurangannya ditutup modul lain, kelebihannya
(scouting + skor viral) dipakai penuh.

## Alur (5 lapis)

### Lapis 1 — Radar sumber (menjawab: video apa yang layak di-clip?)
- **ViralMint `find_breakouts` / `scout_trending`** — YouTube, ambang 70+.
  Skor viral: engagement 30% + kecepatan views 25% + kebaruan 20% +
  views mentah 15% + likes 10%, plus outlier vs rata-rata channel.
- **Evil0ctal/Douyin_TikTok_Download_API** (TERPASANG 2026-11-11,
  lihat catatan versi di bawah) — data TikTok/Douyin self-hosted,
  pengganti TikHub berbayar yang selama ini jadi syarat scout
  TikTok di ViralMint. Peran sekarang: radar tren.
- **Reddit Rising** (praktik radar, belum jadi modul) — tab Rising =
  sinyal paling awal; postingan Rising yang menautkan video YouTube
  bisa masuk antrean sumber. ViralMint sendiri hanya memakai Reddit
  lewat `scout_news` + sinyal di `trend_velocity` (bukan sumber video).
- **`scout_news`** — 12 sumber berita untuk topik dari headline.

### Lapis 2 — Validasi keyword (sebelum memotong)
- ViralMint: `score_keyword`, `rising_keywords`, `trend_velocity`
  (termasuk sinyal Google Trends + Reddit), `get_search_demand`
  (autocomplete YouTube asli).
- **DataForSEO MCP** (sudah ter-clone, BELUM aktif — menunggu akun +
  deposit ±$50 dari pengguna): volume & kesulitan keyword asli,
  lokasi US 2840 / en. Menutup celah terbesar lapis ini.
- Output lapis ini memengaruhi pilihan momen dan judul sejak awal,
  bukan ditempel di akhir.

### Lapis 3 — Pemilihan momen (pendapat ganda)
- **Scorecard kita** (VIRAL-SCORECARD.md, 7 faktor, 0–100) atas
  transkrip penuh: ≥75 render duluan, 60–74 cadangan, <60 lewati.
- **ViralMint `suggest_clips` / `extract_viral_clips`** sebagai
  pendapat kedua mesin — momen yang dipilih kedua sistem = prioritas;
  selisih besar = diperiksa manual.
- **`analyze_competitor`** untuk pola video sejenis yang sudah meledak.

### Lapis 4 — Produksi (pipeline kita, BUKAN editor ViralMint)
- Recipe JSON (`clip_recipe.py`) → tracking v2 (layout per adegan +
  pembicara aktif) → hook standar produksi → caption word-by-word →
  QA sinkron (transkrip ulang klip final, offset median ≈ 0) →
  thumbnail segar per klip (tidak templated) → paket SEO
  (SEO-STANDARD.md, skor ≥80) → clip.mp4 + clip-with-cover.mp4.
- 22 tool editing ViralMint dan generator video-dari-naskah tidak
  dipakai: sudah tertutup pipeline sendiri / beda jenis konten.

### Lapis 5 — Umpan balik (BELUM ada — penutup loop)
- **YouTube OAuth + youtube-marketing-skills** (sudah terpasang,
  belum terhubung): analitik channel asli → CTR & retensi klip yang
  sudah tayang dipakai mengkalibrasi bobot scorecard dan ambang
  breakout. Tanpa lapis ini, skor masih penilaian terstruktur,
  bukan data terukur.

## Yang menguatkan, diringkas
| Kelemahan ViralMint sendiri | Penutupnya |
|---|---|
| Scout TikTok butuh TikHub berbayar | Evil0ctal (MCP self-hosted) |
| Reddit bukan sumber video | Radar Rising → tautan YouTube → scout kita |
| Tanpa volume keyword asli | DataForSEO MCP |
| Pilihan momen = satu pendapat AI | Scorecard kita sebagai pemeriksa silang |
| Editing kalah detail dari pipeline kita | Pipeline sendiri (tracking v2 + recipe) |
| Tanpa umpan balik performa channel | YouTube OAuth + analitik |

## Status jujur
- Lapis 3–4 sudah terbukti jalan (4 klip selesai).
- Lapis 1–2: tool-nya ada, tapi scout ViralMint **belum pernah
  dijalankan live** di proyek ini — semua sumber klip sejauh ini
  pemberian pengguna. Proof run pertama masih menunggu niche.
- Lapis 5 menunggu OAuth pengguna.

## Catatan pemasangan Evil0ctal (2026-11-11)
- Yang terpasang: **branch v4** di `evil0ctal-v4/` (REST FastAPI di
  127.0.0.1:18080, venv sendiri). Alasan: **v5 (main) wajib Docker** —
  Postgres 17 + TimescaleDB + Redis 8 + kontainer browser, total
  plafon ±3,5 GB — dan VM ini tidak punya Docker. v4 ringan dan cukup
  untuk radar. MCP bawaan hanya ada di v5; di v4 kita memakai REST +
  crawler-nya langsung.
- Patch lokal wajib di VM ini (4 titik: `crawlers/douyin/web/utils.py`,
  `crawlers/tiktok/web/utils.py`, dan `get_*_headers` di kedua
  `web_crawler.py`): proxy config kosong → fallback ke env egress
  proxy. Tanpa patch, semua request platform gagal
  `SSL WRONG_VERSION_NUMBER`.
- **Terverifikasi LIVE**: papan hot-search Douyin — 51 topik trending
  + nilai hot, tanpa cookie pengguna. Runner:
  `cd evil0ctal-v4 && ./venv/bin/python radar_hot.py` → snapshot JSON
  ke `radar-snapshots/`.
- **Belum jalan**: data per-video TikTok (web + app API sama-sama
  ditolak 403/gagal) — msToken asli timeout lewat proxy VM dan cookie
  contoh bawaan repo sudah basi. Membukanya butuh **cookie TikTok
  segar milik pengguna** di config crawler (langkah pengguna, jangan
  lewat chat). Douyin per-video juga gagal dengan cookie contoh.
- Server tidak otomatis hidup setelah VM diganti. Menyalakan lagi:
  `cd evil0ctal-v4 && nohup ./venv/bin/python -m uvicorn app.main:app
  --host 127.0.0.1 --port 18080 > server.log 2>&1 &`
