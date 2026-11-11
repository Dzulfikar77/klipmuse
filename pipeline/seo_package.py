r"""
seo_package.py — Pembangun paket SEO Shorts berbasis data saran NYATA.

Langkah roadmap #3 proyek clipper (standar lengkap: SEO-STANDARD.md).
Sumber keyword utama saat ini: YouTube autocomplete (endpoint
suggestqueries, ds=yt, gl=US, hl=en) — gratis, tanpa akun, dan frasa yang
muncul adalah frasa yang benar-benar dicari orang. Volume angka pasti
(DataForSEO) menyusul bila akun pengguna aktif; setiap paket yang dibuat
tanpanya WAJIB mencantumkan catatan itu.

Isi paket: 3 varian judul (diskoring), deskripsi, hashtag, 15–20 tags
(ditandai mana yang didukung saran nyata), komentar tersemat, dan skor
paket 0–100 mengikuti scorecard di SEO-STANDARD.md:
  >=80 kuat, kirim · 60–79 boleh, perbaiki yang bolong · <60 buat ulang.

CARA PAKAI:

    from seo_package import build_package
    md = build_package(
        titles=[...3 judul...], description="...", tags=[...],
        hashtags=["#shorts", ...], pinned_comment="...",
        primary_keyword="world war 3", keyword_variants=["ww3"],
        entity="Robert Pape",
        seeds=["world war 3", "robert pape"],
        out_path="outputs/<klip>/seo-package-v2.md")
"""

import json
import re
import urllib.parse
import urllib.request

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"


def fetch_suggestions(seed, gl="US", hl="en"):
    """Saran autocomplete YouTube untuk satu frasa (urutan = peringkat saran)."""
    q = urllib.parse.quote(seed)
    url = f"{SUGGEST_URL}?client=firefox&ds=yt&hl={hl}&gl={gl}&q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    return data[1] if len(data) > 1 else []


def expand_seed(seed):
    """Alphabet soup: seed + ' a'..' z' untuk menambang long-tail nyata."""
    seen, out = set(), []

    def add(items):
        for s in items:
            key = s.lower().strip()
            if key and key not in seen:
                seen.add(key)
                out.append(s)

    add(fetch_suggestions(seed))
    for ch in "abcdefghijklmnopqrstuvwxyz":
        add(fetch_suggestions(f"{seed} {ch}"))
    return out


def collect_keywords(seeds, expand_first=True):
    """{seed: [saran...]}; seed pertama ditambang penuh (alphabet soup)."""
    result = {}
    for i, seed in enumerate(seeds):
        result[seed] = (expand_seed(seed) if (expand_first and i == 0)
                        else fetch_suggestions(seed))
    return result


def _norm(s):
    return re.sub(r"\s+", " ", s.lower().strip())


def tag_supported(tag, all_suggestions):
    """Tag didukung bila sama persis dengan saran, atau seluruh katanya
    terkandung dalam satu saran nyata."""
    t = _norm(tag)
    twords = set(t.split())
    for s in all_suggestions:
        sn = _norm(s)
        if t == sn or twords <= set(sn.split()):
            return True
    return False


def _title_points(title, primary_keyword, keyword_variants, entity):
    t = title.lower()
    kw_hit = (primary_keyword.lower() in t
              or any(v.lower() in t for v in keyword_variants))
    curiosity = ("?" in title or ":" in title
                 or bool(re.search(r"\d", title)))
    return {
        "kata kunci utama hadir (15)": (15 if kw_hit else 0),
        "<= 55 karakter (10)": (10 if len(title) <= 55 else 0),
        "pemicu penasaran (10)": (10 if curiosity else 0),
        "nama entitas hadir (10)": (10 if entity.lower() in t else 0),
    }


def score_package(titles, description, tags, hashtags, primary_keyword,
                  keyword_variants, entity, supported_count):
    """Skor 0–100 sesuai scorecard SEO-STANDARD.md + rinciannya."""
    per_title = [(t, _title_points(t, primary_keyword,
                                   keyword_variants, entity))
                 for t in titles]
    best_title, best_pts = max(per_title,
                               key=lambda x: sum(x[1].values()))
    breakdown = dict(best_pts)
    desc_low = description.lower()
    breakdown["kata kunci di 100 karakter pertama deskripsi (10)"] = (
        10 if primary_keyword.lower() in desc_low[:100] else 0)
    link = 5 if "http" in desc_low else 0
    cta = 5 if ("subscribe" in desc_low or "follow" in desc_low) else 0
    breakdown["link sumber (5) + CTA (5)"] = link + cta
    breakdown["tags 15-20 buah (10)"] = (
        10 if 15 <= len(tags) <= 20 else 0)
    share = supported_count / max(len(tags), 1)
    breakdown["tags didukung saran nyata >= 50% (10)"] = (
        10 if share >= 0.5 else 0)
    breakdown["tags total <= 500 karakter (5)"] = (
        5 if sum(len(t) + 2 for t in tags) <= 500 else 0)
    hs = [h.lower() for h in hashtags]
    breakdown["hashtag 3-5 + #shorts (10)"] = (
        10 if 3 <= len(hs) <= 5 and "#shorts" in hs else 0)
    total = sum(breakdown.values())
    verdict = (">=80 KUAT — kirim" if total >= 80 else
               "60-79 BOLEH — perbaiki yang bolong" if total >= 60 else
               "<60 BUAT ULANG")
    return {"total": total, "verdict": verdict, "breakdown": breakdown,
            "per_title": per_title, "best_title": best_title,
            "supported_share": share}


