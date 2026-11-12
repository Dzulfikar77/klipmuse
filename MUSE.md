# MUSE.md — Panduan untuk Agen AI yang Membaca Repo Ini

Terakhir diperbarui: **2026-11-12**. File ini adalah pintu masuk resmi
bagi Muse (atau agen AI lain) yang memakai repo **klipmuse** milik
Dzulfikar77. Baca file ini SEBELUM membaca dokumen lain.

## Aturan presedensi — baca ini dulu

> **Jika ada isi yang dobel atau bertentangan antar-dokumen, yang
> berlaku adalah keputusan bertanggal PALING BARU. Versi terbaru
> MENIMPA dan MENGGANTIKAN versi lama — jangan digabung, jangan
> dirata-rata, jangan dihidupkan lagi.**
>
> Urutan otoritas: (1) file ini (`MUSE.md`), (2) dokumen di `docs/`
> dengan tanggal keputusan terbaru, (3) dokumen lain. Contoh nyata:
> praktik lama `clip-with-cover.mp4` (thumbnail ditanam sebagai frame
> pembuka) **sudah dicabut 2026-11-12** — bila kamu menemukan
> penyebutannya di catatan lama mana pun, anggap tidak berlaku dan
> ikuti aturan di bawah.

## Repo ini apa

Pipeline produksi video pendek vertikal (YouTube Shorts) untuk
audiens **Amerika Serikat**, konten berbahasa Inggris:

- `pipeline/` — modul Python produksi (recipe, hook, tracking v1/v2,
  thumbnail, SEO, penggabung ranking).
- `docs/` — standar tertulis proyek (sumber kebenaran operasional).
- `tools/` — alat radar/probe (snapshot Douyin, probe TikTokApi).
- `examples/` — contoh recipe dari produksi nyata.

Layanan pendamping (ViralMint, Evil0ctal, TikTok-Api, DataForSEO MCP,
youtube-marketing-skills) adalah repo terpisah — tidak ada di sini;
perannya diatur di `docs/ORCHESTRATION.md`.

## Keadaan produksi TERKINI (2026-11-12)

1. **Format yang berjalan: kompilasi ranking** — beberapa video pendek
   satu tema, versi terbaik di-ranking countdown #5→#1 jadi satu
   video (`docs/COMPILATION-RANKING.md`, modul `compile_ranking.py`).
   Klip tunggal (gaya podcast) bukan fokus saat ini.
2. **Target kapasitas: 20+ video/hari**, produksi 4 blok × 5 video,
   tema BERBEDA-beda (±12–15 tema/hari, tema kaya maksimal 2 video),
   buffer radar ≥30 tema tervalidasi — `docs/CAPACITY-PLAN.md`.
3. **Urutan alur: TikTok dulu → YouTube Shorts → proses → upload.**
   TikTok = sinyal tren paling awal untuk audiens US + sumber utama;
   YouTube = pelengkap versi + konfirmasi skala.
4. **Pembagian kerja tool:**
   - Radar YouTube + validasi keyword: **ViralMint** (`find_breakouts`,
     `score_keyword`, `trend_velocity`) — scout-nya BELUM pernah live,
     tertahan HTTP 429 dari IP VM; dibuka oleh proxy residensial.
   - Papan hot TikTok/Douyin: **Evil0ctal v4** (live untuk Douyin).
   - Pencarian TikTok: **TikTok-Api** (terpasang 2026-11-12; live
     menunggu proxy residensial/ms_token — `docs/DOWNLOADER-SUPPORT-2026-11-12.md`).
   - Unduh TikTok per ID: **tikwm** (terbukti). Unduh YouTube: **yt-dlp**
     + PO Token (server lokal terpasang, lolosnya BELUM terbukti —
     dua tes gugur oleh 429 di langkah webpage).
   - Produksi (potong/gabung/caption/thumbnail/SEO): **pipeline repo
     ini**, bukan editor bawaan tool mana pun.
5. **Posting masih manual oleh pemilik**; di volume 20+/hari penjadwal
   pihak ketiga (Publer/Buffer) dirancang sebagai lapis posting —
   lihat `CAPACITY-PLAN.md` §5, termasuk batas upload harian YouTube
   berbasis reputasi (±10–15/hari channel baru menurut laporan
   komunitas) sehingga posting naik bertahap dan produksi membangun stok.

## Aturan keras produksi (jangan dilanggar)

- **Thumbnail TIDAK disematkan ke dalam video.** Video mulai langsung
  dengan hook di detik 0,0. Thumbnail = file terpisah. (Keputusan
  pengguna 2026-11-12, menimpa praktik `clip-with-cover` lama.)
- **Thumbnail tidak boleh templated/seragam** — rancang segar per
  tema/momen; varian C di `docs/THUMBNAIL-CONCEPT.md` hanya acuan
  prinsip. Model game: `docs/THUMBNAIL-GAME-MODEL.md`.
- **Hook standar produksi** (klip tunggal): mulai detik 0, animasi
  `fade_scale`, font 118, durasi 2,8 dtk. Fleksibilitas recipe hanya
  untuk pengecualian atas permintaan pemilik.
- **Caption word-by-word, MarginV 560**, teks di area tengah frame.
  Standar video: 1080×1920, 9:16, H.264 30fps (`docs/PRODUCTION-STANDARD.md`).
- **Pemilihan momen/ranking harus bisa diaudit**: tampilkan dasar
  keputusannya (skor scorecard 7 faktor untuk klip tunggal —
  `docs/VIRAL-SCORECARD.md`; angka views/likes terverifikasi + twist
  untuk ranking). Jangan pernah mengklaim video "akan viral".
- **QA wajib sebelum serah terima**: ffprobe + cek frame tiap segmen;
  untuk klip bercaption: transkrip ulang klip final, offset caption
  median ≈ 0 (pelajaran bug sinkron +1,98 dtk, 2026-11-10).
- **Paket SEO** mengikuti `docs/SEO-STANDARD.md` (judul ≤55 karakter,
  tags 15–20, hashtag 3–5 termasuk `#shorts`, skor paket ≥80) dan
  WAJIB menyatakan bila volume keyword belum tervalidasi DataForSEO.
- **Jangan render klip game lagi** kecuali pemilik meminta (keputusan
  2026-11-09: dua klip game sudah cukup).
- **Kredit kreator sumber selalu dicantumkan** di deskripsi kompilasi.
- Cookie/token pengguna tidak pernah masuk repo (lihat `.gitignore`)
  dan tidak pernah diminta lewat chat — selalu sebagai file.

## Urutan baca yang disarankan

1. `MUSE.md` (file ini) → 2. `docs/ORCHESTRATION.md` →
3. `docs/CAPACITY-PLAN.md` → 4. `docs/COMPILATION-RANKING.md`
(format berjalan) → 5. standar terkait tugasmu (`PRODUCTION-STANDARD`,
`VIRAL-SCORECARD`, `SEO-STANDARD`, `THUMBNAIL-CONCEPT`, `RECIPE`).

## Mulai cepat

```bash
pip install -r requirements.txt
cd pipeline
python3 clip_recipe.py ../examples/como-president.recipe.json   # contoh recipe klip tunggal
python3 compile_ranking.py --help                               # penggabung kompilasi ranking
```
