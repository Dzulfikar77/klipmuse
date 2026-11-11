# Standar SEO & Metadata — Proyek Clipper (disepakati 2026-11-10)

YouTube Shorts dulu · audiens Amerika Serikat (gl=US, hl=en) · bahasa Inggris.
Melengkapi VIRAL-SCORECARD.md (memilih momen) dan THUMBNAIL-CONCEPT.md
(kemasan visual). Tiga lapis paket SEO per klip: JUDUL, DESKRIPSI, TAGAR+TAG,
plus komentar tersemat. Skor paket dihitung seo_package.py (ambang di bawah).

## Sumber keyword (bertingkat)

1. **YouTube autocomplete (AKTIF, gratis, tanpa akun)** — endpoint
   suggestqueries ds=yt, gl=US hl=en. Ini sinyal permintaan pencarian NYATA:
   frasa yang muncul = yang benar-benar diketik orang. Teknik "alphabet
   soup" (seed + a..z) untuk menambang long-tail.
2. DataForSEO (MENUNGGU akun pengguna, deposit ±$50) — volume & kompetisi
   angka pasti. Sampai aktif, paket WAJIB mencantumkan catatan:
   "volume belum divalidasi DataForSEO".
3. YouTube Analytics pasca-upload (MENUNGGU OAuth) — iterasi dari data CTR
   & sumber trafik klip sendiri.

## Judul (3 varian per klip, diskoring)

- ≤ 55 karakter (feed Shorts memotong lebih dari itu).
- Entitas/kata kunci utama di PARUH AWAL judul.
- Satu pemicu penasaran: pertanyaan, angka, atau klaim tak selesai —
  TANPA clickbait yang dibantah isi klip (membunuh retensi).
- Minimal 1 varian memakai frasa yang terbukti ada di autocomplete.
- Judul dan teks thumbnail TIDAK boleh sama persis (saling melengkapi).

## Deskripsi

- Baris 1 (±100 karakter pertama): kalimat hook yang memuat kata kunci
  utama + nama entitas — bagian ini yang tampil di pratinjau & pencarian.
- Konteks 1–2 kalimat: siapa bicara, dari acara/episode apa.
- Kredit sumber: link video full-nya (baik untuk hubungan channel &
  ditemukan penonton episode aslinya).
- CTA singkat (subscribe) — satu baris, tidak bertele-tele.
- Baris hashtag terpisah di akhir.

## Hashtag (3–5, di deskripsi)

- Wajib `#shorts` + 2–4 hashtag topik (dari autocomplete bila bisa).
- Lebih dari 15 hashtag diabaikan YouTube — kita jauh di bawah itu.

## Tags (15–20, total ≤ 500 karakter — batas YouTube)

Campuran wajib:
- 1 frasa utama persis (exact match)
- 3–4 varian dekat dari autocomplete (termasuk singkatan: ww3 vs world war 3)
- 3–4 entitas (orang, acara, channel sumber)
- 4–6 topik luas (niche klip)
- Sisa: varian ejaan/bentuk lain yang muncul di saran nyata

## Komentar tersemat (1 per klip)

Pertanyaan terbuka yang memancing jawaban (sinyal engagement), disematkan
pengguna saat upload manual. Bukan pertanyaan ya/tidak.

## Scorecard paket SEO (0–100, dihitung seo_package.py)

| Komponen | Poin |
|---|---|
| Judul terbaik: kata kunci utama hadir | 15 |
| Judul terbaik: ≤ 55 karakter | 10 |
| Judul terbaik: ada pemicu penasaran (?, angka, ":") | 10 |
| Judul terbaik: ada nama entitas | 10 |
| Deskripsi: kata kunci di 100 karakter pertama | 10 |
| Deskripsi: ada link sumber + CTA | 10 |
| Tags: jumlah 15–20 | 10 |
| Tags: ≥ 50% didukung autocomplete | 10 |
| Tags: total ≤ 500 karakter | 5 |
| Hashtag: 3–5 dan memuat #shorts | 10 |

Ambang: **≥80 kuat, kirim · 60–79 boleh, perbaiki yang bolong · <60 buat ulang.**
Skor + rincian WAJIB masuk ke seo-package.md setiap klip (menggantikan
format lama yang tanpa skor dan tanpa data keyword).
