"""
tracking_v2.py — Tracking v2: layout PER ADEGAN + pembicara aktif.

Dibangun 2026-11-10 atas persetujuan pengguna, sebagai generalisasi dari
perbaikan manual render_como.py (jangkar wide-shot + smoothing sadar
potongan) dan penutup celah terbesar v1: tidak ada deteksi adegan dan
tidak ada deteksi siapa yang sedang bicara.

Alur:
1. Segmen dipotong + encode ulang H.264 (seperti v1).
2. Deteksi adegan: beda frame rata-rata pada sampling 6 fps — potongan
   kamera menghasilkan lonjakan besar; adegan < 0,8 dtk digabung.
3. Per adegan, wajah disampel 3 fps dan dikelompokkan jadi cluster
   (posisi konsisten). Deteksi memakai YuNet mentah dengan saringan
   geometri longgar — BUKAN _plausible_face v1 yang menolak wajah kecil
   (< 8% lebar frame) dan menjadi penyebab kegagalan wide shot Como.
4. Pembicara aktif: untuk adegan multi-wajah, tiap cluster dinilai dari
   GERAKAN AREA MULUT antar frame (beda rata-rata piksel ROI mulut pada
   8 fps). Blendshape jawOpen FaceLandmarker terbukti menipu pada wide
   shot Como: wajah profil pembicara asli kalah skor dari wajah frontal
   pendengar yang mengangguk (sampel validnya pun cuma 6/18). Gerakan
   mulut mentah justru tegas: Mirwan 9,27 vs host 1,48. jawOpen hanya
   cadangan bila skor gerak tidak tersedia sama sekali.
5. Layout per adegan diputuskan:
   - 0 wajah stabil                     -> "full"  (frame utuh + blur)
   - 1 wajah                            -> "track" (ikuti wajah, seperti v1)
   - 2 wajah, keduanya cukup besar      -> "split" (dua panel ditumpuk;
                                            pembicara aktif di panel atas)
   - >=2 wajah kecil / >=3 wajah (wide) -> "anchor" (jendela rapat diam
                                            di pembicara aktif / wajah
                                            dominan — pola render_como)
   Smoothing lintasan hanya DI DALAM adegan: tidak ada lagi luncuran
   melintasi potongan kamera.
6. Render 1080x1920 30fps H.264 + AAC mengikuti rencana adegan.

Jalankan dengan .venv-thumb/bin/python (OpenCV + MediaPipe di sana).

    from tracking_v2 import analyze_plan, render_v2
    plan = analyze_plan("section.webm", start=7.68, dur=32.9)
    render_v2("section.webm", 7.68, 32.9, "tracked_v2.mp4", plan=plan)

CLI:
    .venv-thumb/bin/python tracking_v2.py analyze <video> <start> <dur>
    .venv-thumb/bin/python tracking_v2.py render  <video> <start> <dur> <out>
"""

import json
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thumbnail import _detect_faces, _get_landmarker
from tracking import OUT_H, OUT_W, _extract_segment, _smooth

SCENE_DIFF_THRESHOLD = 22.0   # beda rata-rata abu-abu (0-255) = potongan
MIN_SCENE = 0.8               # adegan lebih pendek dari ini digabung
FACE_MIN_FRAC = 0.02          # lebar wajah minimum (relatif lebar frame)
SPLIT_MIN_FRAC = 0.07         # lebar wajah minimum untuk layout split
ANCHOR_WIN_H_FRAC = 0.75      # tinggi jendela anchor (810/1080 di Como)


# ------------------------------------------------------------ util
def _face_loose_ok(f, fw, fh):
    """Saringan longgar untuk analisis v2: geometri landmark masuk akal,
    rasio wajar, di dalam frame. Tanpa syarat ukuran minimum v1."""
    if not (0.45 <= f["w"] / max(f["h"], 1) <= 1.6):
        return False
    if f["w"] < FACE_MIN_FRAC * fw:
        return False
    if f["x"] < -0.05 * fw or f["y"] < -0.05 * fh \
            or f["x"] + f["w"] > 1.05 * fw or f["y"] + f["h"] > 1.05 * fh:
        return False
    if f["lm"]:
        (ex1, ey1), (ex2, ey2), (nx, ny), (mx1, my1), (mx2, my2) = f["lm"]
        if not ((ey1 + ey2) / 2 < ny < (my1 + my2) / 2):
            return False
    return True


