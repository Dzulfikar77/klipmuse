r"""
hook_overlay.py — Modul hook overlay untuk pipeline clipper proyek ini.

Menambah SATU layer teks hook besar di detik-detik awal klip Short,
ala hook overlay OpenShorts, memakai gaya ASS yang terpisah dari caption
word-by-word. Dirancang untuk frame 1080x1920 (PlayRes sama dengan caption).

Spesifikasi gaya (sesuai keputusan proyek 2026-11-10):
- Teks hook 3–6 kata, EN, HURUF BESAR — celah penasaran dari kalimat hook
  momen terpilih, BUKAN judul lengkap. Contoh: "ARE WE IN WW3?" /
  "THEY PAID HIM $5?!" / "HE NEVER SAW IT COMING".
- 1 kata kunci diwarnai kuning/gold (&H00D7FF& — sama dengan kata aktif
  caption proyek), sisanya putih; outline hitam tebal (5).
- Font: DejaVu Sans, Bold, ukuran 118 (tersedia di /usr/share/fonts).
- Posisi: Alignment 8 (atas-tengah), MarginV 560 → pita aman TENGAH frame
  (zona aman produksi: y 480–1440 dari 1920, lihat PRODUCTION-STANDARD.md).

FLEKSIBILITAS (ditambahkan 2026-11-10 malam, fondasi "recipe JSON"):
hook_event() kini menerima parameter per klip — semua opsional, dan
nilai defaultnya menghasilkan output yang PERSIS sama dengan versi lama:
- animation : preset animasi, salah satu dari ANIMATIONS
              ("fade_scale" bawaan lama, "fade", "pop", "zoom_out",
              "rise", "none").
- margin_v  : override MarginV per event (menggeser posisi vertikal hook
              tanpa mengubah style global).
- font_size : override ukuran font per event (tag \fs).
- alignment : override alignment per event (tag \an; 8 = atas-tengah).
hook_style_line(font_size=..., margin_v=..., font=...) membangun baris
Style terparameter; HOOK_STYLE_LINE tetap konstanta default lama.

CARA PAKAI: lihat RECIPE.md — jalur yang disarankan sekarang adalah
clip_recipe.py (recipe JSON per klip). Pemakaian langsung tetap didukung:

    from hook_overlay import HOOK_STYLE_LINE, hook_event
    events.insert(0, hook_event("ARE WE IN WW3?", keyword="WW3"))
    # keyword opsional; defaultnya kata TERAKHIR dianggap kata kunci.
    # Hook dua baris: pisahkan manual dengan r"\N".
    # Fleksibel: hook_event("...", start=1.0, end=4.5,
    #                       animation="pop", font_size=96, margin_v=700)

Fungsi hook_event() mengembalikan string baris Dialogue ASS lengkap.
"""

# Baris Style untuk blok [V4+ Styles]. Nama style: "Hook".
# Format: Name, Fontname, Fontsize, Primary, Secondary, Outline, Back,
# Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
# BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
def hook_style_line(font_size: int = 118, margin_v: int = 560,
                    font: str = "DejaVu Sans") -> str:
    """Bangun baris Style Hook dengan parameter; default = gaya proyek."""
    return (
        f"Style: Hook,{font},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,"
        f"&H64000000,-1,0,0,0,100,100,0,0,1,5,1,8,40,40,{margin_v},1"
    )


HOOK_STYLE_LINE = hook_style_line()

GOLD = r"{\c&H00D7FF&}"
WHITE = r"{\c&HFFFFFF&}"

#: Preset animasi yang didukung hook_event().
ANIMATIONS = ("fade_scale", "fade", "pop", "zoom_out", "rise", "none")


def _anim_tag(animation: str, margin_v: int) -> str:
    """Blok tag ASS untuk satu preset animasi.

    "fade_scale" menghasilkan string yang persis sama dengan versi
    pertama modul ini (fad 150/450 + scale-in 135% -> 100% dlm 220 ms).
    "rise" memakai \\move menuju posisi margin_v (anchor atas-tengah,
    x=540 adalah tengah frame 1080).
    """
    if animation == "fade_scale":
        return r"{\fad(150,450)\fscx135\fscy135\t(0,220,\fscx100\fscy100)}"
    if animation == "fade":
        return r"{\fad(200,400)}"
    if animation == "pop":
        return r"{\fad(80,300)\fscx55\fscy55\t(0,180,\fscx100\fscy100)}"
    if animation == "zoom_out":
        return r"{\fad(120,400)\fscx185\fscy185\t(0,380,\fscx100\fscy100)}"
    if animation == "rise":
        return (
            r"{\move(540," + f"{margin_v + 90},540,{margin_v},0,240"
            r")\fad(120,400)}"
        )
    if animation == "none":
        return ""
    raise ValueError(
        f"Animasi hook tidak dikenal: {animation!r}. Pilihan: {ANIMATIONS}"
    )


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def hook_event(text: str, keyword: str | None = None,
               start: float = 0.0, end: float = 2.8,
               animation: str = "fade_scale",
               margin_v: int | None = None,
               font_size: int | None = None,
               alignment: int | None = None) -> str:
    """Bangun baris Dialogue ASS untuk hook overlay.

    text      : hook 3–6 kata (di-UPPERCASE otomatis; r"\\N" untuk
                memecah dua baris secara manual).
    keyword   : kata/frasa yang diwarnai gold. Harus muncul persis (case
                insensitive) di dalam text. Default: kata terakhir.
    start/end : jendela tampil dalam detik relatif terhadap awal klip
                (standar proyek: 0.0–2.8).
    animation : preset dari ANIMATIONS (default "fade_scale" = perilaku
                versi lama, byte-identik).
    margin_v  : bila diisi, MarginV event menimpa MarginV style —
                menggeser hook vertikal per klip.
    font_size : bila diisi, menimpa ukuran font style lewat tag \\fs.
    alignment : bila diisi, menimpa alignment style lewat tag \\an.
    """
    if end <= start:
        raise ValueError(f"end ({end}) harus > start ({start})")
    anim = _anim_tag(animation, margin_v if margin_v is not None else 560)

    # Override per event (blok tag terpisah; kosong bila tidak dipakai,
    # sehingga output default tetap identik dengan versi lama).
    overrides = ""
    if alignment is not None:
        overrides += rf"\an{alignment}"
    if font_size is not None:
        overrides += rf"\fs{font_size}"
    if overrides:
        overrides = "{" + overrides + "}"

    words = text.upper().split()
    if keyword is None:
        keyword = words[-1] if words else ""
    kw = keyword.upper()

    # Warnai kemunculan pertama kata kunci dengan gold.
    rendered = text.upper()
    if kw and kw in rendered:
        rendered = rendered.replace(kw, GOLD + kw + WHITE, 1)

    mv_field = margin_v if margin_v is not None else 0
    return (
        f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},Hook,,0,0,"
        f"{mv_field},,{anim}{overrides}{rendered}"
    )


if __name__ == "__main__":
    # Demo cepat: python hook_overlay.py
    print(HOOK_STYLE_LINE)
    print(hook_event("Are we in WW3?", keyword="WW3"))
    print(hook_event("They paid him five dollars?"))
    print(hook_event("He called the rival", keyword="RIVAL",
                     start=1.0, end=4.5, animation="pop",
                     font_size=96, margin_v=700))
