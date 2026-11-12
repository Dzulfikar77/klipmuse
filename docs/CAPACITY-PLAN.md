# CAPACITY-PLAN.md — Rancangan Kapasitas 20+ Video/Hari

Ditulis 2026-11-12 atas keputusan pengguna: target produksi **20+ video kompilasi ranking per hari**.
Melengkapi `COMPILATION-RANKING.md` (format) dan standar Jalur Kilat (target ≤45 mnt/video dari tema terkunci).
Format yang berlaku: kompilasi ranking Top 5, sumber dua jalur (TikTok via tikwm + YouTube via yt-dlp + proxy residensial).

## 1. Definisi target

"20+ video/hari" = 20+ video **selesai produksi** (file final + thumbnail terpisah + paket SEO) terkirim sebagai batch,
plus masuk antrean posting. Produksi dan posting adalah dua kapasitas terpisah — lihat §5 soal batas posting platform.

## 2. Matematika throughput (dari angka produksi fancy cafe yang terukur)

| Tahap | Waktu/video | Cara diskalakan |
|---|---|---|
| Pilih tema dari buffer radar | ±0 (sudah tervalidasi) | Buffer selalu berisi ≥30 tema siap (stok 1,5 hari) |
| Unduh 5–7 sumber | 5–10 mnt (paralel dalam batch) | Semua unduhan satu batch jalan bersamaan, bukan satu-satu |
| Verifikasi frame | 2–3 mnt | Satu contact sheet gabungan per batch |
| Kunci ranking (views/likes live) | ±2 mnt | Angka ditarik otomatis dari tikwm/yt-dlp |
| Render (compile_ranking) | 7–12 mnt mesin | **Bottleneck utama** — antrean render sekuensial di VM ini |
| Thumbnail | ±5 mnt | 1 desain kuat per tema (prinsip panel, tetap dirancang segar per tema) |
| Paket SEO | 3–5 mnt | Dari template, angka terisi otomatis |
| QA kilat | 3–5 mnt | ffprobe + cek frame terprogram; tidak boleh dipotong |

Antrean render adalah tahap penentu: 20 video × ±10 mnt ≈ **3–3,5 jam render murni/hari** — muat dalam sehari
karena tahap lain tumpang tindih (selagi antrean render berjalan, batch berikutnya sedang diunduh & diverifikasi).
Siklus efektif kondisi tunak (steady state): ±1 video per 12–15 menit setelah pipa penuh.

## 3. Arsitektur: dari "satu-satu" ke "blok batch"

Produksi berjalan dalam **4 blok × 5 video** per hari:

1. **Buffer radar (lapis pasokan).** Radar (Evil0ctal/Douyin sebagai sinyal, tikwm untuk angka TikTok,
   scout YouTube bila jalur proxy hidup, web/Reddit Rising) menjaga stok ≥30 tema lolos gerbang validasi
   5 cek. Tanpa buffer, produksi mulai dari riset nol — itulah yang membuat run pertama makan 85 menit.
2. **Persetujuan per batch.** Pengguna menyetujui tema per blok (1 keputusan untuk 5 tema), bukan per video.
   Video yang gagal QA ditandai sebagai pengecualian, bukan menghentikan blok.
3. **Sumber paralel.** Semua 25–35 klip satu blok ditarik bersamaan: jalur TikTok (tikwm) dan jalur YouTube
   (yt-dlp + PO Token + proxy residensial) berjalan berdampingan; satu kompilasi boleh campur sumber.
4. **Antrean render.** Satu runner mengerjakan antrean render sekuensial; blok berikutnya disiapkan selagi render berjalan.
5. **QA + kemas batch.** QA kilat terprogram per video; hasil blok = 5 video + 5 thumbnail (file terpisah) + 5 paket SEO + 1 laporan batch.

Urutan sumber per keputusan pengguna 2026-11-12: **TikTok dulu** (sinyal & sumber utama), **YouTube Shorts sebagai
pelengkap** (versi yang tidak ada di TikTok) — peran proxy menyusut jadi pendukung jalur YouTube saja,
estimasi turun ke ±10–20 GB/bln. **Aturan thumbnail (pengguna, 2026-11-12): thumbnail TIDAK disematkan sebagai
frame pembuka video** — video mulai langsung dengan konten hook di detik 0; thumbnail dikirim sebagai file terpisah.

