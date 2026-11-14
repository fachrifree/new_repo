#!/usr/bin/env python3
"""
Kenapa Begini? Kenapa Begitu? — Episode 3: Kenapa Bentuk Bulan Berubah-ubah?

Vertical (1080x1920) short. Engine (character, narration, music, render) lives in ../kbkb.py;
this file holds only the episode script and its scene drawings.

Usage: python3 make_video.py [--out episode.mp4] [--preview SECONDS] [--stills]
"""
import math
import os
import random
import sys

import cairo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kbkb import *  # noqa: E402,F401,F403

# --------------------------------------------------------------------------
# Script. Each line: (subtitle text, text sent to TTS or None = same)
# --------------------------------------------------------------------------
SCENES = [
    dict(key="intro", lead=1.3, label="Eps. 3 · Bentuk Bulan", lines=[
        ("Halo, teman-teman!", None),
        ("Kembali lagi di Kenapa Begini, Kenapa Begitu!", None),
        ("Kali ini kita lihat langit malam, yuk!", None),
    ]),
    dict(key="night", lines=[
        ("Pernah nggak, kamu perhatikan bulan?", None),
        ("Kadang bulat penuh, kadang tinggal sabit tipis. Kok bentuknya bisa berubah?", None),
    ]),
    dict(key="reflect", lines=[
        ("Bulan sebenarnya tidak bisa bersinar sendiri.", None),
        ("Cahayanya berasal dari matahari, yang memantul di permukaan bulan.", None),
        ("Jadi, separuh bulan yang menghadap matahari selalu terang, separuhnya lagi gelap.", None),
    ]),
    dict(key="orbit", lines=[
        ("Bulan bergerak mengelilingi bumi, kira-kira sebulan sekali.", None),
        ("Saat bulan berpindah tempat, bagian terang yang bisa kita lihat dari bumi ikut berubah.", None),
    ]),
    dict(key="phases", lines=[
        ("Mulai dari bulan baru, lalu sabit, separuh, cembung, sampai purnama!", None),
        ("Setelah purnama, bentuknya mengecil lagi, sampai kembali jadi bulan baru.", None),
    ]),
    dict(key="myth", lines=[
        ("Banyak yang mengira bentuk bulan berubah karena tertutup bayangan bumi.", None),
        ("Itu salah! Bayangan bumi hanya menutupi bulan saat terjadi gerhana bulan.", None),
        ("Dan gerhana bulan itu jarang, tidak terjadi setiap malam.", None),
    ]),
    dict(key="outro", lines=[
        ("Jadi, bentuk bulan berubah karena kita melihat bagian terangnya dari sudut yang berbeda-beda.", None),
        ("Fakta seru: dari bulan baru ke bulan baru lagi butuh sekitar 29,5 hari. Makanya disebut satu bulan!",
         "Fakta seru: dari bulan baru ke bulan baru lagi butuh sekitar dua puluh sembilan setengah hari. "
         "Makanya disebut satu bulan!"),
        ("Punya pertanyaan lain? Tulis di kolom komentar ya.", None),
        ("Sampai jumpa!", None),
    ], tail=2.4),
]

rnd3 = random.Random(11)
STARS = [(rnd3.uniform(0, W), rnd3.uniform(0, H), rnd3.uniform(1.5, 4), rnd3.uniform(0, 6.28)) for _ in range(140)]
CRATERS = [(-0.35, -0.3, 0.18), (0.3, -0.45, 0.12), (0.15, 0.25, 0.22), (-0.4, 0.4, 0.1), (0.5, 0.1, 0.09)]
MOON_LIT = "#FFF1B8"
MOON_DARK = (0.17, 0.18, 0.3, 1)


# --------------------------------------------------------------------------
# Episode helpers
# --------------------------------------------------------------------------
def stars(ctx, gt, alpha=1.0):
    for (x, y, r, ph) in STARS:
        tw = 0.45 + 0.55 * abs(math.sin(gt * 1.3 + ph))
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 0.9, 0.8 * tw * alpha)
        ctx.fill()


