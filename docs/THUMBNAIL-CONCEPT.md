# Konsep Thumbnail — TERKUNCI (disetujui pengguna 2026-11-10)

Modul thumbnail dibangun SENDIRI di pipeline clipper (thumbnail.py), merakit
potongan terbaik dari beberapa repo referensi — bukan menyalin satu repo utuh,
dan BUKAN berbasis preangelleo sebagai fondasi (repo itu dinilai ulang
2026-11-10: 7 stars, hanya mesin teks di atas gradasi, tidak memenuhi
standar CTR).

## Standar mutu (penggarisnya: kaidah CTR kreator besar)

1. Satu wajah dominan berekspresi kuat, mengisi 30–40% frame.
2. Teks 3–5 kata, font tebal, TIDAK mengulang judul — membuka celah penasaran.
3. Kontras ekstrem: subjek ≥30% lebih terang/gelap dari latarnya.
4. Lulus tes ukuran perangko: terbaca instan pada lebar ±168–210 px.
5. Maksimal 2–3 elemen visual; zona aman kanan-bawah kosong (badge durasi).
6. Dibuat 3 varian untuk A/B test YouTube Test & Compare.
   Patokan CTR sehat 4–8%; <4% = masalah kemasan.

## Peta referensi (boleh ambil dari >1 repo)

| Tahap | Referensi | Yang diambil | Lisensi |
|---|---|---|---|
| 1. Tambang frame + nilai wajah | jordicor/youtube_thumbnail_generator_with_AIs | Pola: deteksi wajah + penilaian kualitas (ukuran, ketajaman, frontal) untuk memilih frame terbaik; konsep dari transkrip; skoring hasil | MIT — kode boleh, tapi implementasi kita pakai MediaPipe/OpenCV (model InsightFace non-komersial, dihindari) |
| 2. Pop-out subjek | amajorai/backstage | IDE background removal + frame extraction saja | AGPL — ide saja, TANPA kode |
| 3. Komposisi overlay | Hyperkind/openshorts (YouTube Studio) | Penempatan wajah + teks, zona aman | MIT |
| 4. Layout teks | preangelleo/youtube-thumbnail-generator | Logika pecah baris seimbang + auto-fit font | MIT |
| 5. Uji mutu otomatis | jordicor (skoring) + standar CTR | Skor kemiripan → diganti: tes 168px, ukur kontras, % wajah, jumlah kata | — |
| 6. Varian A/B | YouTube Test & Compare | 3 varian per klip | — |

## Pembagian versi

- **v1** (dibangun 2026-11-10): tahap 1, 3, 4, 5, 6 + pop SEDERHANA
  (latar digelapkan & didinginkan saturasinya, area wajah tetap terang +
  sedikit boost). Output: 16:9 (1280×720) + 9:16 (1080×1920),
  pratinjau 168px, thumb-report.md berisi skor mutu per varian.
- **v2** (DIBANGUN 2026-11-10, menyusul kritik pengguna bahwa v1 terlalu
  standar/jelek/tidak clickable — catatan v1 di atas kini historis):
  desain CUTOUT POP-OUT di thumbnail.py `make_v2()` — subjek dipotong
  rembg (isnet) gaya bust kepala+bahu, outline tebal putih/gold, latar
  hasil desain (gradasi tema / scene blur), font ANTON, kata kunci dalam
  pill gold, tepi bawah bust di-fade, lubang alfa rembg diisi otomatis.
  Frame dipilih dengan bonus pose frontal (landmark YuNet); skor ekspresi
  blendshape FaceLandmarker terpasang tapi MENUNGGU lib sistem libEGL
  (instalasi apt masih berjalan) — aktif otomatis begitu tersedia.
  Varian: A gradasi, B scene, C full-bleed + banner. Output di
  outputs/<klip>/thumbs-v2/ + thumb-report-v2.md.

## Aturan gaya

- Satu kata aksen GOLD (255,215,0) — konsisten dengan hook overlay & caption.
- Teks dari hook momen klip, disusun Muse dari transkrip. Tanpa API key.
- Tanpa wajah terdeteksi (mis. klip gameplay): fallback frame tertajam +
  teks saja, DITANDAI di laporan. (Klip game tidak dibuat lagi kecuali
  pengguna meminta.)

## KEPUTUSAN STANDAR SHORTS (2026-11-10)
Pengguna memilih varian C sebagai standar thumbnail Shorts:
gabungan cut-out pop-out (outline putih, gradasi gelap) + frame
paling ekspresif + teks pertanyaan dari transkrip + pill gold.
File acuan: outputs/podcast-pape/thumbnail-final.jpg

## ATURAN KREATIVITAS (perintah pengguna, 2026-11-10)
Thumbnail TIDAK BOLEH dibuat seragam/templated. Varian C adalah
acuan PRINSIP, bukan cetakan: komposisi, warna, perlakuan subjek,
dan teks setiap thumbnail dirancang segar mengikuti konten &
momen klipnya (kreativitas per kasus). Yang tetap hanya prinsip
mutunya: zona aman, uji keterbacaan ukuran kecil, subjek ekspresif
dominan, teks membangkitkan penasaran, tidak mengulang judul.

## Aturan pengiriman (2026-11-12 — menimpa praktik lama)

Thumbnail dikirim sebagai **file terpisah** dan TIDAK PERNAH disematkan
sebagai frame pembuka di dalam video. Video harus mulai langsung
dengan konten hook di detik 0 — frame thumbnail yang diam di awal
adalah jeda yang membunuh retensi detik pertama. Praktik lama
`clip-with-cover.mp4` (thumbnail ditanam 0,5 detik di awal) sudah
dicabut oleh pengguna pada 2026-11-12; jangan dihidupkan lagi dari
catatan atau dokumen lama mana pun.
