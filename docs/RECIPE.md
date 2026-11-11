# RECIPE.md — Fondasi Recipe JSON + Hook Fleksibel

Dibangun 2026-11-10 atas pilihan pengguna: memasukkan fitur ala
ai-clipper-carbon ke proyek ini **tanpa memasang Carbon** — keputusan
edit dijadikan data (recipe JSON), bukan UI. Muse mengisi recipe,
pengguna merevisi lewat chat, render ulang murah dan bisa diaudit.

## Isi satu recipe

Satu file `recipe.json` per klip (contoh hidup:
`outputs/como-president/recipe.json`):

- `moment` — momen dipilih lewat **indeks kata** transkrip
  (`start_word`/`end_word`, inklusif) + `start_pad`/`end_pad` halus,
  atau `start_time`/`end_time`. `anchor_start`/`anchor_end` adalah
  teks jangkar yang diverifikasi terhadap transkrip saat resolusi —
  pelajaran dari bug sinkron 2026-11-10 (file potongan yt-dlp mulai
  1,98 dtk lebih awal dari yang diminta).
- `hook` — `text` (pakai `\N` untuk dua baris), `keyword` (diwarnai
  gold), `start`, `duration`, `animation`, `font_size`, `margin_v`.
- `captions` — font, size, margin_v, `max_words`, `gap_split`.
- `tracking` — `mode`: face | motion | full (fase berikut: layout
  per adegan + pembicara aktif membaca bagian ini).
- `source`, `output` — asal video dan nama file hasil.

## Hook fleksibel (`hook_overlay.py`)

`hook_event()` menerima `animation`, `margin_v`, `font_size`,
`alignment` per klip. Preset animasi: `fade_scale` (bawaan lama),
`fade`, `pop`, `zoom_out`, `rise`, `none`. **Kompatibilitas mundur
terverifikasi**: pemanggilan default menghasilkan ASS byte-identik
dengan versi sebelum upgrade, dan ASS yang dibangkitkan
`clip_recipe.build_ass()` dari recipe Como identik baris-per-baris
dengan `clip_captions.ass` produksi (131/131 event).

## Cara pakai

```bash
# Cek resolusi recipe (momen, jumlah kata, peringatan anchor)
python3 clip_recipe.py outputs/<klip>/recipe.json
```

Render berikutnya: bangun ASS lewat `build_ass(recipe, words)` dari
`clip_recipe.py`, bakar ke video hasil tracking seperti biasa.
Render bukti: `outputs/como-president/recipe-proof.mp4` (6 dtk,
hook digeser ke 1,0–4,0 dtk, animasi `pop`, font 96 — terverifikasi
dari frame: hook absen di 0,5 dtk, tampil di 2,0 dtk, hilang di
5,0 dtk).

## Tracking v2 (SELESAI 2026-11-10 malam)

`tracking_v2.py` menutup fase berikutnya: deteksi adegan (potongan
kamera), layout per adegan (`track` / `anchor` / `split` / `full`),
dan pembicara aktif dari **gerakan area mulut** antar frame
(blendshape jawOpen terbukti menipu di wide shot — kalah oleh
pendengar yang mengangguk; gerakan mulut mentah tegas 9,9 vs 1,2).
Smoothing kini hanya di dalam adegan, tidak melintasi potongan.

Bukti di segmen Como yang sama (rencana: `plan_v2.json`, klip
perbandingan: `clip-v2.mp4`, klip produksi tidak diubah):
wide shot 0–9,8 dtk → anchor otomatis di Mirwan (0,149/0,489 —
nyaris sama dengan jangkar manual produksi 0,138/0,47); close-up
9,8–27,8 → track; two-shot host 27,8–32,3 → split dua panel;
penutup 32,3–32,9 → track kembali ke Mirwan (cacat produksi —
host di tepi kiri pada detik akhir — hilang).
Batas jujur: urutan panel split dipilih per adegan; bila mulut
pembicara tertutup mikrofon, panel atas bisa terisi pembicara
yang lebih banyak bicara di adegan itu — keduanya tetap terlihat.