def build_package(titles, description, tags, hashtags, pinned_comment,
                  primary_keyword, keyword_variants, entity, seeds,
                  out_path, clip_label=""):
    """Ambil data saran, skor paket, tulis seo-package (markdown)."""
    kw = collect_keywords(seeds)
    all_sugg = [s for v in kw.values() for s in v]
    supported = {t: tag_supported(t, all_sugg) for t in tags}
    sc = score_package(titles, description, tags, hashtags,
                       primary_keyword, keyword_variants, entity,
                       sum(supported.values()))
    lines = [f"# Paket SEO v2 — {clip_label}", ""]
    lines.append(f"## Skor paket: {sc['total']}/100 — {sc['verdict']}")
    lines.append("")
    for k, v in sc["breakdown"].items():
        lines.append(f"- [{'x' if v else ' '}] {k}: {v}")
    lines.append("")
    lines.append("## Judul (pilih skor tertinggi; semua diuji)")
    for t, pts in sc["per_title"]:
        mark = " ← TERBAIK" if t == sc["best_title"] else ""
        lines.append(f"- ({sum(pts.values())}/45) {t}{mark}")
    lines.append("")
    lines.append("## Deskripsi")
    lines.append("```")
    lines.append(description)
    lines.append("```")
    lines.append("")
    lines.append("## Hashtag")
    lines.append(" ".join(hashtags))
    lines.append("")
    lines.append(f"## Tags ({len(tags)} buah, "
                 f"{sum(len(t) + 2 for t in tags)} karakter; "
                 f"{sum(supported.values())} didukung saran nyata)")
    for t in tags:
        lines.append(f"- {t}{' ✓saran-nyata' if supported[t] else ''}")
    lines.append("")
    lines.append("## Komentar tersemat (sematkan saat upload)")
    lines.append(pinned_comment)
    lines.append("")
    lines.append("## Bukti keyword (YouTube autocomplete, US/en, hari ini)")
    for seed, sugg in kw.items():
        lines.append(f"- **{seed}**: {', '.join(sugg[:12])}"
                     + (f" … (+{len(sugg) - 12} long-tail dari alphabet "
                        f"soup)" if len(sugg) > 12 else ""))
    lines.append("")
    lines.append("> Catatan: volume pencarian angka pasti BELUM divalidasi "
                 "DataForSEO (akun pengguna belum aktif). Bukti di atas "
                 "adalah saran pencarian nyata YouTube — sinyal permintaan "
                 "yang sah, bukan volume.")
    md = "\n".join(lines) + "\n"
    if out_path:
        with open(out_path, "w") as fh:
            fh.write(md)
    return md


if __name__ == "__main__":
    # Demo: paket v2 untuk klip podcast Pape (momen WW3, 01:14:48–01:15:31).
    build_package(
        titles=[
            "Iran Expert: This Is How World War 3 Starts",
            "Robert Pape: World War III Looks Like This",
            "What World War 3 Actually Looks Like",
        ],
        description=(
            "Iran war expert Robert Pape explains what World War 3 would "
            "actually look like — and the pattern that starts it.\n\n"
            "From The Diary of a CEO with Steven Bartlett. Full episode: "
            "https://www.youtube.com/watch?v=a1mI-ozLyYM\n\n"
            "Subscribe for one sharp clip a day.\n\n"
            "#shorts #worldwar3 #iran #geopolitics #diaryofaceo"),
        tags=[
            "world war 3", "world war iii", "ww3", "robert pape",
            "robert pape diary of a ceo", "diary of a ceo",
            "robert pape interview", "robert pape latest",
            "iran war expert", "how world war 3 starts",
            "world war 3 explained", "iran war", "us iran war",
            "middle east war", "geopolitics", "steven bartlett",
            "diary of a ceo clips", "world war 3 prediction",
        ],
        hashtags=["#shorts", "#worldwar3", "#iran", "#geopolitics",
                  "#diaryofaceo"],
        pinned_comment=("Pape says WW3 won't start with a bang, but with a "
                        "pattern. What's the first sign you'd watch for?"),
        primary_keyword="world war 3",
        keyword_variants=["ww3", "world war iii"],
        entity="Robert Pape",
        seeds=["world war 3", "robert pape", "diary of a ceo", "iran war"],
        out_path="examples/seo-package.md",
        clip_label="Podcast Pape — How Likely Is World War 3? (43 dtk)")
    print("seo-package-v2.md tertulis")
