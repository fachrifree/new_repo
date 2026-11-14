"""Shared engine for the "Kenapa Begini? Kenapa Begitu?" video series.

Each episode script defines SCENES (narration lines) and scene draw functions,
then calls kbkb.run(SCENES, SCENE_FN, default_out).
"""
import argparse
import math
import os
import random
import subprocess
import sys
import tempfile
import wave
from multiprocessing import Pool

import cairo
import numpy as np

W, H = 1080, 1920
FPS = 30
SR = 44100
FONT = "Inter"
VOICE = ["-v", "mb-id1", "-s", "150", "-p", "58"]

# --------------------------------------------------------------------------
GAP = 0.26
LEAD = 0.55
TAIL = 0.75


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------
def load_wav_44k(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


EDGE_VOICE = os.environ.get("KBKB_VOICE", "id-ID-GadisNeural")
EDGE_ARGS = ["--rate=+12%", "--pitch=+6Hz"]


def tts(text, path):
    """Neural voice via edge-tts (natural); falls back to offline espeak-ng/MBROLA."""
    mp3 = path[:-4] + ".mp3"
    cmd = ["edge-tts", "--voice", EDGE_VOICE, *EDGE_ARGS, "--text", text, "--write-media", mp3]
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        cmd[1:1] = ["--proxy", proxy]
    ok = False
    if os.environ.get("KBKB_TTS", "edge") == "edge":
        for _ in range(3):
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0 and os.path.exists(mp3) and os.path.getsize(mp3) > 1000:
                ok = True
                break
        if not ok:
            print("  ! edge-tts unavailable, falling back to espeak-ng", file=sys.stderr)
    if ok:
        a = load_wav_44k(mp3)
    else:
        subprocess.run(["espeak-ng", *VOICE, "-w", path, text], check=True)
        a = load_wav_44k(path)
    # trim leading/trailing silence
    nz = np.where(np.abs(a) > 0.01)[0]
    if len(nz):
        a = a[max(0, nz[0] - 400): nz[-1] + 1600]
    return a


def build_timeline(tmp, SCENES):
    """Synthesize narration and lay out scene/line timings."""
    t = 0.0
    voice_parts = []
    for si, sc in enumerate(SCENES):
        sc["start"] = t
        lt = sc.get("lead", LEAD)
        sc["cues"] = []
        for li, (sub, spoken) in enumerate(sc["lines"]):
            a = tts(spoken or sub, os.path.join(tmp, f"vo_{si}_{li}.wav"))
            a = a / (np.max(np.abs(a)) + 1e-9) * 0.85
            d = len(a) / SR
            sc["cues"].append((lt, lt + d))
            voice_parts.append((t + lt, a))
            lt += d + GAP
        sc["dur"] = lt - GAP + sc.get("tail", TAIL)
        t += sc["dur"]
    total = t
    n = int(math.ceil(total * SR)) + SR
    voice = np.zeros(n, np.float32)
    for st, a in voice_parts:
        i = int(st * SR)
        voice[i:i + len(a)] += a
    return total, voice


def adsr_note(freq, dur, amp, kind="pluck"):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    if kind == "pluck":
        env = np.exp(-tt * 7.0) * np.minimum(1, tt / 0.004)
        sig = (np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(4 * np.pi * freq * tt)
               + 0.12 * np.sin(6 * np.pi * freq * tt))
    elif kind == "bass":
        env = np.exp(-tt * 3.0) * np.minimum(1, tt / 0.01)
        sig = np.sin(2 * np.pi * freq * tt) + 0.2 * np.sin(4 * np.pi * freq * tt)
    else:  # bell
        env = np.exp(-tt * 4.0) * np.minimum(1, tt / 0.002)
        sig = np.sin(2 * np.pi * freq * tt) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * tt)
    return (sig * env * amp).astype(np.float32)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def build_music(total):
    n = int(math.ceil(total * SR)) + SR
    mus = np.zeros(n, np.float32)
    bpm = 104
    beat = 60 / bpm
    # C  G  Am  F   (I V vi IV), voiced around C5
    chords = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]
    roots = [36, 43, 45, 41]
    pattern = [0, 1, 2, 3, 2, 1, 2, 3]  # index into chord+octave
    rng = np.random.default_rng(7)
    t = 0.0
    bar = 0
    while t < total:
        ch = chords[bar % 4]
        notes = list(ch) + [ch[0] + 12]
        for k in range(8):
            st = t + k * beat / 2
            if st >= total:
                break
            m = notes[pattern[k]] + 12
            nt = adsr_note(midi(m), 0.5, 0.16, "pluck")
            i = int(st * SR)
            mus[i:i + len(nt)] += nt[: max(0, n - i)]
            # soft hat on offbeats
            if k % 2 == 1:
                hn = int(0.04 * SR)
                noise = rng.standard_normal(hn).astype(np.float32)
                noise = np.diff(noise, prepend=0) * np.exp(-np.arange(hn) / SR * 90) * 0.03
                mus[i:i + hn] += noise[: max(0, n - i)]
        for k in (0, 2):
            st = t + k * beat
            nt = adsr_note(midi(roots[bar % 4]), beat * 1.8, 0.33, "bass")
            i = int(st * SR)
            mus[i:i + len(nt)] += nt[: max(0, n - i)]
        t += 4 * beat
        bar += 1
    return mus


