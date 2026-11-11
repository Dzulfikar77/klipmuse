r"""
tracking.py — Modul tracking 3 mode untuk reframe 9:16 pipeline clipper.

Disetujui pengguna 2026-11-10 (pengembangan dari "face tracking opsi 3"):
satu modul, tiga mode mengikuti JENIS konten — bukan satu alat untuk semua.

  mode="face"  — podcast / talking head. Jendela crop 9:16 mengikuti wajah
                 pembicara (deteksi YuNet + validasi landmark dari
                 thumbnail.py). Pemilihan target: wajah terbesar dengan
                 bonus kontinuitas (tidak melompat antar orang tiap frame).
                 Keterbatasan v1: belum mendeteksi SIAPA yang sedang bicara
                 (active speaker) — itu v2.
  mode="motion"— sport. Jendela mengikuti pusat massa gerakan (frame
                 differencing). Yang diikuti aksinya, bukan wajah pemain.
  mode="full"  — game / tangkapan lebar. Tanpa tracking: frame utuh
                 16:9 di atas latar blur (pola klip dunkey yang terbukti).

Lintasan (trajectory) = daftar keyframe {t, cx, cy} (pusat jendela,
 ternormalisasi 0..1 terhadap frame sumber), dihaluskan EMA + batas
 kecepatan agar tidak jitter, lalu diinterpolasi per frame saat render.

Render: segmen dipotong + di-encode ulang H.264 via FFmpeg sistem dulu
 (sumber bisa AV1 yang tak terbaca OpenCV), frame di-crop per lintasan
 via OpenCV, di-pipe ke FFmpeg untuk encode final 1080x1920 H.264 30fps
 + audio dari segmen. Output mengikuti PRODUCTION-STANDARD.md.

Jalankan dengan .venv-thumb/bin/python (OpenCV + numpy di sana).

    from tracking import render_tracked_clip
    render_tracked_clip("section.mp4", start=0, dur=15, mode="face",
                        out_path="proof-face.mp4")
"""

import os
import subprocess
import tempfile

import cv2
import numpy as np

from thumbnail import _detect_faces, _plausible_face

OUT_W, OUT_H = 1080, 1920


# ---------------------------------------------------------------- util
def _probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())


def _extract_segment(video, start, dur, out_path):
    """Potong segmen + encode ulang H.264 30fps (aman dibaca OpenCV)."""
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", video,
         "-t", str(dur), "-r", "30", "-c:v", "libx264", "-pix_fmt",
         "yuv420p", "-c:a", "aac", "-shortest", out_path],
        check=True)
    return out_path


def _smooth(points, alpha=0.25, max_step=0.02):
    """EMA + batasi langkah per sampel (anti jitter & anti lompat)."""
    if not points:
        return points
    out = [points[0]]
    for p in points[1:]:
        px, py = out[-1][1], out[-1][2]
        nx = px + alpha * (p[1] - px)
        ny = py + alpha * (p[2] - py)
        nx = px + float(np.clip(nx - px, -max_step, max_step))
        ny = py + float(np.clip(ny - py, -max_step, max_step))
        out.append((p[0], nx, ny))
    return out


def _interp(traj, t):
    """Interpolasi linier pusat jendela pada waktu t."""
    if t <= traj[0][0]:
        return traj[0][1], traj[0][2]
    if t >= traj[-1][0]:
        return traj[-1][1], traj[-1][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(traj, traj[1:]):
        if t0 <= t <= t1:
            k = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return x0 + k * (x1 - x0), y0 + k * (y1 - y0)
    return traj[-1][1], traj[-1][2]


# ------------------------------------------------------------- pelacak
def track_face(video, start=0.0, dur=None, sample_fps=3.0):
    """Lintasan mengikuti wajah dominan. Keyframe per 1/sample_fps detik."""
    dur = dur or _probe_duration(video)
    tmp = tempfile.mkdtemp(prefix="track_face_")
    raw, t, prev = [], 0.0, None
    missing = 0
    while t < dur:
        fp = os.path.join(tmp, "f.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", str(start + t),
             "-i", video, "-frames:v", "1", "-q:v", "3", fp],
            check=True)
        frame = cv2.imread(fp)
        if frame is None:
            break
        fh, fw = frame.shape[:2]
        faces = [f for f in _detect_faces(frame)
                 if _plausible_face(f, fw, fh)]
        if faces:
            def key(f):
                area = f["w"] * f["h"]
                if prev is not None:
                    d = abs((f["x"] + f["w"] / 2) / fw - prev[0]) \
                        + abs((f["y"] + f["h"] / 2) / fh - prev[1])
                    if d < 0.25:
                        area *= 1.6  # bonus kontinuitas
                return area
            f = max(faces, key=key)
            cx = (f["x"] + f["w"] / 2) / fw
            cy = (f["y"] + f["h"] / 2) / fh
            prev, missing = (cx, cy), 0
            raw.append((round(t, 2), cx, cy))
        else:
            missing += 1
            if prev is not None and missing * (1 / sample_fps) <= 2.0:
                raw.append((round(t, 2), prev[0], prev[1]))  # tahan posisi
            else:
                raw.append((round(t, 2), 0.5, 0.45))  # pelan ke tengah
                prev = (0.5, 0.45)
        t += 1.0 / sample_fps
    return _smooth(raw)


