#!/usr/bin/env python3
"""
Kenapa Begini? Kenapa Begitu? — Episode 1: Kenapa Langit Berwarna Biru?

Generates a vertical (1080x1920) short video, fully offline:
  * narration  : espeak-ng + MBROLA Indonesian voice (mb-id1)
  * animation  : pycairo, drawn procedurally frame by frame
  * music/SFX  : synthesized with numpy
  * encoding   : ffmpeg (H.264 + AAC)

Requirements: python3, numpy, pycairo, ffmpeg, espeak-ng, mbrola-id1
Usage:        python3 make_video.py [--out episode.mp4] [--preview SECONDS]
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
# Script. Each line: (subtitle text, text sent to TTS or None = same)
# --------------------------------------------------------------------------
SCENES = [
    dict(key="intro", lead=1.3, lines=[
        ("Halo, teman-teman!", None),
        ("Selamat datang di Kenapa Begini, Kenapa Begitu!", None),
        ("Hari ini kita bahas sesuatu yang kita lihat setiap hari.", None),
    ]),
    dict(key="question", lines=[
        ("Pernah nggak, kamu bertanya… kenapa langit berwarna biru?",
         "Pernah nggak, kamu bertanya, kenapa langit berwarna biru?"),
        ("Kenapa bukan hijau, atau merah muda?", None),
    ]),
    dict(key="light", lines=[
        ("Cahaya matahari memang terlihat putih.", None),
        ("Tapi sebenarnya, di dalamnya ada banyak warna: merah, jingga, kuning, hijau, biru, dan ungu!", None),
    ]),
    dict(key="scatter", lines=[
        ("Saat masuk ke udara, cahaya menabrak partikel udara yang sangat kecil.", None),
        ("Cahaya merah gelombangnya panjang, jadi terus lurus.", None),
        ("Tapi cahaya biru gelombangnya pendek, jadi mudah terpantul ke segala arah!", None),
    ]),
    dict(key="sky", lines=[
        ("Cahaya biru yang tersebar ini memenuhi seluruh langit.", None),
        ("Ke mana pun kita memandang, yang sampai ke mata adalah biru.", None),
        ("Ungu juga tersebar, tapi mata kita lebih peka pada warna biru.", None),
    ]),
    dict(key="sunset", lines=[
        ("Lalu, kenapa langit sore berwarna jingga?", None),
        ("Saat matahari terbenam, cahayanya menempuh jalan yang jauh lebih panjang.", None),
        ("Birunya sudah habis tersebar di jalan, tinggal merah dan jingga yang sampai ke mata kita.", None),
    ]),
    dict(key="outro", lines=[
        ("Jadi, langit biru karena cahaya biru paling banyak dihamburkan oleh udara.", None),
        ("Para ilmuwan menyebutnya hamburan Rayleigh!", "Para ilmuwan menyebutnya hamburan Rélei!"),
        ("Punya pertanyaan lain? Tulis di kolom komentar ya.", None),
        ("Sampai jumpa!", None),
    ], tail=2.4),
]
GAP = 0.32
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


def tts(text, path):
    subprocess.run(["espeak-ng", *VOICE, "-w", path, text], check=True)
    a = load_wav_44k(path)
    # trim leading/trailing silence
    nz = np.where(np.abs(a) > 0.01)[0]
    if len(nz):
        a = a[max(0, nz[0] - 400): nz[-1] + 1600]
    return a


def build_timeline(tmp):
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


def cloud(ctx, x, y, s, alpha=0.95):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.set_source_rgba(1, 1, 1, alpha)
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
    for side in (-1, 1):
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
    if mouth > 0.08:
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
PARTICLES = [(rnd.uniform(80, W - 80), rnd.uniform(620, 1480), rnd.uniform(9, 17),
              rnd.uniform(0, 6.28)) for _ in range(46)]
SKYDOTS = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0, 6.28), rnd.uniform(60, 170),
            rnd.uniform(5, 11)) for _ in range(150)]


# --------------------------------------------------------------------------
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
    text(ctx, "Eps. 1 · Langit Biru", W / 2, 1080, 50, (1, 1, 1, 1), "black", scale=k3)
    kc = ease_out(prog(t, 0.9, 1.6))
    character(ctx, W / 2, 1360 + (1 - kc) * 500, 1.05, gt, m, (0, 0.2), wave=True)


def sc_question(ctx, t, sc, gt, m):
    vgrad(ctx, [(0, hexc("#3FA9FF")), (0.6, hexc("#9AD8FF")), (1, hexc("#E6F6FF"))])
    sun(ctx, 860, 300, 90, gt)
    for i, (cx, cy, s) in enumerate([(200, 330, 1.2), (700, 620, 0.9), (320, 820, 0.7)]):
        x = (cx + gt * 25 * (1 + i * 0.3)) % (W + 400) - 200
        cloud(ctx, x, cy, s)
    # hills
    ctx.set_source_rgba(*hexc("#5ED67A"))
    ctx.move_to(0, 1450)
    ctx.curve_to(300, 1330, 700, 1380, W, 1300)
    ctx.line_to(W, H)
    ctx.line_to(0, H)
    ctx.fill()
    ctx.set_source_rgba(*hexc("#3FBF60"))
    ctx.move_to(0, 1560)
    ctx.curve_to(400, 1480, 800, 1560, W, 1500)
    ctx.line_to(W, H)
    ctx.line_to(0, H)
    ctx.fill()
    c0, c1 = sc["cues"][0], sc["cues"][1]
    k = ease_back(prog(t, c0[0] + 1.0, c0[0] + 1.5))
    rich_line(ctx, [("Kenapa langit", hexc("#FFFFFF"))], W / 2, 470, 96, scale=k)
    rich_line(ctx, [("berwarna ", hexc("#FFFFFF")), ("BIRU?", hexc("#FFE14D"))], W / 2, 590, 110, scale=k)
    kq = ease_back(prog(t, c0[0] + 0.3, c0[0] + 0.8))
    bubble(ctx, 780, 1040, 170, 170, (1, 1, 1, 1), scale=kq, tail=(-50, 110))
    text(ctx, "?", 780, 1040, 140, hexc("#6C3BFF"), "black", scale=kq * (1 + 0.06 * math.sin(gt * 6)))
    ka = ease_back(prog(t, c1[0] + 0.5, c1[0] + 0.9))
    kb = ease_back(prog(t, c1[0] + 1.2, c1[0] + 1.6))
    bubble(ctx, 260, 800, 300, 100, hexc("#4DD97A"), scale=ka)
    text(ctx, "Hijau?", 260, 800, 56, (1, 1, 1, 1), "black", stroke=NAVY, sw=8, scale=ka)
    bubble(ctx, 800, 820, 380, 100, hexc("#FF7AB6"), scale=kb)
    text(ctx, "Merah muda?", 800, 820, 52, (1, 1, 1, 1), "black", stroke=NAVY, sw=8, scale=kb)
    character(ctx, 470, 1330, 1.0, gt, m, (0.6, -1), mood="curious")


def sc_light(ctx, t, sc, gt, m):
    vgrad(ctx, [(0, hexc("#0B0A2E")), (1, hexc("#221A5C"))])
    for i in range(60):
        rx = (i * 173) % W
        ry = (i * 331) % H
        tw = 0.4 + 0.6 * abs(math.sin(gt * 1.5 + i))
        ctx.arc(rx, ry, 2.2, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.35 * tw)
        ctx.fill()
    c0, c1 = sc["cues"]
    sun(ctx, W / 2, 420, 95, gt)
    kt = ease_back(prog(t, c0[0], c0[0] + 0.5))
    rich_line(ctx, [("Cahaya ", hexc("#FFFFFF")), ("putih", hexc("#FFE14D"))], W / 2, 180, 84, scale=kt)
    # white beam
    py = 960
    kb = ease_io(prog(t, c0[0] + 0.3, c0[0] + 1.4))
    if kb > 0:
        ctx.set_source_rgba(1, 1, 1, 0.95)
        y_end = 560 + (py - 40 - 560) * kb
        ctx.move_to(W / 2 - 18, 560)
        ctx.line_to(W / 2 + 18, 560)
        ctx.line_to(W / 2 + 18, y_end)
        ctx.line_to(W / 2 - 18, y_end)
        ctx.fill()
    # prism
    kp = ease_back(prog(t, c0[0] + 0.1, c0[0] + 0.6))
    if kp > 0:
        ctx.save()
        ctx.translate(W / 2, py + 40)
        ctx.scale(kp, kp)
        ctx.move_to(0, -150)
        ctx.line_to(150, 110)
        ctx.line_to(-150, 110)
        ctx.close_path()
        g = cairo.LinearGradient(-150, -150, 150, 110)
        g.add_color_stop_rgba(0, 0.75, 0.9, 1, 0.55)
        g.add_color_stop_rgba(1, 0.5, 0.6, 1, 0.25)
        ctx.set_source(g)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.restore()
        text(ctx, "prisma", W / 2 + 230, py + 60, 40, (1, 1, 1, 0.8), "semi", alpha=kp)
    # rainbow fan
    dur = c1[1] - c1[0]
    kr = ease_io(prog(t, c1[0] + 0.2, c1[0] + 1.6))
    top = py + 150
    bot = 1530
    x0, x1 = 120, W - 120
    bw = (x1 - x0) / 6
    for i, (name, col) in enumerate(RAINBOW):
        if kr <= 0:
            break
        yb = top + (bot - top) * kr
        sx = W / 2 - 54 + i * 18
        ex0 = x0 + i * bw
        ex1 = ex0 + bw
        f = kr
        ctx.move_to(sx, top)
        ctx.line_to(sx + 18, top)
        ctx.line_to(sx + 18 + (ex1 - sx - 18) * f, yb)
        ctx.line_to(sx + (ex0 - sx) * f, yb)
        ctx.close_path()
        ctx.set_source_rgba(*hexc(col, 0.92))
        ctx.fill()
        # labels timed to spoken colour list (~second half of cue)
        lt0 = c1[0] + dur * (0.45 + i * 0.085)
        kl = ease_back(prog(t, lt0, lt0 + 0.35))
        text(ctx, name, ex0 + bw / 2, 1590, 34, hexc(col), "black", stroke=NAVY, sw=8, scale=kl)


def sc_scatter(ctx, t, sc, gt, m):
    vgrad(ctx, [(0, hexc("#0E1150")), (1, hexc("#1F3C8F"))])
    c0, c1, c2 = sc["cues"]
    sun(ctx, 920, 170, 60, gt, alpha=0.9)
    # title
    kt = ease_back(prog(t, c0[0], c0[0] + 0.5))
    text(ctx, "Partikel udara", W / 2, 300, 78, hexc("#FFFFFF"), "black", stroke=NAVY, sw=12, scale=kt)
    # particles
    hit = (750, 1000)
    for i, (x, y, r, ph) in enumerate(PARTICLES):
        kp = ease_back(prog(t, c0[0] + 0.3 + i * 0.03, c0[0] + 0.6 + i * 0.03))
        if kp <= 0:
            continue
        px = x + math.sin(gt * 1.1 + ph) * 10
        py = y + math.cos(gt * 0.9 + ph) * 10
        if abs(px - hit[0]) < 60 and abs(py - hit[1]) < 60:
            continue
        ctx.arc(px, py, r * kp, 0, 2 * math.pi)
        ctx.set_source_rgba(0.75, 0.85, 1, 0.45)
        ctx.fill()
    # highlighted particle the blue wave hits
    kh = ease_back(prog(t, c0[0] + 0.5, c0[0] + 1.0))
    ctx.arc(*hit, 24 * kh, 0, 2 * math.pi)
    ctx.set_source_rgba(0.9, 0.95, 1, 0.95)
    ctx.fill()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    # red wave: long wavelength, goes straight
    ys, ye = 420, 1560
    if t > c1[0]:
        yf = ys + (ye - ys) * ease_io(prog(t, c1[0], c1[0] + 2.2))
        wave_path(ctx, 300, ys, yf, 170, 38, gt * 6)
        ctx.set_source_rgba(*hexc("#FF4D4D"))
        ctx.set_line_width(14)
        ctx.stroke()
        if yf > ye - 5:
            # arrow head
            ctx.move_to(300 - 30, ye - 10)
            ctx.line_to(300, ye + 30)
            ctx.line_to(300 + 30, ye - 10)
            ctx.close_path()
            ctx.fill()
        kl = ease_back(prog(t, c1[0] + 0.3, c1[0] + 0.7))
        bubble(ctx, 300, 470, 400, 120, hexc("#FF4D4D"), scale=kl)
        text(ctx, "Gelombang panjang", 300, 450, 38, (1, 1, 1, 1), "black", scale=kl)
        text(ctx, "→ lurus", 300, 494, 36, (1, 1, 1, 1), "semi", scale=kl)
    # blue wave: short wavelength, scattered
    if t > c2[0]:
        kf = ease_io(prog(t, c2[0], c2[0] + 1.4))
        yf = ys + (hit[1] - ys) * kf
        wave_path(ctx, hit[0], ys, yf, 52, 22, gt * 10)
        ctx.set_source_rgba(*hexc("#3D8BFF"))
        ctx.set_line_width(10)
        ctx.stroke()
        th = c2[0] + 1.4
        if t > th:
            ks = ease_out(prog(t, th, th + 1.2))
            pulse = 1 + 0.15 * math.sin(gt * 12)
            ctx.arc(*hit, 30 * pulse, 0, 2 * math.pi)
            ctx.set_source_rgba(0.6, 0.8, 1, 0.5)
            ctx.fill()
            for j in range(10):
                a = j * 2 * math.pi / 10 + 0.3
                L = 60 + 300 * ks
                ctx.save()
                ctx.translate(*hit)
                ctx.rotate(a)
                wave_path_h(ctx, 36, 36 + L, 40, 12, gt * 10)
                ctx.set_source_rgba(*hexc("#5AA0FF", 0.95))
                ctx.set_line_width(7)
                ctx.stroke()
                ctx.restore()
        kl = ease_back(prog(t, c2[0] + 0.3, c2[0] + 0.7))
        bubble(ctx, 760, 470, 420, 120, hexc("#3D8BFF"), scale=kl)
        text(ctx, "Gelombang pendek", 760, 450, 38, (1, 1, 1, 1), "black", scale=kl)
        text(ctx, "→ terpantul!", 760, 494, 36, (1, 1, 1, 1), "semi", scale=kl)


def wave_path_h(ctx, x0, x1, wl, amp, phase):
    ctx.move_to(x0, 0)
    x = x0
    while x < x1:
        x = min(x + 4, x1)
        ctx.line_to(x, amp * math.sin(2 * math.pi * (x - x0) / wl - phase))


def sc_sky(ctx, t, sc, gt, m):
    c0, c1, c2 = sc["cues"]
    k = ease_io(prog(t, 0, 2.0))
    top = lerpc(hexc("#0E1150"), hexc("#1E7BFF"), k)
    mid = lerpc(hexc("#1F3C8F"), hexc("#5CB6FF"), k)
    bot = lerpc(hexc("#1F3C8F"), hexc("#BFE6FF"), k)
    vgrad(ctx, [(0, top), (0.55, mid), (1, bot)])
    sun(ctx, 180, 220, 80, gt)
    # scattered blue light everywhere
    n = int(len(SKYDOTS) * (0.3 + 0.7 * k))
    for (x, y, a, sp, r) in SKYDOTS[:n]:
        px = (x + math.cos(a) * sp * gt) % (W + 40) - 20
        py = (y + math.sin(a) * sp * gt) % (H + 40) - 20
        ctx.arc(px, py, r, 0, 2 * math.pi)
        ctx.set_source_rgba(0.55, 0.78, 1, 0.55)
        ctx.fill()
    kt = ease_back(prog(t, c0[0] + 0.4, c0[0] + 0.9))
    rich_line(ctx, [("Langit jadi ", hexc("#FFFFFF")), ("BIRU!", hexc("#FFE14D"))], W / 2, 420, 100, scale=kt)
    # eyes look around during cue1
    la = gt * 1.6
    look = (math.cos(la), math.sin(la) * 0.6) if c1[0] < t < c1[1] else (0, -0.6)
    character(ctx, W / 2, 1200, 1.25, gt, m, look)
    kc = ease_back(prog(t, c2[0] + 0.1, c2[0] + 0.6))
    if kc > 0:
        bubble(ctx, W / 2, 650, 900, 220, (1, 1, 1, 0.97), scale=kc)
        text(ctx, "Ungu juga tersebar,", W / 2, 605, 50, hexc("#9B5BFF"), "black", scale=kc)
        text(ctx, "tapi mata kita lebih", W / 2, 665, 46, NAVY, "semi", scale=kc)
        text(ctx, "peka pada biru", W / 2, 720, 46, hexc("#1E6BFF"), "black", scale=kc)


def sc_sunset(ctx, t, sc, gt, m):
    c0, c1, c2 = sc["cues"]
    k = ease_io(prog(t, c0[0], c0[1] + 0.5))
    vgrad(ctx, [(0, lerpc(hexc("#1E7BFF"), hexc("#2B1055"), k)),
                (0.45, lerpc(hexc("#5CB6FF"), hexc("#C9406A"), k)),
                (0.75, lerpc(hexc("#BFE6FF"), hexc("#FF7E5F"), k)),
                (1, lerpc(hexc("#BFE6FF"), hexc("#FEB47B"), k))])
    kt = ease_back(prog(t, c0[0] + 0.2, c0[0] + 0.7))
    rich_line(ctx, [("Kenapa senja ", hexc("#FFFFFF")), ("jingga?", hexc("#FFB347"))], W / 2, 230, 88, scale=kt)
    # earth + atmosphere
    R = 1500
    ox, oy = W / 2, 1320
    ecx, ecy = ox, oy + R
    atm = 170
    ka = ease_out(prog(t, c1[0] - 0.2, c1[0] + 0.6))
    ctx.arc(ecx, ecy, R + atm, 0, 2 * math.pi)
    ctx.set_source_rgba(0.6, 0.85, 1, 0.28 * ka)
    ctx.fill()
    ctx.arc(ecx, ecy, R, 0, 2 * math.pi)
    g = cairo.LinearGradient(0, oy, 0, H)
    g.add_color_stop_rgba(0, *hexc("#3FBF60"))
    g.add_color_stop_rgba(1, *hexc("#1E7A3C"))
    ctx.set_source(g)
    ctx.fill()
    if ka > 0:
        text(ctx, "lapisan udara", 860, 1215, 34, (1, 1, 1, 0.9 * ka), "semi")
    # tiny observer
    character(ctx, ox, oy - 52, 0.32, gt, 0, (-0.8, -0.3))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    # noon ray (short path)
    kn = ease_io(prog(t, c1[0] + 0.2, c1[0] + 1.3))
    if kn > 0:
        sun(ctx, ox, 450, 55, gt, alpha=kn)
        ctx.move_to(ox, 520)
        ctx.line_to(ox, 520 + (oy - 120 - 520) * kn)
        ctx.set_source_rgba(1, 1, 0.9, 0.95)
        ctx.set_line_width(14)
        ctx.stroke()
        kl = ease_back(prog(t, c1[0] + 0.9, c1[0] + 1.3))
        bubble(ctx, 790, 760, 360, 96, (1, 1, 1, 0.95), scale=kl)
        text(ctx, "Siang: jalur pendek", 790, 760, 34, NAVY, "black", scale=kl)
    # sunset ray (long path through the air)
    ks = ease_io(prog(t, c1[0] + 1.6, c1[0] + 3.2))
    sy = oy - 110
    if ks > 0:
        sun(ctx, 70, sy, 60, gt, alpha=ks)
        xe = 130 + (ox - 70 - 130) * ks
        g = cairo.LinearGradient(130, 0, ox - 70, 0)
        g.add_color_stop_rgba(0, 1, 1, 0.92, 1)
        g.add_color_stop_rgba(0.6, 1, 0.65, 0.3, 1)
        g.add_color_stop_rgba(1, 1, 0.4, 0.2, 1)
        ctx.move_to(130, sy)
        ctx.line_to(xe, sy)
        ctx.set_source(g)
        ctx.set_line_width(16)
        ctx.stroke()
        kl = ease_back(prog(t, c1[0] + 2.4, c1[0] + 2.8))
        bubble(ctx, 300, 1010, 380, 96, hexc("#FF9A3C"), scale=kl)
        text(ctx, "Sore: jalur panjang", 300, 1010, 34, (1, 1, 1, 1), "black", scale=kl)
    # blue escaping along the long path
    if t > c2[0]:
        for j in range(14):
            st = c2[0] + j * 0.18
            if t <= st:
                continue
            kk = ((t - st) / 1.6) % 1
            bx = 150 + j * 25
            by = sy - kk * 260 * (1 if j % 2 else -0.6)
            bxx = bx + kk * 60 * math.sin(j)
            ctx.arc(bxx, by, 9 * (1 - kk * 0.5), 0, 2 * math.pi)
            ctx.set_source_rgba(0.35, 0.6, 1, 1 - kk)
            ctx.fill()
        kl = ease_back(prog(t, c2[0] + 0.5, c2[0] + 0.9))
        bubble(ctx, 300, 1100 + 30, 380, 80, hexc("#3D8BFF"), scale=kl, alpha=1)
        text(ctx, "biru habis tersebar", 300, 1130, 32, (1, 1, 1, 1), "black", scale=kl)


def sc_outro(ctx, t, sc, gt, m):
    vgrad(ctx, [(0, hexc("#5B2BFF")), (0.55, hexc("#8E4BFF")), (1, hexc("#24C6FF"))])
    rays_bg(ctx, W / 2, 700, gt)
    c0, c1, c2, c3 = sc["cues"]
    k0 = ease_back(prog(t, c0[0], c0[0] + 0.5))
    bubble(ctx, W / 2, 330, 900, 230, (1, 1, 1, 0.97), scale=k0)
    text(ctx, "Langit biru karena", W / 2, 285, 52, NAVY, "black", scale=k0)
    text(ctx, "cahaya biru paling banyak", W / 2, 345, 46, hexc("#1E6BFF"), "black", scale=k0)
    text(ctx, "dihamburkan udara", W / 2, 400, 46, NAVY, "semi", scale=k0)
    k1 = ease_back(prog(t, c1[0] + 0.9, c1[0] + 1.5))
    text(ctx, "Hamburan", W / 2, 590, 100, hexc("#FFE14D"), "black", stroke=NAVY, sw=16, scale=k1,
         rot=-0.04 + 0.02 * math.sin(gt * 3))
    text(ctx, "Rayleigh", W / 2, 710, 120, hexc("#FFFFFF"), "black", stroke=NAVY, sw=18, scale=k1,
         rot=-0.04 + 0.02 * math.sin(gt * 3))
    k2 = ease_back(prog(t, c2[0] + 0.3, c2[0] + 0.8))
    bubble(ctx, W / 2, 880, 800, 110, hexc("#FF5C8A"), scale=k2)
    text(ctx, "Tulis pertanyaanmu di komentar!", W / 2, 880, 42, (1, 1, 1, 1), "black", scale=k2)
    k3 = ease_back(prog(t, c3[0], c3[0] + 0.5))
    character(ctx, W / 2, 1290, 1.05, gt, m, (0, 0.1), wave=t > c3[0] - 0.3)
    if k3 > 0:
        for (x, y, s, ch, col, ph) in [q for q in QMARKS if q[0] < 190 or q[0] > 890]:
            text(ctx, ch, x, y + 300 + math.sin(gt * 2 + ph) * 30, s * 0.8, hexc(col, 0.6), "black",
                 scale=k3, rot=math.sin(gt + ph) * 0.3)
        text(ctx, "Sampai jumpa!", W / 2, 1060, 96, hexc("#7CF2C5"), "black", stroke=NAVY, sw=16,
             scale=k3 * (1 + 0.04 * math.sin(gt * 5)))


SCENE_FN = dict(intro=sc_intro, question=sc_question, light=sc_light, scatter=sc_scatter,
                sky=sc_sky, sunset=sc_sunset, outro=sc_outro)


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
    SCENE_FN[sc["key"]](ctx, lt, sc, gt, m)
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


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--out", default=os.path.join(here, "ep01-kenapa-langit-biru.mp4"))
    ap.add_argument("--preview", type=float, default=0, help="only render N seconds")
    ap.add_argument("--stills", action="store_true", help="dump one PNG per scene and exit")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="kbkb_")
    total, voice = build_timeline(tmp)
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
    G.update(scenes=SCENES, mouth=mouth, total=total)

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
               (SCENES[-1]["start"] + SCENES[-1]["cues"][3][0], sfx_pop())]
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


if __name__ == "__main__":
    main()