def sfx_pop(amp=0.35):
    d = 0.12
    tt = np.arange(int(d * SR)) / SR
    f = 500 + 1400 * tt / d
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-tt * 30) * amp).astype(np.float32)


def sfx_whoosh(amp=0.18):
    d = 0.45
    n = int(d * SR)
    rng = np.random.default_rng(3)
    x = rng.standard_normal(n).astype(np.float32)
    # simple one-pole lowpass with sweeping coefficient
    y = np.zeros(n, np.float32)
    acc = 0.0
    for i in range(n):
        c = 0.05 + 0.4 * math.sin(math.pi * i / n)
        acc += c * (x[i] - acc)
        y[i] = acc
    env = np.sin(np.pi * np.arange(n) / n) ** 2
    return y * env * amp


def mix_audio(total, voice, events):
    music = build_music(total)
    n = len(voice)
    music = music[:n]
    # duck music under voice
    env = np.abs(voice)
    k = int(0.25 * SR)
    kern = np.ones(k, np.float32) / k
    env = np.convolve(env, kern, mode="same")
    duck = 1.0 - 0.55 * np.clip(env / 0.08, 0, 1)
    fade = np.ones(n, np.float32)
    fo = int(2.0 * SR)
    end = int(total * SR)
    fade[end - fo:end] = np.linspace(1, 0, fo)
    fade[end:] = 0
    fi = int(0.4 * SR)
    fade[:fi] *= np.linspace(0, 1, fi)
    out = voice + music * 0.55 * duck * fade
    for st, s in events:
        i = int(st * SR)
        if i < n:
            out[i:i + len(s)] += s[: n - i]
    out = out[:end]
    peak = np.max(np.abs(out))
    out = out / peak * 0.95 if peak > 0.95 else out
    return out


