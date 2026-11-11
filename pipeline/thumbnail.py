r"""
thumbnail.py — Modul thumbnail yang clickable untuk pipeline clipper proyek ini.

Langkah roadmap #2 (disepakati 2026-11-10, setelah scorecard + hook overlay):
thumbnail dibuat di pipeline kita sendiri dengan Pillow — tanpa API key dan
tanpa dependensi baru. Ide layout teksnya diadaptasi dari repo preangelleo/
youtube-thumbnail-generator (template + teks besar kontras tinggi), yang
direkomendasikan 2026-11-10 sebagai yang paling cocok untuk proyek ini;
repo itu sendiri TIDAK dipasang, karena pip sistem di mesin ini
externally-managed (PEP 668) dan nilai intinya sudah direplikasi di sini.
Kalau nanti mau, pasang di venv dengan `pip install youtube-thumbnail-generator`.

Spesifikasi gaya (selaras dengan hook overlay, biar identitas klip konsisten):
- Frame terbaik klip sebagai latar (wajah ekspresif, dari proses clipping).
- Teks 3–4 kata, EN, HURUF BESAR — celah penasaran yang sama dengan hook
  overlay momen itu. Contoh: "ARE WE IN WW3?" / "THEY PAID HIM $5".
- 1 kata kunci diwarnai gold (255, 215, 0 — sama dengan kata aktif caption
  dan kata kunci hook overlay), sisanya putih; outline hitam tebal +
  drop shadow, jadi terbaca di atas frame apa pun.
- Font: DejaVu Sans Bold (tersedia di /usr/share/fonts), ukuran auto-fit:
  mengecil sampai teks muat dalam margin, tidak pernah terpotong.
- Posisi default: sepertiga ATAS frame (sama seperti hook overlay),
  dengan scrim gradien gelap di belakang teks agar kontras terjamin
  tanpa menutupi wajah di tengah. Opsi position="bottom" tersedia
  kalau wajahnya justru di atas.
- Output: 9:16 (1080x1920, untuk Shorts) dan 16:9 (1280x720, untuk
  video panjang) — keduanya dari frame yang sama, crop tengah.

CARA PAKAI:

    import sys
    sys.path.insert(0, "pipeline")  # folder modul ini
    from thumbnail import make_thumbnail, make_thumbnail_from_clip

    # Dari frame yang sudah ada (mis. frame_clip_21.jpg dari proses clipping):
    make_thumbnail("outputs/podcast-pape/frame_clip_21.jpg",
                   "ARE WE IN WW3?", keyword="WW3?",
                   out_path="outputs/podcast-pape/thumbnail-9x16.jpg")

    # Versi 16:9 dari frame 16:9 (mis. frame_sec_22.jpg 1280x720):
    make_thumbnail("outputs/podcast-pape/frame_sec_22.jpg",
                   "ARE WE IN WW3?", keyword="WW3?",
                   out_path="outputs/podcast-pape/thumbnail-16x9.jpg",
                   aspect="16:9")

    # Langsung dari file klip (ambil frame di detik ke-t, lalu buat thumbnail):
    make_thumbnail_from_clip("outputs/podcast-pape/clip.mp4", seconds=21,
                             text="ARE WE IN WW3?", keyword="WW3?",
                             out_path="outputs/podcast-pape/thumbnail-9x16.jpg")

Fungsi make_thumbnail() mengembalikan path output. Semua parameter posisi
dan warna bisa di-override per klip bila framing berbeda.
"""

import subprocess

from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)          # sama dengan kata kunci hook overlay
BLACK = (0, 0, 0)

SIZES = {
    "9:16": (1080, 1920),
    "16:9": (1280, 720),
}


def _fit_font(draw, text_lines, max_width, start_size):
    """Turunkan ukuran font sampai baris terpanjang muat dalam max_width."""
    size = start_size
    while size > 24:
        font = ImageFont.truetype(FONT_BOLD, size)
        if max(draw.textlength(line, font=font) for line in text_lines) <= max_width:
            return font
        size -= 6
    return ImageFont.truetype(FONT_BOLD, size)


def _wrap(text, draw, font, max_width):
    """Pecah teks jadi maksimal 2 baris yang seimbang, per kata."""
    words = text.upper().split()
    if len(words) <= 2:
        return [" ".join(words)]
    best = None
    for split in range(1, len(words)):
        lines = [" ".join(words[:split]), " ".join(words[split:])]
        width = max(draw.textlength(line, font=font) for line in lines)
        imbalance = abs(len(lines[0]) - len(lines[1]))
        score = (width, imbalance)
        if best is None or score < best[0]:
            best = (score, lines)
    lines = best[1]
    # Kalau satu baris saja sudah muat, jangan pecah.
    if draw.textlength(text.upper(), font=font) <= max_width:
        return [text.upper()]
    return lines


def _draw_text_with_outline(draw, xy, text, font, fill, outline=BLACK,
                            outline_width=6, shadow_offset=(0, 6)):
    """Teks dengan outline hitam tebal + drop shadow, per kata (untuk keyword gold)."""
    x, y = xy
    # Shadow dulu (hitam semi-transparan via offset, digambar sebagai teks hitam).
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font,
              fill=(0, 0, 0), stroke_width=outline_width, stroke_fill=BLACK)
    draw.text((x, y), text, font=font, fill=fill,
              stroke_width=outline_width, stroke_fill=BLACK)


