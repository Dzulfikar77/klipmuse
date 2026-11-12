# Riset dukungan unduh tambahan — 2026-11-12

Pertanyaan pengguna: untuk download video, apakah perlu support lain dari GitHub (jika butuh & menunjang)?

## Celah nyata pipeline kita (yang dinilai)

1. Unduh TikTok per ID/URL — SUDAH TERATASI (tikwm detail endpoint, terbukti di produksi fancy cafe).
2. **Pencarian/penemuan versi TikTok (keyword/hashtag) — CELAH.** Endpoint search tikwm timeout; user-posts 403.
   Sekarang penemuan versi mengandalkan riset web + template ViralReel + KYM.
3. Cadangan bila tikwm mati — belum ada.
4. YouTube — terhalang 429 di level IP; bukan soal tool (semua extractor dari IP ini kena dinding sama).

## Kandidat yang diperiksa (status per Nov 2026)

| Repo | Status | Nilai untuk kita | Putusan |
|---|---|---|---|
| davidteather/TikTok-Api (±6,7 rb bintang, MIT, v7.2.1, commit terakhir 24 Agu 2026) | Aktif, satu-satunya wrapper TikTok open-source yang dinilai layak pasang oleh dua ulasan 2026 | Punya search + trending + hashtag + unduh bytes — mengisi celah #2. TAPI butuh ms_token dari browser (kedaluwarsa hitungan jam) dan proxy residensial agar stabil | **Pasang nanti, setelah proxy aktif** — jadi lapis radar/pencarian, bukan pengganti tikwm |
| JoeanAmier/TikTokDownloader (DouK-Downloader, ±17,4 rb bintang, GPL-3.0, rilis 5.8 Sep 2026, commit akhir Okt 2026) | Aktif | Unduh batch TikTok/Douyin + mode API. TAPI algoritma parameter enkripsi/signing resmi TIDAK dirawat lagi oleh author (bawa generator sendiri) dan banyak fungsi butuh cookie. Masih satu keluarga pendekatan dengan Evil0ctal yang sudah kita jalankan | Cadangan bila tikwm goyah — tes hanya saat dibutuhkan |
| imputnet/cobalt (±44,8 rb bintang, AGPL) | Branch main sepi sejak 6 Apr 2026 — tanda bahaya untuk extractor | Layanan UI/API, bukan library pipeline; instance publiknya sendiri diblokir YouTube sejak 2025; dari IP kita tetap kena 429 yang sama | **Lewati** |
| juanbindez/pytubefix (v11.1.0, Sep 2026) | Aktif | Generator PO Token bawaannya dilaporkan rusak (issue #661/#674); dua analisis independen menilai redundan terhadap yt-dlp | **Lewati** |
| yt-dlp (yang sudah kita pakai) | Rilis stabil berjalan (2026.08.19 di hulu; venv kita 2026.10.26) | Tetap extractor terbaik & tercepat diperbaiki | Pertahankan; jadikan `yt-dlp -U`/update berkala bagian dari ritual awal blok produksi |

## Catatan pemasangan (2026-11-12, persetujuan pengguna "Oke setuju pasang")

- **TERPASANG**: TikTokApi **7.3.3** di venv khusus `~/workspace/clipper-project/.venv-tiktokapi`
  (tidak mencampuri venv ViralMint) + Playwright Chromium penuh & headless shell (chromium-1254) di
  `~/.cache/ms-playwright/`. Impor terverifikasi. Skrip probe: `tiktokapi_probe.py` (sesi anonim → info video
  @leehoustonx 7703227788160961806; proxy egress diteruskan eksplisit ke Playwright dari env).
- **Probe live BELUM lolos — terhalang di lapis jaringan, bukan library**: Chromium gagal membangun tunnel
  lewat proxy egress runtime (`ERR_TUNNEL_CONNECTION_FAILED` ke tiktok.com), pada kedua mode proxy Playwright
  (context & launch). Kontrol: curl lewat proxy yang sama ke tiktok.com = 200. Jadi ini ketidakcocokan
  Chromium ↔ proxy egress VM, sekelas dengan kegagalan msToken Evil0ctal lewat jalur yang sama.
- Konsekuensi sesuai rancangan awal: **pemakaian live TikTokApi menunggu proxy residensial** (proxy standar
  yang bisa dipakai Chromium) dan/atau ms_token pengguna. Tidak ada tembakan lanjutan yang diulang-ulang.

## Kesimpulan

Tidak ada repo yang menggantikan fondasi sekarang. Satu-satunya yang benar-benar menunjang celah nyata
(pencarian TikTok) adalah TikTok-Api, dan dia baru berguna setelah proxy residensial aktif karena
kebutuhan ms_token + IP bersihnya sama dengan yang menghalangi Evil0ctal selama ini. Support yang paling
menunjang justru bukan downloader baru: proxy (sudah direncanakan) + yt-dlp selalu mutakhir + batch_source.py milik kita.