def _norm_face(f, fw, fh):
    return {"cx": (f["x"] + f["w"] / 2) / fw,
            "cy": (f["y"] + f["h"] / 2) / fh,
            "w": f["w"] / fw, "h": f["h"] / fh}


# ------------------------------------------------- deteksi adegan
def detect_scenes(seg_path, dur, fps=6.0):
    """Daftar batas adegan [(t0, t1), ...] dari beda frame rata-rata."""
    cap = cv2.VideoCapture(seg_path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / fps)))
    prev, cuts, idx = None, [0.0], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            small = cv2.resize(frame, (320, 180))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if prev is not None:
                diff = float(cv2.absdiff(gray, prev).mean())
                if diff > SCENE_DIFF_THRESHOLD:
                    cuts.append(idx / src_fps)
            prev = gray
        idx += 1
    cap.release()
    cuts.append(float(dur))
    # Gabung adegan terlalu pendek ke tetangganya.
    merged = [cuts[0]]
    for c in cuts[1:-1]:
        if c - merged[-1] >= MIN_SCENE and cuts[-1] - c >= 0.0:
            merged.append(c)
    merged.append(cuts[-1])
    scenes = [(merged[i], merged[i + 1]) for i in range(len(merged) - 1)
              if merged[i + 1] - merged[i] > 0.05]
    return scenes


# ------------------------------------------------- sampel wajah
def _sample_faces(seg_path, dur, fps=3.0):
    """Sampel wajah ternormalisasi: list[(t, [face, ...])]."""
    cap = cv2.VideoCapture(seg_path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / fps)))
    out, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            fh, fw = frame.shape[:2]
            faces = [_norm_face(f, fw, fh) for f in _detect_faces(frame)
                     if _face_loose_ok(f, fw, fh)]
            out.append((round(idx / src_fps, 3), faces))
        idx += 1
    cap.release()
    return out


def _cluster(samples):
    """Kelompokkan wajah antar sampel jadi cluster posisi konsisten."""
    clusters = []
    for t, faces in samples:
        used = set()
        for f in faces:
            best, bd = None, 0.12
            for i, c in enumerate(clusters):
                if i in used:
                    continue
                d = abs(f["cx"] - c["cx"]) + abs(f["cy"] - c["cy"])
                if d < bd:
                    best, bd = i, d
            if best is None:
                clusters.append({"cx": f["cx"], "cy": f["cy"],
                                 "w": f["w"], "h": f["h"],
                                 "points": [(t, f["cx"], f["cy"])],
                                 "n": 1})
                used.add(len(clusters) - 1)
            else:
                c = clusters[best]
                c["points"].append((t, f["cx"], f["cy"]))
                n = c["n"]
                for k in ("cx", "cy", "w", "h"):
                    c[k] = (c[k] * n + f[k]) / (n + 1)
                c["n"] = n + 1
                used.add(best)
    return clusters


# ------------------------------------------- skor pembicara aktif
def _jawopen_series(seg_path, cluster, t0, t1, samples=18):
    """Seri jawOpen untuk satu cluster di [t0, t1]; [] bila gagal."""
    lm = _get_landmarker()
    if lm is None:
        return []
    import mediapipe as mp
    cap = cv2.VideoCapture(seg_path)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    series = []
    times = np.linspace(t0 + 0.1, max(t0 + 0.11, t1 - 0.1), samples)
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        fx, fy = cluster["cx"] * src_w, cluster["cy"] * src_h
        fw_, fh_ = cluster["w"] * src_w, cluster["h"] * src_h
        m = 0.7 * max(fw_, fh_)
        x0 = int(np.clip(fx - fw_ / 2 - m, 0, src_w - 1))
        y0 = int(np.clip(fy - fh_ / 2 - m, 0, src_h - 1))
        x1 = int(np.clip(fx + fw_ / 2 + m, 1, src_w))
        y1 = int(np.clip(fy + fh_ / 2 + m, 1, src_h))
        crop = frame[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        crop = cv2.resize(crop, (320, int(320 * crop.shape[0]
                                        / max(crop.shape[1], 1))))
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        try:
            res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                     data=rgb))
        except Exception:
            continue
        if res.face_blendshapes:
            bs = {c.category_name: c.score
                  for c in res.face_blendshapes[0]}
            series.append(float(bs.get("jawOpen", 0.0)))
    cap.release()
    return series