def _draw_line_mixed_colour(draw, x, y, line, font, keyword):
    """Gambar satu baris; kata kunci (case-insensitive) berwarna gold."""
    words = line.split()
    kw = (keyword or "").upper()
    cursor = x
    for i, word in enumerate(words):
        colour = GOLD if word.strip("?!.,") == kw.strip("?!.,") and kw else WHITE
        if i > 0:
            cursor += draw.textlength(" ", font=font)
        _draw_text_with_outline(draw, (cursor, y), word, font, colour)
        cursor += draw.textlength(word, font=font)
    return cursor


def _top_scrim(img, height_fraction=0.42):
    """Gradien gelap di atas frame agar teks terbaca; memudar ke bawah."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    h = int(img.size[1] * height_fraction)
    for y in range(h):
        alpha = int(150 * (1 - y / h) ** 1.5)
        od.line([(0, y), (img.size[0], y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _bottom_scrim(img, height_fraction=0.42):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    h = int(img.size[1] * height_fraction)
    top = img.size[1] - h
    for y in range(top, img.size[1]):
        alpha = int(150 * ((y - top) / h) ** 1.5)
        od.line([(0, y), (img.size[0], y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _crop_to_aspect(img, target_w, target_h):
    """Crop tengah ke rasio target (tanpa distorsi)."""
    target_ratio = target_w / target_h
    w, h = img.size
    ratio = w / h
    if ratio > target_ratio:  # terlalu lebar -> potong kiri-kanan
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:  # terlalu tinggi -> potong atas-bawah
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)


def make_thumbnail(frame_path, text, keyword=None, out_path=None,
                   aspect="9:16", position="top", margin=70):
    """Buat thumbnail dari satu frame.

    frame_path : JPG/PNG frame terbaik klip (1080x1920 untuk 9:16,
                 1280x720 untuk 16:9 — atau apa pun, di-crop tengah).
    text       : 3–4 kata (di-UPPERCASE otomatis).
    keyword    : kata yang diwarnai gold; default kata terakhir.
    aspect     : "9:16" (1080x1920, Shorts) atau "16:9" (1280x720).
    position   : "top" (default, selaras hook overlay) atau "bottom".
    """
    if aspect not in SIZES:
        raise ValueError(f"aspect harus salah satu dari {list(SIZES)}")
    target_w, target_h = SIZES[aspect]
    img = Image.open(frame_path).convert("RGB")
    img = _crop_to_aspect(img, target_w, target_h)

    if position == "top":
        img = _top_scrim(img)
    elif position == "bottom":
        img = _bottom_scrim(img)
    else:
        raise ValueError("position harus 'top' atau 'bottom'")

    draw = ImageDraw.Draw(img)
    max_width = target_w - 2 * margin
    start_size = 150 if aspect == "9:16" else 110
    probe = ImageFont.truetype(FONT_BOLD, start_size)
    lines = _wrap(text, draw, probe, max_width)
    font = _fit_font(draw, lines, max_width, start_size)
    # Wrap ulang dengan font final (baris bisa berubah setelah mengecil).
    lines = _wrap(text, draw, font, max_width)

    line_height = int(font.size * 1.12)
    total_h = line_height * len(lines)
    if position == "top":
        y = int(target_h * 0.09)
    else:
        y = target_h - int(target_h * 0.09) - total_h

    for line in lines:
        line_w = draw.textlength(line, font=font)
        x = (target_w - line_w) // 2
        _draw_line_mixed_colour(draw, x, y, line, font, keyword or line.split()[-1])
        y += line_height

    if out_path is None:
        stem = frame_path.rsplit(".", 1)[0]
        out_path = f"{stem}-thumbnail-{aspect.replace(':', 'x')}.jpg"
    img.save(out_path, "JPEG", quality=92)
    return out_path


def extract_frame(clip_path, seconds, out_path):
    """Ambil satu frame dari klip (FFmpeg) — frame terbaik untuk thumbnail."""
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", str(seconds), "-i", clip_path,
         "-frames:v", "1", out_path],
        check=True,
    )
    return out_path


def make_thumbnail_from_clip(clip_path, seconds, text, keyword=None,
                             out_path=None, aspect="9:16", position="top"):
    """Ambil frame di detik ke-`seconds` dari klip, lalu buat thumbnail."""
    import os
    import tempfile
    fd, frame_path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    try:
        extract_frame(clip_path, seconds, frame_path)
        return make_thumbnail(frame_path, text, keyword=keyword,
                              out_path=out_path, aspect=aspect,
                              position=position)
    finally:
        if os.path.exists(frame_path):
            os.remove(frame_path)


# =====================================================================
# v1 (konsep terkunci 2026-11-10, lihat THUMBNAIL-CONCEPT.md):
# tambang frame + nilai wajah (pola jordicor, implementasi OpenCV YuNet —
# BUKAN InsightFace yang modelnya non-komersial), pop sederhana,
# uji mutu otomatis (tes 168px, kontras, % wajah, jumlah kata),
# 3 varian per rasio untuk A/B test YouTube Test & Compare.
# Butuh opencv + numpy: jalankan dengan .venv-thumb/bin/python.
# =====================================================================
import os
import tempfile

import numpy as np

_YUNET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "models", "face_detection_yunet_2023mar.onnx")
_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        import cv2
        _detector = cv2.FaceDetectorYN.create(
            _YUNET, "", (320, 320), score_threshold=0.6)
    return _detector


def _detect_faces(bgr):
    """Daftar wajah [{x,y,w,h,score,lm}] dari frame BGR (OpenCV YuNet).

    lm = landmark (mata kanan, mata kiri, hidung, mulut kanan, mulut kiri)
    bila tersedia — dipakai untuk menolak positif palsu (tangan/baju).
    """
    det = _get_detector()
    h, w = bgr.shape[:2]
    det.setInputSize((w, h))
    _, faces = det.detect(bgr)
    out = []
    if faces is not None:
        for f in faces:
            lm = None
            if len(f) >= 14:
                lm = [(float(f[i]), float(f[i + 1]))
                      for i in range(4, 14, 2)]
            out.append({"x": int(f[0]), "y": int(f[1]), "w": int(f[2]),
                        "h": int(f[3]), "score": float(f[-1]), "lm": lm})
    return out


def _plausible_face(f, fw, fh):
    """Saring deteksi: rasio & ukuran wajar, utuh di dalam frame, dan
    geometri landmark masuk akal (mata di atas hidung di atas mulut)."""
    if not (0.5 <= f["w"] / max(f["h"], 1) <= 1.5):
        return False
    if not (0.08 * fw <= f["w"] <= 0.80 * fw):
        return False
    if f["x"] < -2 or f["y"] < -2 or f["x"] + f["w"] > fw + 2 \
            or f["y"] + f["h"] > fh + 2:
        return False
    if f["lm"]:
        (ex1, ey1), (ex2, ey2), (nx, ny), (mx1, my1), (mx2, my2) = f["lm"]
        eye_y = (ey1 + ey2) / 2
        mouth_y = (my1 + my2) / 2
        if not (eye_y < ny < mouth_y):
            return False
    return True


def _sharpness(gray, box):
    import cv2
    x, y, w, h = box
    roi = gray[max(y, 0):y + h, max(x, 0):x + w]
    if roi.size == 0:
        return 0.0
    return float(cv2.Laplacian(roi, cv2.CV_64F).var())


def pick_best_frames(video_path, n=3, sample_every=1.0, min_gap=1.5,
                     work_dir=None):
    """Sampel frame dari video, nilai wajahnya, ambil n terbaik.

    Skor wajah = 55% ukuran (target memenuhi frame), 30% ketajaman,
    15% kedekatan ke tengah. Mengembalikan list dict {path, seconds,
    face (bbox di koordinat frame asli / None), face_frac, sharp, score}.
    Tanpa wajah sama sekali: fallback ke frame tertajam, face=None
    (pemanggil wajib menandainya di laporan).
    """
    import cv2
    # Frame diambil via FFmpeg sistem (bukan VideoCapture): wheel OpenCV
    # tidak bisa decode AV1, sedangkan segmen sumber kita bisa AV1.
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True)
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        raise RuntimeError(f"tidak bisa membaca durasi: {video_path}")
    work_dir = work_dir or tempfile.mkdtemp(prefix="thumb_frames_")
    os.makedirs(work_dir, exist_ok=True)
    cands = []
    t = 0.5
    while t < max(duration, 0.6):
        path = os.path.join(work_dir, f"cand_{t:06.1f}.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video_path,
             "-frames:v", "1", "-q:v", "2", path],
            check=True)
        frame = cv2.imread(path)
        if frame is None:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fh, fw = frame.shape[:2]
        faces = [f for f in _detect_faces(frame)
                 if _plausible_face(f, fw, fh)]
        if faces:
            f = max(faces, key=lambda d: d["w"] * d["h"])
            frac = (f["w"] * f["h"]) / float(fw * fh)
            sharp = _sharpness(gray, (f["x"], f["y"], f["w"], f["h"]))
            cx = abs((f["x"] + f["w"] / 2) / fw - 0.5)
            centre = 1.0 - min(cx * 2, 1.0)
            score = (0.55 * min(frac / 0.35, 1.0)
                     + 0.30 * min(sharp / 300.0, 1.0) + 0.15 * centre)
            cands.append({"path": path, "seconds": round(t, 1),
                          "face": (f["x"], f["y"], f["w"], f["h"]),
                          "face_frac": frac, "sharp": sharp,
                          "score": score})
        else:
            cands.append({"path": path, "seconds": round(t, 1),
                          "face": None, "face_frac": 0.0,
                          "sharp": _sharpness(gray, (0, 0, fw, fh)),
                          "score": -1.0})
        t += sample_every
    faced = sorted([c for c in cands if c["face"]],
                   key=lambda c: -c["score"])
    pool = faced if faced else sorted(cands, key=lambda c: -c["sharp"])
    picked = []
    for c in pool:
        if all(abs(c["seconds"] - p["seconds"]) >= min_gap
               for p in picked):
            picked.append(c)
        if len(picked) >= n:
            break
    return picked


def _map_bbox(bbox, src_size, target_size):
    """Petakan bbox mengikuti logika _crop_to_aspect (crop tengah + resize)."""
    sw, sh = src_size
    tw, th = target_size
    tr = tw / th
    if sw / sh > tr:
        cw = int(sh * tr)
        left, top, ch = (sw - cw) // 2, 0, sh
    else:
        ch = int(sw / tr)
        left, top, cw = 0, (sh - ch) // 2, sw
    x, y, w, h = bbox
    sx, sy = tw / cw, th / ch
    return (int((x - left) * sx), int((y - top) * sy),
            int(w * sx), int(h * sy))


def _crop_around_face(img, face, tw, th, target_frac=0.42, tight=False):
    """Crop jendela di sekitar wajah agar wajah ~target_frac lebar frame.

    tight=True (untuk 9:16): jendela rapat mengikuti lebar wajah (wajah
    ~80% lebar jendela) — di frame vertikal, fraksi LUAS wajah memang
    tidak bisa setinggi di 16:9 tanpa memotong sisi kepala.
    """
    sw, sh = img.size
    x, y, w, h = face
    if tight:
        win_w = w * 1.25
        win_h = win_w * th / tw
        if win_h < h * 1.2:
            win_h = h * 1.2
            win_w = win_h * tw / th
    else:
        win_w = w / target_frac
        win_h = win_w * th / tw
        if win_h < h * 1.35:
            win_h = h * 1.35
            win_w = win_h * tw / th
    if win_w > sw:
        win_w = float(sw)
        win_h = win_w * th / tw
    if win_h > sh:
        win_h = float(sh)
        win_w = win_h * tw / th
    cx, cy = x + w / 2, y + h / 2 - h * 0.1
    left = int(min(max(cx - win_w / 2, 0), sw - win_w))
    top = int(min(max(cy - win_h / 2, 0), sh - win_h))
    crop = img.crop((left, top, left + int(win_w), top + int(win_h)))
    out = crop.resize((tw, th), Image.LANCZOS)
    sx, sy = tw / win_w, th / win_h
    face2 = (int((x - left) * sx), int((y - top) * sy),
             int(w * sx), int(h * sy))
    return out, face2


def pop_treatment(img, face):
    """Pop sederhana v1: latar digelapkan + saturasi diturunkan, area wajah
    (diperluas, tepi di-feather) tetap terang + sedikit boost.

    Mengembalikan (img_baru, kontras_persen): beda luminansi rata-rata area
    wajah vs keseluruhan gambar, dalam persen.
    """
    from PIL import ImageEnhance, ImageFilter
    if face is None:
        return img, 0.0
    bg = ImageEnhance.Brightness(
        ImageEnhance.Color(img).enhance(0.5)).enhance(0.55)
    x, y, w, h = face
    pad_w, pad_h = int(w * 0.45), int(h * 0.55)
    box = (max(x - pad_w, 0), max(y - pad_h, 0),
           min(x + w + pad_w, img.size[0]),
           min(y + h + pad_h, img.size[1]))
    subj = img.crop(box)
    subj = ImageEnhance.Contrast(
        ImageEnhance.Color(
            ImageEnhance.Brightness(subj).enhance(1.07)).enhance(1.18)
    ).enhance(1.05)
    mask = Image.new("L", (box[2] - box[0], box[3] - box[1]), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([0, 0, mask.size[0], mask.size[1]], fill=255)
    mask = mask.filter(
        ImageFilter.GaussianBlur(radius=max(min(mask.size) * 0.12, 4)))
    bg.paste(subj, (box[0], box[1]), mask)
    lum = np.asarray(bg.convert("L"), dtype=float)
    fx = lum[max(y, 0):y + h, max(x, 0):x + w]
    face_mean = float(fx.mean()) if fx.size else 0.0
    bg_mean = float(lum.mean()) or 1.0
    return bg, (face_mean - bg_mean) / bg_mean * 100.0


def _render_text(img, text, keyword, position, tw, th):
    """Scrim + teks thumbnail di atas img yang sudah berukuran final."""
    img = _top_scrim(img) if position == "top" else _bottom_scrim(img)
    draw = ImageDraw.Draw(img)
    margin = 70 if tw >= 1080 else 60
    max_width = tw - 2 * margin
    start_size = 150 if th > tw else 110
    probe = ImageFont.truetype(FONT_BOLD, start_size)
    lines = _wrap(text, draw, probe, max_width)
    font = _fit_font(draw, lines, max_width, start_size)
    lines = _wrap(text, draw, font, max_width)
    line_height = int(font.size * 1.12)
    total_h = line_height * len(lines)
    y = int(th * 0.07) if position == "top" else th - int(th * 0.07) - total_h
    for line in lines:
        line_w = draw.textlength(line, font=font)
        x = (tw - line_w) // 2
        _draw_line_mixed_colour(draw, x, y, line, font,
                                keyword or line.split()[-1])
        y += line_height
    return img


def make_variants(video_path, text, keyword=None, out_dir=None,
                  aspects=("16:9", "9:16")):
    """Bangun 3 varian thumbnail per rasio + pratinjau 168px + laporan mutu.

    Varian A: frame terbaik + pop + teks atas.
    Varian B: frame terbaik ke-2 + pop + teks bawah.
    Varian C: frame ke-3 + zoom wajah (~38% lebar) + pop + teks atas.
    Mengembalikan list dict hasil + menulis thumb-report.md di out_dir.
    """
    if out_dir is None:
        raise ValueError("out_dir wajib diisi")
    os.makedirs(out_dir, exist_ok=True)
    words = text.upper().split()
    frames = pick_best_frames(video_path, n=3)
    if not frames:
        raise RuntimeError("tidak ada frame yang bisa diambil dari video")
    results = []
    for aspect in aspects:
        tw, th = SIZES[aspect]
        tag = aspect.replace(":", "x")
        # Semua varian zoom ke wajah bila ada wajah: standar CTR menuntut
        # wajah dominan; pada sumber yang sudah close-up, jendela zoom
        # menyamai frame penuh sehingga hasilnya setara crop biasa.
        recipes = [("A", 0, "zoom", "top"), ("B", 1, "zoom", "bottom"),
                   ("C", 2, "zoom", "top")]
        for name, fi, mode, pos in recipes:
            fr = frames[min(fi, len(frames) - 1)]
            img = Image.open(fr["path"]).convert("RGB")
            if mode == "zoom" and fr["face"]:
                base, face2 = _crop_around_face(img, fr["face"], tw, th,
                                                tight=(th > tw))
            else:
                base = _crop_to_aspect(img, tw, th)
                face2 = (_map_bbox(fr["face"], img.size, (tw, th))
                         if fr["face"] else None)
            base, contrast = pop_treatment(base, face2)
            final = _render_text(base, text, keyword, pos, tw, th)
            out = os.path.join(out_dir, f"thumb-{tag}-{name}.jpg")
            final.save(out, "JPEG", quality=92)
            stamp = os.path.join(out_dir, f"thumb-{tag}-{name}-stamp168.png")
            final.resize((168, int(168 * th / tw)),
                         Image.LANCZOS).save(stamp)
            face_frac = (face2[2] * face2[3]) / (tw * th) if face2 else 0.0
            checks = [
                ("kata <= 5", len(words) <= 5, f"{len(words)} kata"),
                ("wajah terdeteksi", face2 is not None,
                 "ya" if face2 else "TIDAK - fallback frame tertajam"),
                ("wajah 20-55% frame", 0.20 <= face_frac <= 0.55,
                 f"{face_frac * 100:.0f}%"),
                ("kontras subjek >= 30%", bool(face2) and contrast >= 30,
                 f"{contrast:+.0f}%"),
            ]
            results.append({
                "file": out, "stamp": stamp, "aspect": aspect,
                "variant": name, "frame_seconds": fr["seconds"],
                "face_frac": face_frac, "contrast": contrast,
                "checks": checks,
                "verdict": ("LULUS" if all(c[1] for c in checks)
                            else "PERIKSA"),
            })
    lines = [f"# Laporan Mutu Thumbnail — {os.path.basename(video_path)}",
             "", f"Teks: **{text.upper()}** · kata kunci gold: "
             f"**{(keyword or words[-1]).upper()}**", ""]
    for r in results:
        lines.append(f"## {os.path.basename(r['file'])} — {r['verdict']}")
        lines.append(f"- Frame sumber: detik {r['frame_seconds']} · "
                     f"wajah {r['face_frac'] * 100:.0f}% frame · "
                     f"kontras {r['contrast']:+.0f}%")
        for label, ok, val in r["checks"]:
            lines.append(f"- [{'x' if ok else ' '}] {label}: {val}")
        lines.append(f"- Tes perangko: {os.path.basename(r['stamp'])} "
                     "(cek terbaca pada lebar 168px)")
        lines.append("")
    lines.append("Catatan: ambang wajah 20–55% adalah longgar untuk v1; "
                 "standar CTR ideal 30–40% (lihat THUMBNAIL-CONCEPT.md). "
                 "Kontras diukur sebelum teks digambar.")
    with open(os.path.join(out_dir, "thumb-report.md"), "w") as fh:
        fh.write("\n".join(lines))
    return results


# =====================================================================
# v2 (2026-11-10, menyusul kritik pengguna: v1 "terlalu standar, jelek,
# tidak clickable") — desain CUTOUT POP-OUT beneran:
#  - berburu frame EKSPRESIF: skor blendshape MediaPipe FaceLandmarker
#    (jawOpen + mata melebar + alis naik = ekspresi "kaget/serius"),
#    bukan cuma frame tertajam.
#  - subjek dipotong (rembg isnet) dan diberi OUTLINE tebal + bayangan,
#    ditempel di latar hasil desain (gradasi tema / scene blur) — bukan
#    lagi frame mentah + teks.
#  - font ANTON (font khas thumbnail YouTube), kata kunci dibungkus
#    PILL gold, blok teks sedikit miring (-2 derajat) untuk energi.
# Butuh: .venv-thumb (rembg, mediapipe) + model face_landmarker.task.
# =====================================================================
import os as _os
_ANTON_LOCAL = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                             "..", "assets", "fonts", "Anton-Regular.ttf")
ANTON = (_ANTON_LOCAL if _os.path.exists(_ANTON_LOCAL)
         else "/usr/share/fonts/truetype/dejavu/Anton-Regular.ttf")
_FACE_LANDMARKER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "models", "face_landmarker.task")
_landmarker = "unset"
_rembg_session = None


def _get_landmarker():
    global _landmarker
    if _landmarker == "unset":
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
            opts = vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=_FACE_LANDMARKER),
                output_face_blendshapes=True, num_faces=2)
            _landmarker = vision.FaceLandmarker.create_from_options(opts)
        except Exception:
            _landmarker = None  # lib sistem kurang -> skor ekspresi dilewati
    return _landmarker


def _expression_score(frame_path):
    """Skor ekspresi 0..1 dari blendshape; None bila landmarker tak ada."""
    lm = _get_landmarker()
    if lm is None:
        return None
    try:
        import mediapipe as mp
        res = lm.detect(mp.Image.create_from_file(frame_path))
        if not res.face_blendshapes:
            return 0.0
        bs = {c.category_name: c.score for c in res.face_blendshapes[0]}
        return float(0.40 * bs.get("jawOpen", 0)
                     + 0.25 * (bs.get("eyeWideLeft", 0)
                               + bs.get("eyeWideRight", 0)) / 2
                     + 0.25 * bs.get("browInnerUp", 0)
                     + 0.10 * bs.get("mouthFunnel", 0))
    except Exception:
        return None


def pick_expressive_frames(video_path, n=3, sample_every=0.5,
                           min_gap=1.5, work_dir=None):
    """Seperti pick_best_frames tapi skor menimbang EKSPRESI tertinggi.

    skor = 45% ekspresi + 30% ketajaman + 25% ukuran wajah.
    """
    import cv2
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path], capture_output=True, text=True)
    duration = float(probe.stdout.strip())
    work_dir = work_dir or tempfile.mkdtemp(prefix="thumb_expr_")
    os.makedirs(work_dir, exist_ok=True)
    cands, t = [], 0.25
    while t < duration:
        path = os.path.join(work_dir, f"expr_{t:06.2f}.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video_path,
             "-frames:v", "1", "-q:v", "2", path], check=True)
        frame = cv2.imread(path)
        if frame is None:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fh, fw = frame.shape[:2]
        faces = [f for f in _detect_faces(frame)
                 if _plausible_face(f, fw, fh)]
        if faces:
            f = max(faces, key=lambda d: d["w"] * d["h"])
            frac = (f["w"] * f["h"]) / float(fw * fh)
            sharp = _sharpness(gray, (f["x"], f["y"], f["w"], f["h"]))
            expr = _expression_score(path)
            # Bonus pose frontal-tegak dari landmark YuNet: kepala
            # menunduk memampatkan jarak hidung-mulut vs mata-hidung.
            frontal = 1.0
            if f.get("lm"):
                (_, ey1), (_, ey2), (_, ny), (_, my1), (_, my2) = f["lm"]
                eye_y = (ey1 + ey2) / 2
                mouth_y = (my1 + my2) / 2
                ratio = (mouth_y - ny) / max(ny - eye_y, 1.0)
                frontal = 1.0 if 0.7 <= ratio <= 1.5 else 0.45
            score = (0.45 * (expr if expr is not None else 0.3)
                     + 0.30 * min(sharp / 300.0, 1.0)
                     + 0.25 * min(frac / 0.12, 1.0)) * frontal
            cands.append({"path": path, "seconds": round(t, 2),
                          "face": (f["x"], f["y"], f["w"], f["h"]),
                          "face_frac": frac, "sharp": sharp,
                          "expr": expr, "score": score})
        t += sample_every
    cands.sort(key=lambda c: -c["score"])
    picked = []
    for c in cands:
        if all(abs(c["seconds"] - p["seconds"]) >= min_gap
               for p in picked):
            picked.append(c)
        if len(picked) >= n:
            break
    return picked


def _cutout(frame_pil, face=None):
    """Potong subjek (rembg isnet) -> RGBA ter-crop ke subjek.

    Bila `face` (bbox di koordinat frame) diberikan, hasil dipotong gaya
    BUST (kepala + bahu): wilayah di sekitar wajah saja — membuang meja/
    objek depan yang ikut terpotong rembg dan mengganggu thumbnail.
    """
    global _rembg_session
    from rembg import new_session, remove
    if _rembg_session is None:
        _rembg_session = new_session("isnet-general-use")
    out = remove(frame_pil.convert("RGB"), session=_rembg_session)
    # Isi LUBANG alfa tertutup (artefak rembg: area terang di antara jas/
    # lengan terbaca sebagai latar, meninggalkan tambalan warna desain di
    # dada subjek). Lubang dipadatkan; RGB-nya diisi frame asli yang
    # di-blur kuat -> terbaca sebagai bayangan lipatan, bukan tambalan.
    import cv2
    arr = np.asarray(out).copy()
    bgmask = (arr[:, :, 3] < 128).astype(np.uint8)
    seeds = np.argwhere(bgmask == 1)
    if len(seeds):
        ff = bgmask.copy()
        ffmask = np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8)
        cv2.floodFill(ff, ffmask, (int(seeds[0][1]), int(seeds[0][0])), 2)
        holes = (bgmask == 1) & (ff != 2)
        if holes.any():
            blur = cv2.GaussianBlur(
                np.asarray(frame_pil.convert("RGB")), (0, 0), 18)
            arr[holes, 0] = blur[holes, 0]
            arr[holes, 1] = blur[holes, 1]
            arr[holes, 2] = blur[holes, 2]
            arr[holes, 3] = 255
            out = Image.fromarray(arr, "RGBA")
    if face is not None:
        fx, fy, fw2, fh2 = face
        region = (max(int(fx - 1.15 * fw2), 0),
                  max(int(fy - 0.38 * fh2), 0),
                  min(int(fx + 2.15 * fw2), out.size[0]),
                  min(int(fy + 2.45 * fh2), out.size[1]))
        out = out.crop(region)
        # Perkuat alfa semi-transparan (baju terang rembg sering bolong)
        # + fade tepi bawah bust agar sisa tepi keras meleleh ke latar.
        arr = np.asarray(out).astype(np.int32)
        a = np.clip((arr[:, :, 3] - 25) * 1.25, 0, 255)
        fade = int(out.size[1] * 0.16)
        if fade > 4:
            ramp = np.linspace(1.0, 0.0, fade)[:, None]
            a[-fade:] = (a[-fade:] * ramp).astype(np.int32)
        arr[:, :, 3] = a
        out = Image.fromarray(arr.astype(np.uint8), "RGBA")
    bbox = out.split()[3].getbbox()
    return out.crop(bbox) if bbox else out


def _grade(img, brightness=1.04, color=1.16, contrast=1.08):
    from PIL import ImageEnhance, ImageFilter
    img = ImageEnhance.Contrast(
        ImageEnhance.Color(
            ImageEnhance.Brightness(img).enhance(brightness)
        ).enhance(color)).enhance(contrast)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=68,
                                              threshold=2))


def _outlined(subject_rgba, px, color):
    """Subjek + outline warna solid mengikuti siluet + bayangan lembut."""
    from PIL import ImageFilter
    alpha = subject_rgba.split()[3]
    sil = Image.new("RGBA", subject_rgba.size, color + (255,))
    sil_alpha = alpha.filter(ImageFilter.MaxFilter(px * 2 + 1))
    sil_alpha = sil_alpha.filter(ImageFilter.GaussianBlur(1.6))
    sil.putalpha(sil_alpha)
    canvas = Image.new("RGBA",
                       (subject_rgba.size[0] + px * 4,
                        subject_rgba.size[1] + px * 4), (0, 0, 0, 0))
    shadow = Image.new("RGBA", sil.size, (0, 0, 0, 200))
    shadow.putalpha(sil.split()[3].filter(
        ImageFilter.GaussianBlur(px)))
    canvas.alpha_composite(shadow, (px * 2, px * 2 + px))
    canvas.alpha_composite(sil, (px * 2, px * 2))
    canvas.alpha_composite(subject_rgba, (px * 2, px * 2))
    return canvas


def _gradient_bg(size, glow, edge, glow_center=(0.72, 0.42)):
    """Latar gradasi radial: terang di titik glow, gelap di tepi."""
    w, h = size
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = glow_center[0] * w, glow_center[1] * h
    d = np.sqrt(((x - cx) / w) ** 2 + ((y - cy) / h) ** 2)
    d = np.clip(d / (d.max() or 1), 0, 1) ** 1.4
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        arr[:, :, i] = (glow[i] * (1 - d) + edge[i] * d).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _anton_fit(lines, max_width, start_size):
    probe_img = Image.new("RGB", (8, 8))
    draw = ImageDraw.Draw(probe_img)
    size = start_size
    while size > 30:
        font = ImageFont.truetype(ANTON, size)
        if max(draw.textlength(ln, font=font) for ln in lines) <= max_width:
            return font
        size -= 6
    return ImageFont.truetype(ANTON, size)


def _text_block(lines, keyword, max_width, start_size, align="left"):
    """Blok teks Anton di layer transparan; kata kunci di PILL gold."""
    font = _anton_fit(lines, max_width, start_size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    widths = [probe.textlength(ln, font=font) for ln in lines]
    lh = int(font.size * 1.14)
    layer = Image.new("RGBA", (int(max(widths)) + 30, lh * len(lines) + 20),
                      (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    kw = (keyword or "").upper().strip("?!.,")
    y = 6
    for ln, lw in zip(lines, widths):
        x = 6 if align == "left" else (layer.size[0] - lw) // 2
        cursor = x
        for word in ln.split():
            ww = probe.textlength(word, font=font)
            if word.strip("?!.,") == kw and kw:
                d.rounded_rectangle(
                    [cursor - 8, y - 2, cursor + ww + 8,
                     y + lh - 2], radius=10, fill=GOLD + (255,))
                d.text((cursor, y), word, font=font, fill=(10, 10, 10))
            else:
                d.text((cursor, y + 4), word, font=font,
                       fill=(0, 0, 0, 255))
                d.text((cursor, y), word, font=font,
                       fill=(255, 255, 255, 255))
            cursor += ww + probe.textlength(" ", font=font)
        y += lh
    return layer


def _wrap_words(text, n_lines=2):
    words = text.upper().split()
    if len(words) <= 2:
        return [" ".join(words)]
    best = None
    for split in range(1, len(words)):
        lines = [" ".join(words[:split]), " ".join(words[split:])]
        imb = abs(len(lines[0]) - len(lines[1]))
        if best is None or imb < best[0]:
            best = (imb, lines)
    return best[1]


def make_v2(video_path, text, keyword=None, out_dir=None,
            theme_glow=(128, 16, 16), theme_edge=(10, 8, 14)):
    """Set thumbnail v2: A=pop gradasi, B=pop scene, C=full-bleed banner.

    Tiap varian dibuat 16:9 (1280x720) dan 9:16 (1080x1920) + stamp 168px
    + thumb-report-v2.md. Mengembalikan list dict hasil.
    """
    if out_dir is None:
        raise ValueError("out_dir wajib diisi")
    os.makedirs(out_dir, exist_ok=True)
    frames = pick_expressive_frames(video_path, n=3)
    if not frames:
        raise RuntimeError("tidak ada frame berwajah untuk thumbnail v2")
    lines = _wrap_words(text)
    results = []
    recipes = [("A", 0, "gradient"), ("B", 1, "scene"), ("C", 2, "raw")]
    for aspect in ("16:9", "9:16"):
        tw, th = SIZES[aspect]
        tag = aspect.replace(":", "x")
        for name, fi, kind in recipes:
            fr = frames[min(fi, len(frames) - 1)]
            src = Image.open(fr["path"]).convert("RGB")
            out = os.path.join(out_dir, f"v2-{tag}-{name}.jpg")
            if kind == "raw":
                img = _grade(_crop_to_aspect(src, tw, th))
                bar_h = int(th * 0.30)
                bar = Image.new("RGBA", (tw, bar_h), (5, 5, 8, 235))
                img = img.convert("RGBA")
                img.alpha_composite(bar, (0, th - bar_h))
                d = ImageDraw.Draw(img)
                d.rectangle([0, th - bar_h, tw, th - bar_h + 6],
                            fill=GOLD + (255,))
                block = _text_block(lines, keyword, tw - 120,
                                    150 if th > tw else 104,
                                    align="center")
                img.alpha_composite(
                    block, ((tw - block.size[0]) // 2,
                            th - bar_h + (bar_h - block.size[1]) // 2))
                img = img.convert("RGB")
            else:
                subj = _outlined(_grade(_cutout(src, face=fr["face"])), 8,
                                 (255, 255, 255) if kind == "gradient"
                                 else GOLD)
                if kind == "gradient":
                    img = _gradient_bg((tw, th), theme_glow, theme_edge,
                                       (0.72, 0.4) if tw > th
                                       else (0.5, 0.34)).convert("RGBA")
                else:
                    from PIL import ImageEnhance, ImageFilter
                    bg = _crop_to_aspect(src, tw, th)
                    bg = ImageEnhance.Brightness(
                        ImageEnhance.Color(bg).enhance(0.55)).enhance(0.5)
                    img = bg.filter(
                        ImageFilter.GaussianBlur(6)).convert("RGBA")
                if tw > th:  # 16:9 — subjek kanan, teks kiri miring
                    scale = (th * 0.98) / subj.size[1]
                    subj = subj.resize(
                        (int(subj.size[0] * scale),
                         int(subj.size[1] * scale)), Image.LANCZOS)
                    img.alpha_composite(subj, (tw - subj.size[0] + 30,
                                               th - subj.size[1]))
                    block = _text_block(lines, keyword, int(tw * 0.52),
                                        128)
                    block = block.rotate(2, expand=True,
                                         resample=Image.BICUBIC)
                    img.alpha_composite(block, (56, (th - block.size[1])
                                                // 2 - 30))
                else:  # 9:16 — subjek besar tengah-atas, teks menempel
                    scale = (th * 0.66) / subj.size[1]
                    subj = subj.resize(
                        (int(subj.size[0] * scale),
                         int(subj.size[1] * scale)), Image.LANCZOS)
                    img.alpha_composite(
                        subj, ((tw - subj.size[0]) // 2, 110))
                    block = _text_block(lines, keyword, tw - 110, 168,
                                        align="center")
                    img.alpha_composite(
                        block, ((tw - block.size[0]) // 2,
                                110 + subj.size[1] - 30))
                img = img.convert("RGB")
            img.save(out, "JPEG", quality=92)
            stamp = os.path.join(out_dir, f"v2-{tag}-{name}-stamp168.png")
            img.resize((168, int(168 * th / tw)),
                       Image.LANCZOS).save(stamp)
            results.append({"file": out, "stamp": stamp,
                            "aspect": aspect, "variant": name,
                            "kind": kind,
                            "frame_seconds": fr["seconds"],
                            "expr": fr["expr"]})
    rep = [f"# Laporan Thumbnail v2 — {os.path.basename(video_path)}",
           "", f"Teks: **{text.upper()}** · desain: cutout pop-out "
           "(rembg) + outline + Anton + pill gold", ""]
    for r in results:
        expr = (f"{r['expr']:.2f}" if r["expr"] is not None
                else "n/a (landmarker tidak tersedia)")
        rep.append(f"- {os.path.basename(r['file'])} · jenis {r['kind']} · "
                   f"frame detik {r['frame_seconds']} · skor ekspresi "
                   f"{expr} · stamp: {os.path.basename(r['stamp'])}")
    with open(os.path.join(out_dir, "thumb-report-v2.md"), "w") as fh:
        fh.write("\n".join(rep) + "\n")
    return results


if __name__ == "__main__":
    # Demo v1: varian thumbnail dari klip podcast Pape.
    import json
    res = make_variants(
        "examples/section.mp4",
        "WW3 LOOKS LIKE THIS", keyword="WW3",
        out_dir="examples/thumbs-v1")
    print(json.dumps([{k: r[k] for k in ("file", "verdict", "frame_seconds")}
                      for r in res], indent=1))


# ---------- v3: SHORTS MODEL (9:16 only, feed-safe) ----------
# Shorts surfaces: shelf/search tiles are small; in the feed the bottom
# ~25% and the right action-button column are covered by UI. So: face
# dominates the top, ALL text sits in the centre band (y 620-1440 of
# 1920) and within the left 82% width. Hybrid of both v2 directions:
# cut-out pop (B) + separated layout & question copy (A).

def make_short(video_path, text, keyword=None, out_dir=None):
    import os
    out_dir = out_dir or "outputs/short-thumbs"
    os.makedirs(out_dir, exist_ok=True)
    keyword = (keyword or text.split()[-1]).upper()
    lines = _wrap_words(text.upper())
    picks = pick_expressive_frames(video_path, n=3)
    results = []

    def finish(img, name, frame_t):
        img.save(os.path.join(out_dir, name), quality=92)
        stamp = img.resize((135, 240))
        sp = os.path.join(out_dir, name.replace(".jpg", "-shelf135.png"))
        stamp.save(sp)
        results.append({"file": name, "frame_t": frame_t, "stamp": sp})

    # S-A: cut-out pop-out on gradient, text below in safe band
    src = Image.open(picks[0]["path"]).convert("RGB")
    cut = _cutout(src, picks[0]["face"])
    bg = _gradient_bg((1080, 1920), (96, 10, 14), (8, 5, 8),
                      glow_center=(0.5, 0.30))
    subj = _outlined(_grade(cut), 10, (255, 255, 255))
    sc = 940 / subj.width
    subj = subj.resize((940, int(subj.height * sc)))
    bg.paste(subj, ((1080 - subj.width) // 2, 90), subj)
    tb = _text_block(lines, keyword, 900, 190, align="center")
    bg.paste(tb, ((1080 - tb.width) // 2, 1210), tb)
    finish(bg, "short-A-cutout.jpg", picks[0]["seconds"])

    # S-B: photo panel - face top, black panel + question below
    src2 = Image.open(picks[1]["path"]).convert("RGB")
    top = _crop_around_face(src2, picks[1]["face"], 1080, 1180,
                            target_frac=0.52)
    if isinstance(top, tuple):
        top = top[0]
    canvas = Image.new("RGB", (1080, 1920), (5, 5, 8))
    canvas.paste(top, (0, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 1174, 1080, 1184], fill=GOLD)
    tb2 = _text_block(lines, keyword, 920, 200, align="center")
    canvas.paste(tb2, ((1080 - tb2.width) // 2, 1300), tb2)
    finish(canvas, "short-B-panel.jpg", picks[1]["seconds"])
    return {"out_dir": out_dir, "variants": results}


if __name__ == "__main__":
    import sys, json
    print(json.dumps(make_short(sys.argv[1], sys.argv[2],
                                sys.argv[3] if len(sys.argv) > 3 else None,
                                sys.argv[4] if len(sys.argv) > 4 else None),
                     indent=1))