def moon_phase(ctx, x, y, r, p, glow=True, dark=MOON_DARK):
    """Moon as seen from Earth. p: 0 = new, 0.25 = first quarter, 0.5 = full, 0.75 = last quarter."""
    q = p % 1.0
    k = (1 - math.cos(2 * math.pi * q)) / 2  # illuminated fraction
    ctx.save()
    ctx.translate(x, y)
    if glow and k > 0.05:
        g = cairo.RadialGradient(0, 0, r * 0.9, 0, 0, r * 1.8)
        g.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.35 * k)
        g.add_color_stop_rgba(1, 1, 0.95, 0.7, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r * 1.8, 0, 2 * math.pi)
        ctx.fill()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgba(*dark)
    ctx.fill()
    if q > 0.5:
        ctx.scale(-1, 1)
        q = 1 - q
    e = math.cos(2 * math.pi * q)  # +1 new ... -1 full
    if e < 0.999:
        ctx.new_path()
        ctx.arc(0, 0, r, -math.pi / 2, math.pi / 2)
        ctx.save()
        sx = e if abs(e) > 0.002 else 0.002
        ctx.scale(sx, 1)
        ctx.arc_negative(0, 0, r, math.pi / 2, -math.pi / 2)
        ctx.restore()
        ctx.close_path()
        ctx.set_source_rgba(*hexc(MOON_LIT))
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        for (cx, cy, cr) in CRATERS:
            ctx.arc(cx * r, cy * r, cr * r, 0, 2 * math.pi)
            ctx.set_source_rgba(0.85, 0.75, 0.45, 0.35)
            ctx.fill()
        ctx.restore()
    ctx.new_path()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.25)
    ctx.set_line_width(3)
    ctx.stroke()
    ctx.restore()


def moon_space(ctx, x, y, r, lit_angle=math.pi, alpha=1.0, red=0.0):
    """Moon seen from space: the half facing lit_angle (direction to the sun) is bright."""
    ctx.save()
    ctx.translate(x, y)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgba(*MOON_DARK[:3], alpha)
    ctx.fill()
    if alpha > 0:
        ctx.arc(0, 0, r, lit_angle - math.pi / 2, lit_angle + math.pi / 2)
        ctx.close_path()
        col = lerpc(hexc(MOON_LIT), hexc("#C0392B"), red)
        ctx.set_source_rgba(*col[:3], alpha)
        ctx.fill()
    ctx.restore()