def _speaking_score(series):
    if len(series) < 4:
        return None
    a = np.array(series)
    return float(a.std() + 0.3 * a.mean())


def _mouth_motion_scores(seg, clusters, t0, t1, fps=8.0):
    """Skor bicara per cluster: rata-rata beda piksel area mulut antar
    frame berurutan dalam [t0, t1]. Satu lintasan sekuensial untuk
    semua cluster. None bila data kurang."""
    cap = cv2.VideoCapture(seg)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / fps)))
    cap.set(cv2.CAP_PROP_POS_MSEC, float(t0) * 1000)
    start_frame = int(t0 * src_fps)
    prev, diffs = {}, {i: [] for i in range(len(clusters))}
    idx = start_frame
    while True:
        ok, frame = cap.read()
        if not ok or idx / src_fps >= t1:
            break
        if (idx - start_frame) % step == 0:
            for i, c in enumerate(clusters):
                wpx, hpx = c["w"] * src_w, c["h"] * src_h
                x0 = int(c["cx"] * src_w - wpx / 2)
                y0 = int(c["cy"] * src_h - hpx / 2)
                mx0 = int(np.clip(x0 + 0.22 * wpx, 0, src_w - 1))
                mx1 = int(np.clip(x0 + 0.78 * wpx, 1, src_w))
                my0 = int(np.clip(y0 + 0.60 * hpx, 0, src_h - 1))
                my1 = int(np.clip(y0 + 0.98 * hpx, 1, src_h))
                roi = cv2.cvtColor(frame[my0:my1, mx0:mx1],
                                   cv2.COLOR_BGR2GRAY)
                if i in prev and roi.shape == prev[i].shape:
                    diffs[i].append(
                        float(cv2.absdiff(roi, prev[i]).mean()))
                prev[i] = roi
        idx += 1
    cap.release()
    return [float(np.mean(d)) if len(d) >= 3 else None
            for d in (diffs[i] for i in range(len(clusters)))]


# ------------------------------------------------------- analisis
def analyze_plan(video, start, dur):
    """Bangun rencana adegan untuk segmen [start, start+dur)."""
    tmp = tempfile.mkdtemp(prefix="track2_plan_")
    seg = _extract_segment(video, start, dur, os.path.join(tmp, "seg.mp4"))
    return _analyze_segment(seg, dur), seg


def _analyze_segment(seg, dur):
    scenes = detect_scenes(seg, dur)
    samples = _sample_faces(seg, dur)
    plan = []
    for (t0, t1) in scenes:
        sc_samples = [(t, fs) for (t, fs) in samples if t0 <= t < t1]
        clusters = _cluster(sc_samples)
        n_samples = max(1, len(sc_samples))
        stable = [c for c in clusters if c["n"] >= 0.4 * n_samples]
        stable.sort(key=lambda c: c["w"] * c["h"], reverse=True)
        entry = {"t0": round(t0, 2), "t1": round(t1, 2),
                 "faces": len(stable)}

        if not stable:
            entry["layout"] = "full"
            plan.append(entry)
            continue

        # Skor bicara hanya berguna (dan hanya dihitung) bila >1 wajah.
        # Utama: gerakan area mulut. Cadangan: blendshape jawOpen.
        scores = [None] * len(stable)
        if len(stable) >= 2:
            scores = _mouth_motion_scores(seg, stable, t0, t1)
            entry["speaking_method"] = "mouth_motion"
            if all(s is None for s in scores):
                scores = [
                    _speaking_score(_jawopen_series(seg, c, t0, t1))
                    for c in stable]
                entry["speaking_method"] = "jawopen_fallback"
            scores = [-1.0 if s is None else s for s in scores]
        entry["speaking_scores"] = [
            None if s is None or s < 0 else round(s, 4) for s in scores]
        active = None
        valid = [(s, i) for i, s in enumerate(scores)
                 if s is not None and s >= 0]
        if valid:
            active = max(valid)[1]

        def traj_of(c):
            pts = [(t, x, y) for (t, x, y) in c["points"]]
            return [[round(a, 2), round(b, 4), round(d, 4)]
                    for a, b, d in _smooth(pts)]

        if len(stable) == 1:
            c = stable[0]
            entry.update({"layout": "track", "traj": traj_of(c)})
        elif len(stable) == 2 and min(c["w"] for c in stable) \
                >= SPLIT_MIN_FRAC:
            top_i = active if active is not None else 0
            bot_i = 1 - top_i
            entry.update({
                "layout": "split", "active": top_i,
                "top": {"traj": traj_of(stable[top_i]),
                        "face_h": stable[top_i]["h"]},
                "bottom": {"traj": traj_of(stable[bot_i]),
                           "face_h": stable[bot_i]["h"]}})
        else:
            c = stable[active] if active is not None else stable[0]
            entry.update({"layout": "anchor",
                          "cx": round(c["cx"], 4), "cy": round(c["cy"], 4),
                          "active": active})
        plan.append(entry)
    return plan