def track_motion(video, start=0.0, dur=None, sample_fps=3.0):
    """Lintasan mengikuti pusat massa gerakan (untuk sport)."""
    dur = dur or _probe_duration(video)
    tmp = tempfile.mkdtemp(prefix="track_motion_")
    raw, t, prev_gray, prev_c = [], 0.0, None, (0.5, 0.45)
    while t < dur:
        fp = os.path.join(tmp, "f.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", str(start + t),
             "-i", video, "-frames:v", "1", "-q:v", "3", fp],
            check=True)
        frame = cv2.imread(fp)
        if frame is None:
            break
        small = cv2.resize(frame, (320, 180))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            _, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                    np.ones((3, 3), np.uint8))
            # Ikuti BLOB gerakan terbesar, bukan centroid global —
            # centroid merata-ratakan dua subjek bergerak menjadi titik
            # kosong di tengahnya (pelajaran uji sport pertama).
            n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
            if n > 1:
                areas = stats[1:, cv2.CC_STAT_AREA]
                k = int(np.argmax(areas)) + 1
                if areas[k - 1] > 300:
                    prev_c = (cents[k][0] / 320, cents[k][1] / 180)
            else:
                m = cv2.moments(mask)
                if m["m00"] > 800:
                    prev_c = (m["m10"] / m["m00"] / 320,
                              m["m01"] / m["m00"] / 180)
        raw.append((round(t, 2), prev_c[0], prev_c[1]))
        prev_gray = gray
        t += 1.0 / sample_fps
    return _smooth(raw, alpha=0.3, max_step=0.03)


def track_full(video, start=0.0, dur=None):
    """Mode penuh: lintasan diam di tengah (render memakai pola blur)."""
    dur = dur or _probe_duration(video)
    return [(0.0, 0.5, 0.5), (round(float(dur), 2), 0.5, 0.5)]


TRACKERS = {"face": track_face, "motion": track_motion, "full": track_full}


# -------------------------------------------------------------- render
def _window(src_w, src_h):
    """Ukuran jendela crop 9:16 di dalam frame sumber."""
    win_w = int(src_h * 9 / 16)
    if win_w <= src_w:
        return win_w, src_h
    return src_w, int(src_w * 16 / 9)


def render_tracked_clip(video, start, dur, mode, out_path,
                        sample_fps=3.0):
    """Render klip 1080x1920 mengikuti lintasan mode terpilih.

    Mengembalikan dict ringkasan {mode, frames, travel} — travel = jarak
    tempuh pusat jendela (piksel sumber), bukti tracking benar bergerak.
    """
    if mode not in TRACKERS:
        raise ValueError(f"mode harus salah satu dari {list(TRACKERS)}")
    tmp = tempfile.mkdtemp(prefix="track_render_")
    seg = _extract_segment(video, start, dur,
                           os.path.join(tmp, "seg.mp4"))
    traj = TRACKERS[mode](seg, 0.0, dur, sample_fps) \
        if mode != "full" else track_full(seg, 0.0, dur)
    cap = cv2.VideoCapture(seg)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    win_w, win_h = _window(src_w, src_h)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s",
         f"{OUT_W}x{OUT_H}", "-r", "30", "-i", "-",
         "-i", seg, "-map", "0:v", "-map", "1:a?",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-shortest", out_path],
        stdin=subprocess.PIPE)
    frames, travel, last = 0, 0.0, None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = idx / 30.0
        idx += 1
        cx, cy = _interp(traj, t)
        if mode == "full":
            bg = cv2.resize(frame, (OUT_W, OUT_H))
            bg = cv2.GaussianBlur(bg, (0, 0), 24)
            bg = (bg * 0.75).astype(np.uint8)
            fg_h = int(OUT_W * src_h / src_w)
            y0 = (OUT_H - fg_h) // 2
            bg[y0:y0 + fg_h, 0:OUT_W] = cv2.resize(frame, (OUT_W, fg_h))
            out = bg
        else:
            x0 = int(np.clip(cx * src_w - win_w / 2, 0, src_w - win_w))
            y0 = int(np.clip(cy * src_h - win_h / 2, 0, src_h - win_h))
            if last is not None:
                travel += float(np.hypot(x0 - last[0], y0 - last[1]))
            last = (x0, y0)
            crop = frame[y0:y0 + win_h, x0:x0 + win_w]
            out = cv2.resize(crop, (OUT_W, OUT_H),
                             interpolation=cv2.INTER_LINEAR)
        proc.stdin.write(out.tobytes())
        frames += 1
    cap.release()
    proc.stdin.close()
    proc.wait()
    return {"mode": mode, "frames": frames, "travel_px": round(travel),
            "out": out_path}


if __name__ == "__main__":
    import json
    base = "examples"  # folder berisi section.mp4 contoh
    print(json.dumps(render_tracked_clip(
        f"{base}/section.mp4", start=0, dur=15, mode="face",
        out_path=f"{base}/proof-face-tracking.mp4"), indent=1))