def earth(ctx, x, y, r, t):
    ctx.save()
    ctx.translate(x, y)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgba(*hexc("#2E8FE0"))
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    ctx.set_source_rgba(*hexc("#4DD97A"))
    for (cx, cy, cr) in [(-0.3, -0.25, 0.35), (0.35, 0.2, 0.3), (-0.1, 0.5, 0.2)]:
        ox = ((cx + t * 0.05 + 1) % 2 - 1) * r
        ctx.arc(ox, cy * r, cr * r, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()
    ctx.set_source_rgba(1, 1, 1, 0.8)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.restore()


def phase_name(p):
    q = p % 1.0
    if q < 0.04 or q > 0.96:
        return "Bulan baru"
    if 0.46 <= q <= 0.54:
        return "Purnama"
    if 0.21 <= q <= 0.29 or 0.71 <= q <= 0.79:
        return "Separuh"
    if 0.29 < q < 0.71:
        return "Cembung"
    return "Sabit"


def sun_rays_left(ctx, gt, y0, y1, x1, alpha=1.0):
    """Animated sunlight arrows coming from the left edge."""
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    n = 6
    for i in range(n):
        y = y0 + (y1 - y0) * (i + 0.5) / n
        off = (gt * 160 + i * 47) % 120
        ctx.set_dash([60, 60], -off)
        ctx.move_to(20, y)
        ctx.line_to(x1, y)
        ctx.set_source_rgba(1, 0.86, 0.3, 0.65 * alpha)
        ctx.set_line_width(7)
        ctx.stroke()
    ctx.set_dash([])


# --------------------------------------------------------------------------
# Scenes  (ctx, local time, scene dict, global time, mouth)
# --------------------------------------------------------------------------
def night_bg(ctx):
    vgrad(ctx, [(0, hexc("#0A0B2E")), (0.6, hexc("#1B1F5E")), (1, hexc("#33307A"))])


def sc_night(ctx, t, sc, gt, m):
    c0, c1 = sc["cues"]
    night_bg(ctx)
    stars(ctx, gt)
    # moon cycling through its phases
    p = 0.5 + max(0.0, t - c0[0] - 0.5) * 0.16
    moon_phase(ctx, 540, 470, 160, p)
    kn = prog(t, c1[0], c1[0] + 0.4)
    bubble(ctx, 540, 700, 300, 76, (1, 1, 1, 0.9), scale=kn)
    text(ctx, phase_name(p), 540, 700, 40, NAVY, "black", scale=kn)
    k = ease_back(prog(t, c1[1] - 2.0, c1[1] - 1.5))
    rich_line(ctx, [("Kenapa bentuk bulan", hexc("#FFFFFF"))], W / 2, 880, 80, scale=k)
    rich_line(ctx, [("BERUBAH?", hexc("#FFE14D"))], W / 2, 990, 110, scale=k)
    # houses
    ctx.set_source_rgba(*hexc("#141433"))
    for (hx, hw, hh) in [(0, 220, 230), (200, 180, 320), (620, 240, 260), (850, 230, 360)]:
        ctx.rectangle(hx, 1560 - hh, hw, hh)
        ctx.fill()
        ctx.move_to(hx - 15, 1560 - hh)
        ctx.line_to(hx + hw / 2, 1560 - hh - 90)
        ctx.line_to(hx + hw + 15, 1560 - hh)
        ctx.close_path()
        ctx.fill()
    ctx.set_source_rgba(1, 0.85, 0.4, 0.85)
    for (wx, wy) in [(60, 1420), (260, 1330), (700, 1400), (930, 1300), (930, 1420)]:
        ctx.rectangle(wx, wy, 50, 50)
        ctx.fill()
    ctx.rectangle(0, 1550, W, H - 1550)
    ctx.set_source_rgba(*hexc("#101028"))
    ctx.fill()
    character(ctx, 470, 1420, 0.9, gt, m, (0.3, -1), mood="curious")


def sc_reflect(ctx, t, sc, gt, m):
    c0, c1, c2 = sc["cues"]
    vgrad(ctx, [(0, hexc("#05061A")), (1, hexc("#141A45"))])
    stars(ctx, gt, 0.6)
    mx, my, mr = 650, 700, 190
    lit = ease_io(prog(t, c1[0] + 0.6, c1[0] + 1.6))
    if t > c1[0]:
        sun(ctx, -60, 700, 190, gt, alpha=prog(t, c1[0], c1[0] + 0.5))
        sun_rays_left(ctx, gt, 540, 860, mx - mr - 10, prog(t, c1[0] + 0.2, c1[0] + 0.8))
    moon_space(ctx, mx, my, mr, math.pi, alpha=1.0)
    if lit < 1:
        # dark overlay before the light arrives
        ctx.arc(mx, my, mr + 1, 0, 2 * math.pi)
        ctx.set_source_rgba(*MOON_DARK[:3], 1 - lit)
        ctx.fill()
    kt = ease_back(prog(t, c0[0], c0[0] + 0.5))
    text(ctx, "Bulan", W / 2, 200, 100, hexc("#FFFFFF"), "black", stroke=NAVY, sw=14, scale=kt)
    kn = ease_back(prog(t, c0[0] + 0.8, c0[0] + 1.2)) * (1 - prog(t, c1[0], c1[0] + 0.3))
    bubble(ctx, W / 2, 360, 620, 96, hexc("#FF5C8A"), scale=kn)
    text(ctx, "tidak bersinar sendiri", W / 2, 360, 44, (1, 1, 1, 1), "black", scale=kn)
    km = ease_back(prog(t, c1[0] + 1.4, c1[0] + 1.8))
    bubble(ctx, W / 2, 360, 640, 96, hexc("#FFC93C"), scale=km)
    text(ctx, "memantulkan cahaya matahari", W / 2, 360, 40, NAVY, "black", scale=km)
    # reflected light reaching Earth / Tanya below
    kr = ease_io(prog(t, c1[0] + 2.0, c1[0] + 3.0))
    if kr > 0:
        ctx.arc(540, 2350, 900, 0, 2 * math.pi)
        g = cairo.LinearGradient(0, 1450, 0, H)
        g.add_color_stop_rgba(0, *hexc("#2E8FE0"))
        g.add_color_stop_rgba(1, *hexc("#1B5FA8"))
        ctx.set_source(g)
        ctx.fill()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for dx in (-60, 0, 60):
            x0, y0 = mx - mr * 0.6 + dx * 0.5, my + mr * 0.8
            x1, y1 = 420 + dx, 1360
            ctx.move_to(x0, y0)
            ctx.line_to(x0 + (x1 - x0) * kr, y0 + (y1 - y0) * kr)
            ctx.set_source_rgba(1, 0.95, 0.7, 0.75)
            ctx.set_line_width(6)
            ctx.stroke()
        character(ctx, 400, 1400, 0.55, gt, 0, (0.6, -1))
    # labels: lit half vs dark half
    k1 = ease_back(prog(t, c2[0] + 0.8, c2[0] + 1.2))
    k2 = ease_back(prog(t, c2[0] + 2.6, c2[0] + 3.0))
    bubble(ctx, 300, 1000, 330, 90, hexc("#FFE14D"), scale=k1)
    text(ctx, "selalu terang", 300, 1000, 40, NAVY, "black", scale=k1)
    bubble(ctx, 900, 1000, 220, 90, hexc("#3B3F6E"), scale=k2)
    text(ctx, "gelap", 900, 1000, 42, (1, 1, 1, 1), "black", scale=k2)


def sc_orbit(ctx, t, sc, gt, m):
    c0, c1 = sc["cues"]
    vgrad(ctx, [(0, hexc("#05061A")), (1, hexc("#141A45"))])
    stars(ctx, gt, 0.5)
    ex, ey, R = 540, 1080, 330
    sun_rays_left(ctx, gt, 760, 1400, W - 20, 0.8)
    text(ctx, "cahaya matahari →", 220, 1500, 34, hexc("#FFE14D"), "black")
    # orbit ring
    ctx.arc(ex, ey, R, 0, 2 * math.pi)
    ctx.set_dash([14, 14])
    ctx.set_source_rgba(1, 1, 1, 0.35)
    ctx.set_line_width(3)
    ctx.stroke()
    ctx.set_dash([])
    earth(ctx, ex, ey, 80, gt)
    text(ctx, "Bumi", ex, ey + 125, 36, (1, 1, 1, 0.9), "black")
    # moon going around (one full orbit across the scene)
    ko = prog(t, c0[0] + 0.6, c1[1])
    a = math.pi + 2 * math.pi * ko
    p = (a - math.pi) / (2 * math.pi)
    mx, my = ex + R * math.cos(a), ey - R * math.sin(a)
    moon_space(ctx, mx, my, 55, math.pi)
    # what we see from Earth
    kv = ease_back(prog(t, c0[0] + 0.2, c0[0] + 0.7))
    bubble(ctx, W / 2, 470, 720, 470, (1, 1, 1, 0.12), scale=kv)
    if kv > 0.01:
        ctx.save()
        ctx.translate(W / 2, 470)
        ctx.scale(kv, kv)
        text(ctx, "Dari bumi terlihat:", 0, -170, 44, (1, 1, 1, 1), "black")
        moon_phase(ctx, 0, 10, 120, p)
        text(ctx, phase_name(p), 0, 185, 50, hexc("#FFE14D"), "black", stroke=NAVY, sw=8)
        ctx.restore()
    kt = ease_back(prog(t, c0[0], c0[0] + 0.4))
    text(ctx, "1 putaran ≈ 1 bulan", W / 2, 170, 64, hexc("#FFFFFF"), "black", stroke=NAVY, sw=12, scale=kt)


PHASE_ROW1 = [(0.0, "Baru"), (0.125, "Sabit"), (0.25, "Separuh"), (0.375, "Cembung"), (0.5, "Purnama")]
PHASE_ROW2 = [(0.625, "Cembung"), (0.75, "Separuh"), (0.875, "Sabit"), (1.0, "Baru")]


def sc_phases(ctx, t, sc, gt, m):
    c0, c1 = sc["cues"]
    night_bg(ctx)
    stars(ctx, gt, 0.6)
    kt = ease_back(prog(t, c0[0], c0[0] + 0.4))
    rich_line(ctx, [("Bulan ", hexc("#FFFFFF")), ("membesar", hexc("#FFE14D"))], W / 2, 330, 84, scale=kt)
    d0 = c0[1] - c0[0]
    for i, (p, name) in enumerate(PHASE_ROW1):
        st = c0[0] + d0 * (0.08 + i * 0.19)
        k = ease_back(prog(t, st, st + 0.4))
        x = 140 + i * 200
        if k > 0.01:
            ctx.save()
            ctx.translate(x, 620)
            ctx.scale(k, k)
            moon_phase(ctx, 0, 0, 78, p)
            ctx.restore()
            text(ctx, name, x, 750, 34, (1, 1, 1, 1), "black", scale=k)
    # arrow
    ka = ease_out(prog(t, c0[0] + 0.5, c0[1]))
    ctx.move_to(100, 820)
    ctx.line_to(100 + 880 * ka, 820)
    ctx.set_source_rgba(1, 0.88, 0.3, 0.9)
    ctx.set_line_width(8)
    ctx.stroke()
    kt2 = ease_back(prog(t, c1[0] + 0.6, c1[0] + 1.0))
    rich_line(ctx, [("lalu ", hexc("#FFFFFF")), ("mengecil", hexc("#7CF2C5"))], W / 2, 1020, 84, scale=kt2)
    d1 = c1[1] - c1[0]
    for i, (p, name) in enumerate(PHASE_ROW2):
        st = c1[0] + d1 * (0.2 + i * 0.17)
        k = ease_back(prog(t, st, st + 0.4))
        x = 240 + i * 200
        if k > 0.01:
            ctx.save()
            ctx.translate(x, 1290)
            ctx.scale(k, k)
            moon_phase(ctx, 0, 0, 78, p)
            ctx.restore()
            text(ctx, name, x, 1420, 34, (1, 1, 1, 1), "black", scale=k)
    kb = ease_out(prog(t, c1[0] + d1 * 0.2, c1[1]))
    if kb > 0:
        ctx.move_to(980, 1490)
        ctx.line_to(980 - 880 * kb, 1490)
        ctx.set_source_rgba(0.5, 0.95, 0.8, 0.9)
        ctx.set_line_width(8)
        ctx.stroke()


def sc_myth(ctx, t, sc, gt, m):
    c0, c1, c2 = sc["cues"]
    vgrad(ctx, [(0, hexc("#05061A")), (1, hexc("#1F1240"))])
    stars(ctx, gt, 0.5)
    kt = ease_back(prog(t, c0[0], c0[0] + 0.5))
    rich_line(ctx, [("Karena ", hexc("#FFFFFF")), ("bayangan bumi?", hexc("#FF9A3C"))], W / 2, 260, 76, scale=kt)
    # diagram: sun — earth — shadow — moon
    ey = 820
    sun(ctx, 60, ey, 120, gt)
    ctx.move_to(540, ey - 95)
    ctx.line_to(W + 40, ey - 40)
    ctx.line_to(W + 40, ey + 40)
    ctx.line_to(540, ey + 95)
    ctx.close_path()
    ctx.set_source_rgba(0, 0, 0, 0.55)
    ctx.fill()
    earth(ctx, 540, ey, 95, gt)
    eclipse = prog(t, c1[0] + 1.2, c1[0] + 2.6)
    mx = 900
    my = ey - 330 * (1 - ease_io(eclipse))
    moon_space(ctx, mx, my, 55, math.pi, red=0.8 * eclipse)
    if eclipse > 0.6:
        ctx.arc(mx, my, 55, 0, 2 * math.pi)
        ctx.set_source_rgba(0, 0, 0, 0.25)
        ctx.fill()
    text(ctx, "bayangan bumi", 820, ey + 140, 34, (1, 1, 1, 0.85), "black", alpha=kt)
    # wrong! stamp
    ks = ease_back(prog(t, c1[0], c1[0] + 0.4))
    if ks > 0:
        fade = 1 - prog(t, c1[0] + 2.0, c1[0] + 2.4)
        ctx.save()
        ctx.translate(W / 2, 1180)
        ctx.rotate(-0.12)
        ctx.scale(ks, ks)
        rrect(ctx, -230, -75, 460, 150, 30)
        ctx.set_source_rgba(*hexc("#FF4D4D", fade))
        ctx.fill()
        text(ctx, "SALAH!", 0, 0, 96, (1, 1, 1, fade), "black")
        ctx.restore()
    kg = ease_back(prog(t, c1[0] + 2.4, c1[0] + 2.8))
    bubble(ctx, W / 2, 1180, 620, 110, hexc("#C0392B"), scale=kg)
    text(ctx, "= Gerhana bulan", W / 2, 1180, 56, (1, 1, 1, 1), "black", scale=kg)
    kr = ease_back(prog(t, c2[0] + 0.5, c2[0] + 0.9))
    bubble(ctx, W / 2, 1380, 760, 96, (1, 1, 1, 0.95), scale=kr)
    text(ctx, "jarang, tidak setiap malam", W / 2, 1380, 42, NAVY, "black", scale=kr)


def calendar(ctx, x, y, s):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    rrect(ctx, -170, -150, 340, 300, 36)
    ctx.set_source_rgba(1, 1, 1, 1)
    ctx.fill()
    ctx.save()
    rrect(ctx, -170, -150, 340, 300, 36)
    ctx.clip()
    ctx.rectangle(-170, -150, 340, 80)
    ctx.set_source_rgba(*hexc("#FF4D4D"))
    ctx.fill()
    ctx.restore()
    text(ctx, "1 BULAN", 0, -110, 40, (1, 1, 1, 1), "black")
    text(ctx, "29,5", 0, 10, 110, NAVY, "black")
    text(ctx, "hari", 0, 100, 44, hexc("#1E6BFF"), "black")
    ctx.restore()


def sc_outro(ctx, t, sc, gt, m):
    vgrad(ctx, [(0, hexc("#5B2BFF")), (0.55, hexc("#8E4BFF")), (1, hexc("#24C6FF"))])
    rays_bg(ctx, W / 2, 700, gt)
    c0, c1, c2, c3 = sc["cues"]
    k0 = ease_back(prog(t, c0[0], c0[0] + 0.5))
    bubble(ctx, W / 2, 320, 920, 240, (1, 1, 1, 0.97), scale=k0)
    text(ctx, "Bentuk bulan berubah karena", W / 2, 270, 46, NAVY, "black", scale=k0)
    text(ctx, "bagian terangnya kita lihat", W / 2, 330, 44, hexc("#1E6BFF"), "black", scale=k0)
    text(ctx, "dari sudut yang berbeda", W / 2, 388, 44, NAVY, "semi", scale=k0)
    kf = ease_back(prog(t, c1[0] + 0.4, c1[0] + 0.9))
    fade = 1 - prog(t, c3[0] - 0.3, c3[0] + 0.2)
    if kf > 0.01 and fade > 0:
        ctx.push_group()
        calendar(ctx, 330, 760, kf)
        for i, p in enumerate([0.0, 0.25, 0.5, 0.75]):
            kk = ease_back(prog(t, c1[0] + 1.0 + i * 0.25, c1[0] + 1.4 + i * 0.25))
            if kk > 0.01:
                ctx.save()
                ctx.translate(690 + (i % 2) * 170, 680 + (i // 2) * 170)
                ctx.scale(kk, kk)
                moon_phase(ctx, 0, 0, 62, p)
                ctx.restore()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(fade)
    k2 = ease_back(prog(t, c2[0] + 0.3, c2[0] + 0.8))
    bubble(ctx, W / 2, 1150, 800, 110, hexc("#FF5C8A"), scale=k2)
    text(ctx, "Tulis pertanyaanmu di komentar!", W / 2, 1150, 42, (1, 1, 1, 1), "black", scale=k2)
    k3 = ease_back(prog(t, c3[0], c3[0] + 0.5))
    if k3 > 0:
        for (x, y, s, ch, col, ph) in [q for q in QMARKS if q[0] < 190 or q[0] > 890]:
            text(ctx, ch, x, y + math.sin(gt * 2 + ph) * 30, s * 0.8, hexc(col, 0.6), "black",
                 scale=k3, rot=math.sin(gt + ph) * 0.3)
        text(ctx, "Sampai jumpa!", W / 2, 760, 110, hexc("#7CF2C5"), "black", stroke=NAVY, sw=16,
             scale=k3 * (1 + 0.04 * math.sin(gt * 5)))
    character(ctx, W / 2, 1420, 0.85, gt, m, (0, 0.1), wave=t > c3[0] - 0.3)


SCENE_FN = dict(intro=sc_intro, night=sc_night, reflect=sc_reflect, orbit=sc_orbit, phases=sc_phases,
                myth=sc_myth, outro=sc_outro)


if __name__ == "__main__":
    run(SCENES, SCENE_FN, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ep03-kenapa-bentuk-bulan.mp4"))