# ---------------------------------------------------------- render
def _interp(traj, t):
    if t <= traj[0][0]:
        return traj[0][1], traj[0][2]
    if t >= traj[-1][0]:
        return traj[-1][1], traj[-1][2]
    for a, b in zip(traj, traj[1:]):
        if a[0] <= t <= b[0]:
            k = 0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
            return a[1] + k * (b[1] - a[1]), a[2] + k * (b[2] - a[2])
    return traj[-1][1], traj[-1][2]


def _crop(frame, cx, cy, win_w, win_h):
    src_h, src_w = frame.shape[:2]
    win_w, win_h = int(win_w), int(win_h)
    x0 = int(np.clip(cx * src_w - win_w / 2, 0, max(src_w - win_w, 0)))
    y0 = int(np.clip(cy * src_h - win_h / 2, 0, max(src_h - win_h, 0)))
    return frame[y0:y0 + win_h, x0:x0 + win_w]


def render_v2(video, start, dur, out_path, plan=None):
    """Render segmen mengikuti rencana adegan v2 -> 1080x1920."""
    tmp = tempfile.mkdtemp(prefix="track2_render_")
    seg = _extract_segment(video, start, dur, os.path.join(tmp, "seg.mp4"))
    if plan is None:
        plan = _analyze_segment(seg, dur)
    cap = cv2.VideoCapture(seg)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo",
         "-pix_fmt", "bgr24", "-s", f"{OUT_W}x{OUT_H}", "-r", "30",
         "-i", "-", "-i", seg, "-map", "0:v", "-map", "1:a?",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-shortest", out_path],
        stdin=subprocess.PIPE)
    win_w_full = int(src_h * 9 / 16)
    frames, idx = 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = idx / 30.0
        idx += 1
        scene = next((s for s in plan if s["t0"] <= t < s["t1"]),
                     plan[-1])
        layout = scene["layout"]
        if layout == "track":
            cx, cy = _interp(scene["traj"], t)
            out = cv2.resize(_crop(frame, cx, cy, win_w_full, src_h),
                             (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)
        elif layout == "anchor":
            win_h = int(ANCHOR_WIN_H_FRAC * src_h)
            out = cv2.resize(
                _crop(frame, scene["cx"], scene["cy"],
                      int(win_h * 9 / 16), win_h),
                (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)
        elif layout == "split":
            panels = []
            for key in ("top", "bottom"):
                p = scene[key]
                cx, cy = _interp(p["traj"], t)
                win_h = int(np.clip(p["face_h"] * src_h * 2.4,
                                    0.35 * src_h, src_h))
                win_w = int(win_h * OUT_W / (OUT_H // 2))
                panels.append(cv2.resize(
                    _crop(frame, cx, cy, win_w, win_h),
                    (OUT_W, OUT_H // 2), interpolation=cv2.INTER_LINEAR))
            out = np.vstack(panels)
        else:  # full
            bg = cv2.resize(frame, (OUT_W, OUT_H))
            bg = cv2.GaussianBlur(bg, (0, 0), 24)
            bg = (bg * 0.75).astype(np.uint8)
            fg_h = int(OUT_W * src_h / src_w)
            y0 = (OUT_H - fg_h) // 2
            bg[y0:y0 + fg_h, 0:OUT_W] = cv2.resize(frame, (OUT_W, fg_h))
            out = bg
        proc.stdin.write(out.tobytes())
        frames += 1
    cap.release()
    proc.stdin.close()
    proc.wait()
    return {"frames": frames, "scenes": len(plan), "out": out_path,
            "plan": plan}


if __name__ == "__main__":
    cmd = sys.argv[1]
    video, start, dur = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    if cmd == "analyze":
        plan, _seg = analyze_plan(video, start, dur)
        print(json.dumps(plan, indent=1))
    elif cmd == "render":
        print(json.dumps(render_v2(video, start, dur, sys.argv[5]),
                         indent=1))