## 4. Otomasi yang harus dibangun (urutan bangun)

1. `batch_source.py` — unduh paralel banyak ID/URL (tikwm + yt-dlp via ytdl.sh), laporan sukses/gagal per item.
2. `render_queue.py` — antrean render compile_ranking dari banyak config JSON, jalan sekuensial, resume bila terputus.
3. QA terprogram — contact sheet otomatis per video + cek ffprobe massal, output daftar lolos/gagal.
4. Generator paket SEO dari template (judul Top 5, kredit kreator, timestamp, angka ranking terisi dari data sumber).
5. Pengisi buffer radar terjadwal — snapshot tren + kandidat tema masuk file shortlist bergulir.

## 5. Lapisan posting — batas platform yang sebenarnya

- Posting manual gugur di volume ini: 20 × 5–10 mnt = 2–3,5 jam/hari hanya untuk upload.
  **Alat penjadwal pihak ketiga menjadi wajib**, bukan opsional (harga dicek 2026-11-12 dari halaman penyedia):
  - Publer Professional **$12/bln** (3 akun) — termurah yang layak.
  - Buffer **±$6/channel/bln** (±$18 untuk YouTube+TikTok+IG); paket berbayar = antrean terjadwal nyaris tak terbatas (fair-use 5.000).
  - Metricool Starter **$25/bln**; paket gratisnya (20 posting/bln) tidak cukup untuk ±600 posting/bln.
  - Postiz **$29/bln** cloud, atau gratis self-host (butuh Docker — VM ini tidak punya; bukan rute sekarang).
- **Batas upload harian YouTube tidak dipublikasikan resmi** dan berbasis reputasi channel: laporan komunitas
  konsisten di kisaran ±10–15/hari untuk channel baru, naik ke 50–100 untuk channel mapan terverifikasi.
  Konsekuensi desain: **produksi boleh 20+/hari sejak awal, posting naik bertahap** (mis. 5 → 10 → 15 → 20+/hari
  mengikuti riwayat channel). Selisihnya menjadi **stok video cadangan** — justru sehat untuk momentum:
  saat tren meledak, kita posting dari stok, bukan mulai produksi.
- API resmi YouTube bukan rute posting utama di volume ini: kuota bawaan 10.000 unit/hari ÷ 1.600 unit/upload ≈ 6 upload/hari.

## 6. Anggaran berjalan (estimasi di volume 20/hari)

| Item | Estimasi |
|---|---|
| Proxy residensial (jalur YouTube, 50–60 GB/bln @ $1/GB DataImpulse PAYG) | $50–60/bln |
| Penjadwal posting (Publer/Buffer) | $12–18/bln |
| **Total** | **±$65–80/bln** |

Kuota proxy tidak kedaluwarsa dan pembelian awal minimum $5 — mulai kecil, ukur dari pemakaian minggu pertama.

## 7. Batas jujur rancangan ini

- **Pasokan tema adalah pembatas jangka panjang**, bukan mesin: tidak setiap hari lahir 20 tema ranking kelas-atas
  yang lolos validasi. Hari sepi tren diisi tema lapis-2 dari buffer atau varian tema yang sama dengan set versi berbeda;
  lantai kualitas (angka terverifikasi, kredit kreator, QA) tidak diturunkan untuk mengejar angka.
- Risiko Content ID/klaim monetisasi kompilasi multi-sumber naik sebanding volume — sudah melekat pada format, dicatat di tiap paket SEO.
- VM ini 1,5 CPU bersama: render paralel tidak menolong (saling berebut), antrean sekuensial adalah pilihan sadar.
- Server latar (PO Token/Evil0ctal/ViralMint) di VM ini mati sendiri dalam hitungan menit–puluhan menit;
  blok produksi harus menyalakan layanannya sendiri di awal blok (pola start-stack), tidak mengandalkan proses yang "sudah jalan".

## 8. Langkah bangun berikutnya

1. Pengguna: beli proxy DataImpulse paket awal ($5) + buat akun penjadwal (Publer/Buffer) — dua-duanya akun milik pengguna.
2. Muse: bangun otomasi §4 butir 1–3, lalu **hari uji**: 1 blok 5 video diukur ujung-ke-ujung.
3. Bila hari uji lulus waktunya, naik ke 4 blok/hari; buffer radar diotomatiskan terakhir (butir 5) setelah pola blok stabil.
