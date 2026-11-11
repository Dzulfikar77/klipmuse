"""
clip_recipe.py — Fondasi "recipe JSON" untuk pipeline clipper proyek ini.

Satu file JSON per klip yang mendeskripsikan SELURUH keputusan edit
sebagai data (pengganti panel editor ala ai-clipper-carbon, tanpa UI):
momen dipilih lewat INDEKS KATA transkrip (trim per kata), hook dengan
timing/animasi/posisi sendiri, gaya caption, mode tracking, dan output.
Recipe diisi Muse, direvisi lewat chat ("hook mulai detik 1, animasi
pop"), lalu di-render ulang — murah dan bisa diaudit.

Skema (semua bagian selain "name" opsional; default = standar proyek):

    {
      "version": 1,
      "name": "nama-klip",
      "source": {"url": "...", "title": "..."},
      "transcript": "transcript.json",        // relatif thd file recipe
      "moment": {
        "start_word": 9616, "end_word": 9745, // indeks ke words[] (inklusif)
        "start_pad": 0.04, "end_pad": 0.0,    // geser halus dari batas kata
        "anchor_start": "Why don't I just call",  // cek jangkar anti-geser
        "anchor_end": "Yeah, why not?"
        // Alternatif: "start_time": 3007.70, "end_time": 3040.60
      },
      "tracking": {"mode": "face"},           // face | motion | full
      "captions": {"font": "Arial", "size": 64, "margin_v": 560,
                   "max_words": 4, "gap_split": 0.7},
      "hook": {"text": "HE CALLED THE\\NRIVAL PRESIDENT",
               "keyword": "RIVAL", "start": 0.0, "duration": 2.8,
               "animation": "fade_scale",     // lihat hook_overlay.ANIMATIONS
               "font_size": 118, "margin_v": 560},
      "output": {"clip": "clip.mp4"}
    }

Fungsi utama:
- load_recipe(path)  -> dict tervalidasi + path transkrip teresolusi.
- resolve_moment(recipe, words) -> (start, end, clip_words, warnings);
  memverifikasi anchor teks terhadap kata di indeks yang ditunjuk
  (pelajaran dari bug sinkron 2026-11-10: jangan percaya offset buta).
- build_ass(recipe, words) -> (teks ASS lengkap, info) — caption
  word-by-word (progressive reveal, kata aktif gold) + event hook dari
  recipe. Logika grouping identik dengan make_clip_como.py yang teruji.
- CLI: python clip_recipe.py recipe.json  → ringkasan resolusi + cek.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_overlay import ANIMATIONS, hook_event, hook_style_line

CAPTION_DEFAULTS = {
    "font": "Arial", "size": 64, "margin_v": 560,
    "margin_lr": 60, "max_words": 4, "gap_split": 0.7,
}
HOOK_DEFAULTS = {
    "text": "", "keyword": None, "start": 0.0, "duration": 2.8,
    "animation": "fade_scale", "font_size": 118, "margin_v": 560,
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()


def load_recipe(path: str) -> dict:
    """Baca + validasi recipe JSON. Path transkrip dibuat absolut."""
    with open(path) as f:
        recipe = json.load(f)
    if recipe.get("version", 1) != 1:
        raise ValueError(f"Versi recipe tidak didukung: {recipe.get('version')}")
    if not recipe.get("name"):
        raise ValueError("Recipe wajib punya 'name'")

    recipe["captions"] = {**CAPTION_DEFAULTS, **recipe.get("captions", {})}
    recipe["hook"] = {**HOOK_DEFAULTS, **recipe.get("hook", {})}
    recipe.setdefault("tracking", {"mode": "face"})
    recipe.setdefault("moment", {})

    hook = recipe["hook"]
    if hook["animation"] not in ANIMATIONS:
        raise ValueError(
            f"hook.animation {hook['animation']!r} tidak dikenal; "
            f"pilihan: {ANIMATIONS}")
    if hook["duration"] <= 0:
        raise ValueError("hook.duration harus > 0")
    if recipe["tracking"].get("mode") not in ("face", "motion", "full"):
        raise ValueError("tracking.mode harus face | motion | full")

    moment = recipe["moment"]
    has_words = "start_word" in moment and "end_word" in moment
    has_times = "start_time" in moment and "end_time" in moment
    if not (has_words or has_times):
        raise ValueError(
            "moment wajib berisi start_word+end_word ATAU start_time+end_time")

    base = os.path.dirname(os.path.abspath(path))
    transcript = recipe.get("transcript", "transcript.json")
    recipe["_transcript_path"] = (
        transcript if os.path.isabs(transcript)
        else os.path.join(base, transcript))
    recipe["_dir"] = base
    return recipe


def load_words(recipe: dict) -> list:
    with open(recipe["_transcript_path"]) as f:
        data = json.load(f)
    return data["words"]


def resolve_moment(recipe: dict, words: list):
    """Resolusi momen recipe -> (start, end, clip_words, warnings).

    Jalur indeks kata: start = words[start_word].start - start_pad,
    end = words[end_word].end + end_pad. Anchor (bila ada) diverifikasi
    terhadap kata-kata di sekitar indeks — ketidakcocokan menghasilkan
    warning, bukan kegagalan, agar manusia yang memutuskan.
    """
    m = recipe["moment"]
    warnings = []
    if "start_word" in m:
        si, ei = int(m["start_word"]), int(m["end_word"])
        if not (0 <= si <= ei < len(words)):
            raise ValueError(
                f"Indeks kata di luar jangkauan: {si}..{ei} "
                f"(total {len(words)} kata)")
        clip_words = words[si:ei + 1]
        start = clip_words[0]["start"] - float(m.get("start_pad", 0.0))
        end = clip_words[-1]["end"] + float(m.get("end_pad", 0.0))

        for key, sample in (("anchor_start", clip_words[:8]),
                            ("anchor_end", clip_words[-8:])):
            if m.get(key):
                want = _norm(m[key])
                got = _norm(" ".join(w["word"] for w in sample))
                if want and want != got[:len(want)] and want != got[-len(want):]:
                    if not all(w in got for w in want):
                        warnings.append(
                            f"{key} tidak cocok: recipe={m[key]!r} "
                            f"transkrip={' '.join(w['word'] for w in sample)!r}")
        return start, end, clip_words, warnings

    start, end = float(m["start_time"]), float(m["end_time"])
    clip_words = [w for w in words if start - 0.05 <= w["start"] < end]
    return start, end, clip_words, warnings


def caption_style_line(captions: dict) -> str:
    c = captions
    return (
        f"Style: Cap,{c['font']},{c['size']},&H00FFFFFF,&H0000FFFF,"
        f"&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,"
        f"{c['margin_lr']},{c['margin_lr']},{c['margin_v']},1"
    )


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    mn = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{mn:02d}:{s:05.2f}"


def build_ass(recipe: dict, words: list, max_duration: float | None = None):
    """Bangun ASS lengkap (hook + caption word-by-word) dari recipe.

    Mengembalikan (ass_text, info). max_duration membatasi klip untuk
    render pratinjau pendek tanpa mengubah recipe.
    """
    start, end, clip_words, warnings = resolve_moment(recipe, words)
    dur = end - start
    if max_duration is not None:
        dur = min(dur, max_duration)
        clip_words = [w for w in clip_words if w["start"] - start < dur]
    cap = recipe["captions"]
    hk = recipe["hook"]

    groups, cur = [], []
    for w in clip_words:
        if cur and (len(cur) >= cap["max_words"]
                    or w["start"] - cur[-1]["end"] > cap["gap_split"]):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)

    header = (
        "[Script Info]\n"
        "Title: Word-by-word captions\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        + caption_style_line(cap) + "\n"
        + hook_style_line(font_size=hk["font_size"],
                          margin_v=hk["margin_v"]) + "\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )

    events = []
    if hk["text"]:
        events.append(hook_event(
            hk["text"], keyword=hk["keyword"],
            start=float(hk["start"]),
            end=float(hk["start"]) + float(hk["duration"]),
            animation=hk["animation"]))
    for g in groups:
        for i, w in enumerate(g):
            t_start = w["start"] - start
            t_end = ((g[i + 1]["start"] if i + 1 < len(g)
                      else w["end"] + 0.25) - start)
            parts = []
            for j, gw in enumerate(g[:i + 1]):
                txt = gw["word"].strip().upper()
                if j == i:
                    parts.append(r"{\c&H00D7FF&}" + txt + r"{\c&HFFFFFF&}")
                else:
                    parts.append(txt)
            events.append(
                f"Dialogue: 0,{_ass_time(t_start)},"
                f"{_ass_time(min(t_end, dur))},Cap,,0,0,0,,"
                f"{' '.join(parts)}")

    info = {
        "start": start, "end": start + dur, "duration": dur,
        "words": len(clip_words), "caption_events": len(events),
        "warnings": warnings,
    }
    return header + "\n".join(events) + "\n", info


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Pakai: python clip_recipe.py <recipe.json>")
        raise SystemExit(2)
    r = load_recipe(sys.argv[1])
    ws = load_words(r)
    ass, info = build_ass(r, ws)
    _, _, clip_words, _ = resolve_moment(r, ws)
    print(f"recipe        : {r['name']}")
    print(f"momen         : {info['start']:.2f} -> {info['end']:.2f} "
          f"({info['duration']:.2f} dtk)")
    print(f"kata          : {info['words']} "
          f"(pertama: {clip_words[0]['word'].strip()!r}, "
          f"terakhir: {clip_words[-1]['word'].strip()!r})")
    print(f"event ASS     : {info['caption_events']} (termasuk hook)")
    for w in info["warnings"]:
        print(f"WARNING       : {w}")
    hook_line = next((ln for ln in ass.splitlines()
                      if ln.startswith("Dialogue: 1,")), "(tanpa hook)")
    print(f"hook          : {hook_line}")