def write_wav(path, a):
    pcm = (np.clip(a, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_io(x):
    return 3 * x * x - 2 * x * x * x


def ease_back(x):
    c1, c3 = 1.70158, 2.70158
    return max(0.0, 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2) if x > 0 else 0.0


def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def lerpc(c1, c2, k):
    return tuple(a + (b - a) * k for a, b in zip(c1, c2))


def vgrad(ctx, stops, y0=0, y1=H):
    g = cairo.LinearGradient(0, y0, 0, y1)
    for off, col in stops:
        g.add_color_stop_rgba(off, *col)
    ctx.set_source(g)
    ctx.paint()


def rrect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def set_font(ctx, size, weight="bold"):
    fam = {"bold": "Inter", "black": "Inter ExtraBold", "semi": "Inter SemiBold"}[weight]
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if weight != "semi" else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def text(ctx, s, x, y, size, color=(1, 1, 1, 1), weight="bold", align="c",
         stroke=None, sw=0, scale=1.0, alpha=1.0, rot=0.0):
    """Draw text with its baseline-centre at (x, y)."""
    if alpha <= 0 or scale <= 0.001:
        return
    ctx.save()
    ctx.translate(x, y)
    if rot:
        ctx.rotate(rot)
    ctx.scale(scale, scale)
    set_font(ctx, size, weight)
    xb, yb, tw, th, xa, ya = ctx.text_extents(s)
    ox = {"c": -tw / 2 - xb, "l": -xb, "r": -tw - xb}[align]
    ctx.move_to(ox, th / 2 - (th + yb))  # vertically centred
    ctx.text_path(s)
    if stroke:
        ctx.set_source_rgba(*stroke[:3], stroke[3] * alpha)
        ctx.set_line_width(sw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*color[:3], color[3] * alpha)
    ctx.fill()
    ctx.restore()


def text_width(ctx, s, size, weight="bold"):
    set_font(ctx, size, weight)
    return ctx.text_extents(s)[4]


def wrap(ctx, s, size, maxw, weight="bold"):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if text_width(ctx, trial, size, weight) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def rich_line(ctx, parts, x, y, size, scale=1.0, alpha=1.0, stroke=hexc("#1b1446"), sw=14):
    """parts: list of (text, color). Centered at x."""
    total = sum(text_width(ctx, p, size, "black") for p, _ in parts)
    cx = x - total * scale / 2
    for p, col in parts:
        wdt = text_width(ctx, p, size, "black") * scale
        text(ctx, p, cx, y, size, col, "black", "l", stroke, sw, scale, alpha)
        cx += wdt


def sun(ctx, x, y, r, t, alpha=1.0):
    ctx.save()
    ctx.translate(x, y)
    g = cairo.RadialGradient(0, 0, r * 0.5, 0, 0, r * 2.6)
    g.add_color_stop_rgba(0, 1, 0.95, 0.55, 0.55 * alpha)
    g.add_color_stop_rgba(1, 1, 0.9, 0.4, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, r * 2.6, 0, 2 * math.pi)
    ctx.fill()
    ctx.rotate(t * 0.4)
    ctx.set_source_rgba(1, 0.86, 0.3, alpha)
    for i in range(12):
        a = i * math.pi / 6
        ctx.move_to(math.cos(a - 0.12) * r * 1.1, math.sin(a - 0.12) * r * 1.1)
        ctx.line_to(math.cos(a) * r * 1.55, math.sin(a) * r * 1.55)
        ctx.line_to(math.cos(a + 0.12) * r * 1.1, math.sin(a + 0.12) * r * 1.1)
        ctx.close_path()
    ctx.fill()
    ctx.set_source_rgba(1, 0.82, 0.2, alpha)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_source_rgba(1, 0.95, 0.6, alpha)
    ctx.arc(-r * 0.25, -r * 0.25, r * 0.55, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def cloud(ctx, x, y, s, alpha=0.95, col=(1, 1, 1)):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.set_source_rgba(*col[:3], alpha)
    for cx, cy, r in [(-70, 10, 45), (-20, -20, 60), (45, -5, 50), (85, 18, 35), (10, 22, 45)]:
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()


def character(ctx, x, y, s, t, mouth=0.0, look=(0, 0), wave=False, mood="happy", alpha=1.0):
    """Tanya, the curious host."""
    ctx.save()
    ctx.translate(x, y + math.sin(t * 3.2) * 6 * s)
    ctx.scale(s, s)
    ctx.push_group()
    outline = hexc("#2a1f4d")
    lw = 7
    # body / shirt
    rrect(ctx, -95, 95, 190, 200, 70)
    ctx.set_source_rgba(*hexc("#FFC93C"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*outline)
    ctx.set_line_width(lw)
    ctx.stroke()
    # "?" logo on shirt
    text(ctx, "?", 0, 190, 90, hexc("#6C3BFF"), "black")
    # arms
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for side in (-1, 1):
        ctx.save()
        ctx.translate(side * 85, 140)
        if wave and side == 1:
            ang = -0.95 + 0.35 * math.sin(t * 9)
        else:
            ang = math.pi / 2 - side * 0.5
        ctx.rotate(ang)
        ctx.move_to(0, 0)
        ctx.line_to(110, 0)
        ctx.set_source_rgba(*outline)
        ctx.set_line_width(34)
        ctx.stroke()
        ctx.move_to(0, 0)
        ctx.line_to(110, 0)
        ctx.set_source_rgba(*hexc("#FFC93C"))
        ctx.set_line_width(22)
        ctx.stroke()
        ctx.arc(118, 0, 22, 0, 2 * math.pi)
        ctx.set_source_rgba(*hexc("#F6C29A"))
        ctx.fill_preserve()
        ctx.set_source_rgba(*outline)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.restore()
    # head
    ctx.arc(0, 0, 120, 0, 2 * math.pi)
    ctx.set_source_rgba(*hexc("#F6C29A"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*outline)
    ctx.set_line_width(lw)
    ctx.stroke()
    # hair
    ctx.save()
    ctx.arc(0, 0, 124, math.pi * 1.02, math.pi * 1.98)
    ctx.curve_to(90, -40, 40, -70, 0, -62)
    ctx.curve_to(-40, -70, -90, -40, -124, -6)
    ctx.close_path()
    ctx.set_source_rgba(*hexc("#3b2a20"))
    ctx.fill()
    # ahoge curl
    ctx.move_to(5, -118)
    ctx.curve_to(10, -175, 70, -170, 50, -135)
    ctx.set_line_width(12)
    ctx.set_source_rgba(*hexc("#3b2a20"))
    ctx.stroke()
    ctx.restore()
    # eyes
    blink = 1.0
    bt = (t + 0.7) % 3.4
    if bt < 0.14:
        blink = abs(bt - 0.07) / 0.07
    lx, ly = look
    for side in (-1, 1) if mood == "yuck" else ():
        # squeezed ">  <" eyes
        ctx.move_to(side * 65, -12)
        ctx.line_to(side * 30, 5)
        ctx.line_to(side * 65, 22)
        ctx.set_line_width(9)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(*outline)
        ctx.stroke()
    for side in (-1, 1) if mood != "yuck" else ():
        ex, ey = side * 45, 5
        ctx.save()
        ctx.translate(ex, ey)
        ctx.scale(1, max(0.08, blink))
        ctx.arc(0, 0, 26, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 1)
        ctx.fill_preserve()
        ctx.set_source_rgba(*outline)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.arc(lx * 9, ly * 9, 15, 0, 2 * math.pi)
        ctx.set_source_rgba(*outline)
        ctx.fill()
        ctx.arc(lx * 9 + 5, ly * 9 - 6, 5, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 1)
        ctx.fill()
        ctx.restore()
    # brows
    ctx.set_line_width(7)
    ctx.set_source_rgba(*hexc("#3b2a20"))
    for side in (-1, 1):
        lift = -8 if mood == "curious" and side == 1 else 0
        ctx.move_to(side * 25, -44 + lift)
        ctx.line_to(side * 65, -38 + lift)
        ctx.stroke()
    # cheeks
    for side in (-1, 1):
        ctx.arc(side * 78, 45, 16, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.45, 0.5, 0.45)
        ctx.fill()
    # mouth
    if mood == "yuck" and mouth <= 0.08:
        # wavy mouth with tongue out
        ctx.save()
        ctx.translate(0, 62)
        ctx.scale(1, 0.7)
        ctx.arc(8, 14, 18, 0, math.pi)
        ctx.restore()
        ctx.set_source_rgba(*hexc("#FF7A8A"))
        ctx.fill_preserve()
        ctx.set_source_rgba(*outline)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.move_to(-34, 62)
        for k in range(1, 9):
            ctx.line_to(-34 + k * 8.5, 62 + (6 if k % 2 else -6))
        ctx.set_line_width(7)
        ctx.stroke()
    elif mouth > 0.08:
        h_ = 10 + 34 * mouth
        ctx.save()
        ctx.translate(0, 62)
        ctx.scale(1, h_ / 30)
        ctx.arc(0, 0, 30, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(*hexc("#8a2333"))
        ctx.fill_preserve()
        ctx.set_source_rgba(*outline)
        ctx.set_line_width(5)
        ctx.stroke()
    elif mood == "curious":
        ctx.arc(0, 66, 12, 0, 2 * math.pi)
        ctx.set_source_rgba(*hexc("#8a2333"))
        ctx.fill()
    else:
        ctx.arc(0, 45, 32, 0.2 * math.pi, 0.8 * math.pi)
        ctx.set_source_rgba(*outline)
        ctx.set_line_width(7)
        ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def bubble(ctx, x, y, w, h, fill, alpha=1.0, scale=1.0, tail=None):
    if scale <= 0.001 or alpha <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    ctx.push_group()
    rrect(ctx, -w / 2, -h / 2, w, h, min(h / 2, 40))
    if tail:
        tx, ty = tail
        ctx.move_to(tx - 30, h / 2 - 2)
        ctx.line_to(tx, ty)
        ctx.line_to(tx + 30, h / 2 - 2)
        ctx.close_path()
    ctx.set_source_rgba(*fill)
    ctx.fill_preserve()
    ctx.set_source_rgba(*hexc("#1b1446"))
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def rays_bg(ctx, cx, cy, t, col=(1, 1, 1, 0.07), n=18):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(t * 0.15)
    ctx.set_source_rgba(*col)
    for i in range(n):
        a0 = i * 2 * math.pi / n
        ctx.move_to(0, 0)
        ctx.arc(0, 0, 2400, a0, a0 + math.pi / n)
        ctx.close_path()
    ctx.fill()
    ctx.restore()


def wave_path(ctx, x, y0, y1, wl, amp, phase):
    ctx.move_to(x, y0)
    y = y0
    while y < y1:
        y = min(y + 4, y1)
        ctx.line_to(x + amp * math.sin(2 * math.pi * (y - y0) / wl - phase), y)


RAINBOW = [("Merah", "#FF4D4D"), ("Jingga", "#FF9A3C"), ("Kuning", "#FFE14D"),
           ("Hijau", "#4DD97A"), ("Biru", "#3D8BFF"), ("Ungu", "#9B5BFF")]
NAVY = hexc("#1b1446")

rnd = random.Random(42)
QMARKS = [(rnd.uniform(60, W - 60), rnd.uniform(150, H - 300), rnd.uniform(40, 110),
           rnd.choice(["?", "?", "!"]), rnd.choice(["#FFE14D", "#FF7AB6", "#7CF2C5", "#FFFFFF"]),
           rnd.uniform(0, 6.28)) for _ in range(16)]


# Scenes  (ctx, local time, scene dict, global time, mouth)
# --------------------------------------------------------------------------
def sc_intro(ctx, t, sc, gt, m):
    vgrad(ctx, [(0, hexc("#5B2BFF")), (0.55, hexc("#8E4BFF")), (1, hexc("#24C6FF"))])
    rays_bg(ctx, W / 2, 760, gt)
    for (x, y, s, ch, col, ph) in QMARKS:
        k = ease_back(prog(t, 0.1 + ph / 12, 0.6 + ph / 12))
        text(ctx, ch, x + math.sin(gt * 1.3 + ph) * 18, y + math.cos(gt * 1.7 + ph) * 22, s,
             hexc(col, 0.55), "black", scale=k, rot=math.sin(gt + ph) * 0.3)
    k1 = ease_back(prog(t, 0.25, 0.75))
    k2 = ease_back(prog(t, 0.7, 1.2))
    wob = math.sin(gt * 2.5) * 0.03
    text(ctx, "KENAPA", W / 2, 470, 120, hexc("#FFFFFF"), "black", stroke=NAVY, sw=18, scale=k1, rot=-0.05 + wob)
    text(ctx, "BEGINI?", W / 2, 610, 150, hexc("#FFE14D"), "black", stroke=NAVY, sw=20, scale=k1, rot=-0.05 + wob)
    text(ctx, "KENAPA", W / 2, 790, 120, hexc("#FFFFFF"), "black", stroke=NAVY, sw=18, scale=k2, rot=0.04 - wob)
    text(ctx, "BEGITU?", W / 2, 930, 150, hexc("#7CF2C5"), "black", stroke=NAVY, sw=20, scale=k2, rot=0.04 - wob)
    k3 = ease_back(prog(t, 1.4, 1.9))
    bubble(ctx, W / 2, 1080, 640, 96, hexc("#FF5C8A"), scale=k3)
    text(ctx, sc["label"], W / 2, 1080, 50, (1, 1, 1, 1), "black", scale=k3)
    kc = ease_out(prog(t, 0.9, 1.6))
    character(ctx, W / 2, 1360 + (1 - kc) * 500, 1.05, gt, m, (0, 0.2), wave=True)


def wave_path_h(ctx, x0, x1, wl, amp, phase):
    ctx.move_to(x0, 0)
    x = x0
    while x < x1:
        x = min(x + 4, x1)
        ctx.line_to(x, amp * math.sin(2 * math.pi * (x - x0) / wl - phase))



# --------------------------------------------------------------------------
# Overlays
# --------------------------------------------------------------------------
def draw_header(ctx, sc, t):
    if sc["key"] in ("intro",):
        return
    a = prog(t, 0, 0.4)
    ctx.push_group()
    rrect(ctx, 40, 40, 520, 64, 32)
    ctx.set_source_rgba(0.1, 0.07, 0.3, 0.55)
    ctx.fill()
    text(ctx, "Kenapa Begini? Kenapa Begitu?", 300, 72, 30, (1, 1, 1, 1), "black")
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)


def draw_subtitle(ctx, sc, t):
    for i, (a, b) in enumerate(sc["cues"]):
        if a - 0.05 <= t <= b + GAP * 0.9:
            s = sc["lines"][i][0]
            size = 48
            lines = wrap(ctx, s, size, 900)
            lh = size * 1.28
            bh = lh * len(lines) + 44
            yc = 1755
            al = prog(t, a - 0.05, a + 0.12) * (1 - prog(t, b + GAP * 0.6, b + GAP * 0.9))
            ctx.push_group()
            maxw = max(text_width(ctx, ln, size) for ln in lines)
            bw = maxw + 70
            rrect(ctx, W / 2 - bw / 2, yc - bh / 2, bw, bh, 30)
            ctx.set_source_rgba(0.06, 0.04, 0.18, 0.72)
            ctx.fill()
            for j, ln in enumerate(lines):
                yy = yc - (len(lines) - 1) * lh / 2 + j * lh
                text(ctx, ln, W / 2, yy, size, (1, 1, 1, 1), "bold")
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(al)
            return


def draw_transition(ctx, t, idx):
    if idx == 0:
        a = 1 - prog(t, 0, 0.35)
        if a > 0:
            ctx.set_source_rgba(0, 0, 0, a)
            ctx.paint()
        return
    k = prog(t, 0, 0.45)
    if k < 1:
        r = (1 - ease_out(k)) * 1300
        ctx.arc(W / 2, H / 2, r, 0, 2 * math.pi)
        ctx.set_source_rgba(*hexc("#FFE14D"))
        ctx.fill()


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
G = {}


def render(fi):
    gt = fi / FPS
    scenes = G["scenes"]
    idx = 0
    for i, sc in enumerate(scenes):
        if gt >= sc["start"]:
            idx = i
    sc = scenes[idx]
    lt = gt - sc["start"]
    env = G["mouth"]
    m = float(env[min(fi, len(env) - 1)])
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    fo = cairo.FontOptions()
    fo.set_antialias(cairo.ANTIALIAS_GRAY)
    fo.set_hint_style(cairo.HINT_STYLE_NONE)
    ctx.set_font_options(fo)
    G["scene_fn"][sc["key"]](ctx, lt, sc, gt, m)
    draw_header(ctx, sc, lt)
    draw_subtitle(ctx, sc, lt)
    draw_transition(ctx, lt, idx)
    # global fade out
    fade = prog(gt, G["total"] - 0.8, G["total"])
    if fade > 0:
        ctx.set_source_rgba(0, 0, 0, fade)
        ctx.paint()
    surf.flush()
    return bytes(surf.get_data())


def run(SCENES, SCENE_FN, default_out):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=default_out)
    ap.add_argument("--preview", type=float, default=0, help="only render N seconds")
    ap.add_argument("--stills", action="store_true", help="dump one PNG per scene and exit")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="kbkb_")
    total, voice = build_timeline(tmp, SCENES)
    print(f"total duration: {total:.1f}s")
    for sc in SCENES:
        print(f"  {sc['key']:9s} start={sc['start']:5.1f}s dur={sc['dur']:5.1f}s")

    # mouth envelope per video frame
    nfr = int(math.ceil(total * FPS))
    spf = SR // FPS
    mouth = np.zeros(nfr, np.float32)
    for f in range(nfr):
        seg = voice[f * spf:(f + 1) * spf]
        mouth[f] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0
    mouth = np.clip(mouth / (np.percentile(mouth[mouth > 0.01], 85) + 1e-6), 0, 1) if np.any(mouth > 0.01) else mouth
    G.update(scenes=SCENES, mouth=mouth, total=total, scene_fn=SCENE_FN)

    if args.stills:
        for sc in SCENES:
            f = int((sc["start"] + sc["cues"][-1][1]) * FPS)
            buf = render(f)
            s = cairo.ImageSurface.create_for_data(bytearray(buf), cairo.FORMAT_RGB24, W, H)
            s.write_to_png(os.path.join(tmp, f"still_{sc['key']}.png"))
        print("stills in", tmp)
        return

    events = []
    for i, sc in enumerate(SCENES):
        if i > 0:
            events.append((sc["start"] - 0.1, sfx_whoosh()))
    events += [(0.25, sfx_pop()), (0.7, sfx_pop()), (1.4, sfx_pop(0.25)),
               (SCENES[-1]["start"] + SCENES[-1]["cues"][-1][0], sfx_pop())]
    audio = mix_audio(total, voice, events)
    wav = os.path.join(tmp, "mix.wav")
    write_wav(wav, audio)

    if args.preview:
        nfr = min(nfr, int(args.preview * FPS))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count() or 2) as pool:
        for i, buf in enumerate(pool.imap(render, range(nfr), chunksize=6)):
            ff.stdin.write(buf)
            if i % 150 == 0:
                print(f"  frame {i}/{nfr}", flush=True)
    ff.stdin.close()
    ff.wait()
    if ff.returncode:
        sys.exit("ffmpeg failed")
    print("wrote", args.out)
