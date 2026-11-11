#!/usr/bin/env python3
"""compile_ranking.py — rakit kompilasi ranking (countdown) dari beberapa klip vertikal.

Alur: normalisasi tiap segmen ke 1080x1920/30fps/H.264+AAC (blur-pad bila
rasio bukan 9:16), bakar badge ranking (#N besar, fade 0-2,6 dtk) + label
versi dan sublabel (views/keterangan) yang menetap, buat intro judul,
lalu gabung semua dengan transisi xfade 0,3 dtk (video) + acrossfade (audio).

Pakai:
  python compile_ranking.py config.json
Config JSON:
{
  "title_lines": ["TOP 5", "FIRST TIME IN A", "FANCY CAFE"],
  "title_sub": "RANKED BY VIEWS + TWIST",
  "intro_seconds": 2.5,
  "fade": 0.3,
  "output": "out.mp4",
  "workdir": "work",
  "segments": [   # URUTAN TAMPIL (countdown: peringkat terbesar dulu)
    {"file": "a.mp4", "rank": 5, "label": "KEVKEVKIWI", "sub": "729K VIEWS - THE CREATOR"},
    ...
  ]
}
"""
import json, subprocess, sys, os

W, H, FPS = 1080, 1920, 30
GOLD = "0xFFC21C"
FONT = os.path.expanduser("~/workspace/clipper-project/assets-ref/fonts/Anton-Regular.ttf")


def run(cmd):
    print("+", " ".join(cmd[:3]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit(f"ffmpeg gagal: {cmd[1] if len(cmd)>1 else cmd}")
    return r


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-show_entries", "stream=width,height",
                        "-of", "json", path], capture_output=True, text=True)
    d = json.loads(r.stdout)
    w = h = None
    for s in d.get("streams", []):
        if "width" in s:
            w, h = s["width"], s["height"]
    return float(d["format"]["duration"]), w, h


def esc(text):
    # Apostrof dibuang: escaping-nya merusak parser drawtext (terbukti 2026-11-11).
    return (text.replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "").replace("%", "\\%"))


def normalize(seg, out):
    dur, w, h = probe(seg["file"])
    rank, label, sub = seg["rank"], esc(seg["label"]), esc(seg["sub"])
    badge_alpha = "if(lt(t,0.25),t/0.25,if(lt(t,2.2),1,max(0,(2.6-t)/0.4)))"
    draws = (
        f"drawtext=fontfile='{FONT}':text='#{rank}':fontsize=200:fontcolor={GOLD}"
        f":borderw=12:bordercolor=black:x=38:y=430:alpha='{badge_alpha}':enable='between(t,0,2.6)',"
        f"drawtext=fontfile='{FONT}':text='{label}':fontsize=56:fontcolor=white"
        f":box=1:boxcolor=black@0.55:boxborderw=16:x=(w-text_w)/2:y=1600,"
        f"drawtext=fontfile='{FONT}':text='{sub}':fontsize=40:fontcolor={GOLD}"
        f":borderw=4:bordercolor=black:x=(w-text_w)/2:y=1706"
    )
    if w and abs(w / h - W / H) < 0.03:
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"fps={FPS},setsar=1,{draws},format=yuv420p")
        fc = ["-vf", vf]
    else:
        fc = ["-filter_complex",
              f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"gblur=sigma=45,eq=brightness=-0.12[bg];"
              f"[0:v]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,"
              f"fps={FPS},setsar=1,{draws},format=yuv420p[v]"]
        fc += ["-map", "[v]", "-map", "0:a?"]
    run(["ffmpeg", "-v", "error", "-i", seg["file"], *fc,
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", out, "-y"])
    return probe(out)[0]


def make_intro(cfg, out):
    lines = cfg["title_lines"]
    draws = []
    # Baris pertama = paling besar (mis. "TOP 5"), sisanya lebih kecil.
    draws.append(f"drawtext=fontfile='{FONT}':text='{esc(lines[0])}':fontsize=280"
                 f":fontcolor={GOLD}:borderw=14:bordercolor=black:x=(w-text_w)/2:y=640")
    y = 990
    for ln in lines[1:]:
        draws.append(f"drawtext=fontfile='{FONT}':text='{esc(ln)}':fontsize=96"
                     f":fontcolor=white:borderw=8:bordercolor=black:x=(w-text_w)/2:y={y}")
        y += 118
    draws.append(f"drawtext=fontfile='{FONT}':text='{esc(cfg['title_sub'])}':fontsize=44"
                 f":fontcolor={GOLD}:borderw=5:bordercolor=black:x=(w-text_w)/2:y={y+36}")
    dur = cfg.get("intro_seconds", 2.5)
    run(["ffmpeg", "-v", "error",
         "-f", "lavfi", "-i", f"color=c=0x141414:s={W}x{H}:r={FPS}:d={dur}",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", ",".join(draws) + ",format=yuv420p",
         "-t", str(dur), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "160k", out, "-y"])
    return dur


def main():
    cfg = json.load(open(sys.argv[1]))
    work = cfg.get("workdir", "compile-work")
    os.makedirs(work, exist_ok=True)
    parts, durs = [], []
    intro = os.path.join(work, "00-intro.mp4")
    durs.append(make_intro(cfg, intro)); parts.append(intro)
    for i, seg in enumerate(cfg["segments"]):
        out = os.path.join(work, f"{i+1:02d}-rank{seg['rank']}.mp4")
        durs.append(normalize(seg, out)); parts.append(out)
    fade = cfg.get("fade", 0.3)
    # Rantai xfade + acrossfade
    inputs = []
    for p in parts:
        inputs += ["-i", p]
    fc, vlabel, alabel = [], "0:v", "0:a"
    cum = durs[0]
    for i in range(1, len(parts)):
        off = cum - fade
        fc.append(f"[{vlabel}][{i}:v]xfade=transition=fade:duration={fade}:offset={off:.3f}[vx{i}]")
        fc.append(f"[{alabel}][{i}:a]acrossfade=d={fade}[ax{i}]")
        vlabel, alabel = f"vx{i}", f"ax{i}"
        cum = cum + durs[i] - fade
    run(["ffmpeg", "-v", "error", *inputs, "-filter_complex", ";".join(fc),
         "-map", f"[{vlabel}]", "-map", f"[{alabel}]",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "160k", cfg["output"], "-y"])
    total = probe(cfg["output"])[0]
    print(f"SELESAI: {cfg['output']} durasi {total:.1f} dtk (target {cum:.1f})")


if __name__ == "__main__":
    main()
