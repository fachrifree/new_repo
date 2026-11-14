#!/usr/bin/env python3
"""
Kenapa Begini? Kenapa Begitu? — Episode 2: Kenapa Air Laut Asin?

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
    dict(key="intro", lead=1.3, label="Eps. 2 · Laut Asin", lines=[
        ("Halo, teman-teman!", None),
        ("Kembali lagi di Kenapa Begini, Kenapa Begitu!", None),
        ("Kali ini kita akan menyelam ke laut!", None),
    ]),
    dict(key="beach", lines=[
        ("Pernah nggak, kamu berenang di pantai, lalu air lautnya terasa asin?", None),
        ("Padahal air hujan dan air sungai tidak asin. Kok bisa?", None),
    ]),
    dict(key="rain", lines=[
        ("Ceritanya dimulai dari hujan.", None),
        ("Air hujan sedikit bersifat asam, jadi pelan-pelan mengikis batuan di daratan.", None),
        ("Dari batuan itu, lepaslah mineral dan garam yang sangat kecil.", None),
    ]),
    dict(key="river", lines=[
        ("Garam-garam ini terbawa aliran sungai, terus menuju ke laut.", None),
        ("Ada juga garam yang keluar dari gunung berapi di dasar laut.", None),
    ]),
    dict(key="evap", lines=[
        ("Di laut, matahari memanaskan air sehingga menguap ke udara.", None),
        ("Tapi garamnya tidak ikut menguap. Garamnya tertinggal di laut!", None),
        ("Uap air jadi awan, lalu turun lagi sebagai hujan yang tawar.", None),
    ]),
    dict(key="years", lines=[
        ("Proses ini terjadi terus-menerus, selama jutaan tahun.", None),
        ("Garam pun makin menumpuk, sampai air laut jadi asin seperti sekarang.", None),
        ("Dalam satu liter air laut, ada sekitar 35 gram garam. Kira-kira dua sendok makan!",
         "Dalam satu liter air laut, ada sekitar tiga puluh lima gram garam. Kira-kira dua sendok makan!"),
    ]),
    dict(key="outro", lines=[
        ("Jadi, laut asin karena garam dari daratan terbawa ke laut, dan tertinggal saat airnya menguap.", None),
        ("Fakta seru: kalau semua garam laut disebar di daratan, tebalnya lebih dari 150 meter. Lebih tinggi dari Monas!",
         "Fakta seru: kalau semua garam laut disebar di daratan, tebalnya lebih dari seratus lima puluh meter. Lebih tinggi dari Monas!"),
        ("Punya pertanyaan lain? Tulis di kolom komentar ya.", None),
        ("Sampai jumpa!", None),
    ], tail=2.4),
]

rnd2 = random.Random(7)
RAIN = [(rnd2.uniform(40, W - 40), rnd2.uniform(0, 1)) for _ in range(70)]
SALT = [(rnd2.uniform(60, W - 60), rnd2.uniform(0, 1), rnd2.uniform(0, 6.28), rnd2.uniform(9, 15))
        for _ in range(90)]
VAPOR = [(rnd2.uniform(80, W - 80), rnd2.uniform(0, 1)) for _ in range(40)]
MINERAL_COLS = ["#FFFFFF", "#FFD1DC", "#FFF3B0", "#CFF5FF"]


# --------------------------------------------------------------------------
# Episode helpers
# --------------------------------------------------------------------------
def sea(ctx, top, t, c_top="#2EA8E6", c_bot="#0B4F8A", amp=14, alpha=1.0):
    ctx.move_to(0, H)
    ctx.line_to(0, top)
    x = 0
    while x <= W:
        ctx.line_to(x, top + amp * math.sin(x / 70 + t * 2.2) + amp * 0.5 * math.sin(x / 31 - t * 3))
        x += 12
    ctx.line_to(W, H)
    ctx.close_path()
    g = cairo.LinearGradient(0, top, 0, H)
    g.add_color_stop_rgba(0, *hexc(c_top, alpha))
    g.add_color_stop_rgba(1, *hexc(c_bot, alpha))
    ctx.set_source(g)
    ctx.fill()
    # foam line
    x = 0
    ctx.move_to(0, top)
    while x <= W:
        ctx.line_to(x, top + amp * math.sin(x / 70 + t * 2.2) + amp * 0.5 * math.sin(x / 31 - t * 3))
        x += 12
    ctx.set_source_rgba(1, 1, 1, 0.7 * alpha)
    ctx.set_line_width(6)
    ctx.stroke()


def salt(ctx, x, y, s, rot=0.0, alpha=1.0, col="#FFFFFF"):
    if s <= 0 or alpha <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    rrect(ctx, -s, -s, 2 * s, 2 * s, s * 0.3)
    ctx.set_source_rgba(*hexc(col, alpha))
    ctx.fill_preserve()
    ctx.set_source_rgba(0.45, 0.65, 0.85, alpha)
    ctx.set_line_width(2.5)
    ctx.stroke()
    ctx.restore()


def drop(ctx, x, y, s, col=(0.6, 0.85, 1, 0.9)):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, -18)
    ctx.curve_to(8, -4, 12, 4, 12, 9)
    ctx.arc(0, 9, 12, 0, math.pi)
    ctx.curve_to(-12, 4, -8, -4, 0, -18)
    ctx.set_source_rgba(*col)
    ctx.fill()
    ctx.restore()


MOUNT = [(0, 1560), (160, 1260), (430, 820), (600, 1080), (760, 1180), (920, 960), (W, 1150), (W, 1560)]


def mount_y(x):
    pts = MOUNT[:-1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0 + 1e-9)
    return 1560


def mountains(ctx):
    ctx.move_to(*MOUNT[0])
    for p in MOUNT[1:]:
        ctx.line_to(*p)
    ctx.line_to(W, H)
    ctx.line_to(0, H)
    ctx.close_path()
    g = cairo.LinearGradient(0, 820, 0, 1560)
    g.add_color_stop_rgba(0, *hexc("#8A8FA8"))
    g.add_color_stop_rgba(1, *hexc("#545A78"))
    ctx.set_source(g)
    ctx.fill()
    # rock facets
    ctx.set_source_rgba(1, 1, 1, 0.12)
    for poly in [[(430, 820), (520, 950), (470, 1150), (380, 1000)],
                 [(920, 960), (980, 1040), (930, 1200), (860, 1060)],
                 [(160, 1260), (240, 1320), (180, 1450)]]:
        ctx.move_to(*poly[0])
        for p in poly[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.fill()
    # ground
    ctx.rectangle(0, 1540, W, H - 1540)
    ctx.set_source_rgba(*hexc("#6B4F3A"))
    ctx.fill()


def bez(p0, p1, p2, p3, s):
    u = 1 - s
    return (u ** 3 * p0[0] + 3 * u * u * s * p1[0] + 3 * u * s * s * p2[0] + s ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * s * p1[1] + 3 * u * s * s * p2[1] + s ** 3 * p3[1])


# --------------------------------------------------------------------------
# Scenes  (ctx, local time, scene dict, global time, mouth)
# --------------------------------------------------------------------------
def sc_beach(ctx, t, sc, gt, m):
    c0, c1 = sc["cues"]
    vgrad(ctx, [(0, hexc("#3FA9FF")), (0.5, hexc("#9AD8FF")), (1, hexc("#E6F6FF"))])
    sun(ctx, 870, 280, 85, gt)
    for i, (cx, cy, s) in enumerate([(180, 300, 1.1), (650, 560, 0.8)]):
        cloud(ctx, (cx + gt * 22 * (1 + i * 0.3)) % (W + 400) - 200, cy, s)
    sea(ctx, 960, gt)
    # sand
    ctx.move_to(0, 1330)
    ctx.curve_to(300, 1250, 700, 1300, W, 1240)
    ctx.line_to(W, H)
    ctx.line_to(0, H)
    ctx.close_path()
    ctx.set_source_rgba(*hexc("#F7D9A0"))
    ctx.fill()
    k = ease_back(prog(t, c0[0] + 0.6, c0[0] + 1.1))
    rich_line(ctx, [("Kenapa air laut", hexc("#FFFFFF"))], W / 2, 460, 92, scale=k)
    rich_line(ctx, [("terasa ", hexc("#FFFFFF")), ("ASIN?", hexc("#FFE14D"))], W / 2, 580, 110, scale=k)
    yuck = c0[1] - 1.2 < t < c1[0] + 0.6
    ka = ease_back(prog(t, c0[1] - 1.2, c0[1] - 0.8))
    bubble(ctx, 790, 1030, 260, 120, (1, 1, 1, 1), scale=ka, tail=(-60, 90))
    text(ctx, "Asin!", 790, 1030, 64, hexc("#FF4D6D"), "black", scale=ka * (1 + 0.05 * math.sin(gt * 9)))
    # rain & river are fresh
    kb = ease_back(prog(t, c1[0] + 0.3, c1[0] + 0.7))
    kc = ease_back(prog(t, c1[0] + 1.0, c1[0] + 1.4))
    bubble(ctx, 270, 760, 400, 100, hexc("#4DD97A"), scale=kb)
    text(ctx, "Air hujan: tawar", 270, 760, 40, (1, 1, 1, 1), "black", stroke=NAVY, sw=7, scale=kb)
    bubble(ctx, 800, 800, 420, 100, hexc("#4DD97A"), scale=kc)
    text(ctx, "Air sungai: tawar", 800, 800, 40, (1, 1, 1, 1), "black", stroke=NAVY, sw=7, scale=kc)
    character(ctx, 440, 1360, 1.0, gt, m, (0.5, -0.4), mood="yuck" if yuck else "curious")


def sc_rain(ctx, t, sc, gt, m):
    c0, c1, c2 = sc["cues"]
    vgrad(ctx, [(0, hexc("#4A5578")), (1, hexc("#A9B6D3"))])
    mountains(ctx)
    # rain
    kr = prog(t, c0[0] + 0.3, c0[0] + 1.0)
    if kr > 0:
        for x, ph in RAIN[: int(len(RAIN) * kr)]:
            ys = mount_y(x)
            span = ys - 420
            y = 420 + ((gt * 900 + ph * span) % (span + 60))
            if y < ys:
                drop(ctx, x, y, 0.8)
            else:
                k = (y - ys) / 60
                ctx.arc(x, ys, 8 + 22 * k, math.pi * 1.1, math.pi * 1.9)
                ctx.set_source_rgba(0.75, 0.9, 1, 0.8 * (1 - k))
                ctx.set_line_width(4)
                ctx.stroke()
    for i, (cx, s) in enumerate([(260, 2.0), (620, 2.3), (930, 1.8)]):
        cloud(ctx, cx + math.sin(gt * 0.5 + i) * 15, 360 + i * 20, s, 0.97, (0.78, 0.8, 0.88))
    kt = ease_back(prog(t, c0[0], c0[0] + 0.5))
    text(ctx, "Hujan", W / 2, 180, 90, hexc("#FFFFFF"), "black", stroke=NAVY, sw=14, scale=kt)
    ka = ease_back(prog(t, c1[0] + 0.4, c1[0] + 0.9))
    bubble(ctx, 300, 640, 420, 100, hexc("#FF9A3C"), scale=ka)
    text(ctx, "sedikit asam", 300, 640, 46, (1, 1, 1, 1), "black", stroke=NAVY, sw=7, scale=ka)
    kb = ease_back(prog(t, c1[0] + 1.6, c1[0] + 2.0))
    bubble(ctx, 780, 700, 440, 100, hexc("#8E4BFF"), scale=kb)
    text(ctx, "mengikis batuan", 780, 700, 44, (1, 1, 1, 1), "black", stroke=NAVY, sw=7, scale=kb)
    # crack lines on rocks during erosion
    if t > c1[0] + 1.6:
        kc = ease_out(prog(t, c1[0] + 1.6, c1[0] + 3.0))
        ctx.set_source_rgba(0.2, 0.2, 0.3, 0.6)
        ctx.set_line_width(4)
        for (x0, y0, dx, dy) in [(430, 860, 30, 120), (920, 1000, -40, 110), (250, 1150, 60, 90)]:
            ctx.move_to(x0, y0)
            ctx.line_to(x0 + dx * 0.5 * kc, y0 + dy * 0.5 * kc)
            ctx.line_to(x0 + dx * kc, y0 + dy * kc)
            ctx.stroke()
    # minerals breaking off and rolling down
    if t > c2[0]:
        for j in range(26):
            st = c2[0] + 0.1 + j * 0.09
            if t < st:
                continue
            k = ease_out(prog(t, st, st + 2.0))
            x0 = 200 + (j * 137) % 760
            y0 = mount_y(x0)
            x = x0 + (j % 3 - 1) * 60 * k
            y = y0 - 10 + k * (1520 - y0)
            salt(ctx, x, min(y, 1520), 11, gt * 2 + j, col=MINERAL_COLS[j % 4])
        kl = ease_back(prog(t, c2[0] + 1.0, c2[0] + 1.4))
        bubble(ctx, W / 2, 1420, 520, 100, (1, 1, 1, 0.97), scale=kl)
        text(ctx, "mineral & garam", W / 2, 1420, 50, NAVY, "black", scale=kl)


RIVER = [((210, 560), (120, 860), (720, 820), (520, 1080)),
         ((520, 1080), (380, 1250), (700, 1250), (620, 1380))]


def river_pt(s):
    if s < 0.5:
        return bez(*RIVER[0], s * 2)
    return bez(*RIVER[1], (s - 0.5) * 2)


def sc_river(ctx, t, sc, gt, m):
    c0, c1 = sc["cues"]
    vgrad(ctx, [(0, hexc("#7CC8FF")), (1, hexc("#D9F1FF"))])
    # land
    ctx.move_to(0, 520)
    ctx.curve_to(300, 460, 700, 520, W, 480)
    ctx.line_to(W, 1350)
    ctx.line_to(0, 1350)
    ctx.close_path()
    ctx.set_source_rgba(*hexc("#7BD389"))
    ctx.fill()
    # little mountain at source
    ctx.move_to(60, 600)
    ctx.line_to(210, 330)
    ctx.line_to(360, 600)
    ctx.close_path()
    ctx.set_source_rgba(*hexc("#7A809C"))
    ctx.fill()
    ctx.move_to(160, 420)
    ctx.line_to(210, 330)
    ctx.line_to(260, 420)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 1)
    ctx.fill()
    # river
    kr = ease_io(prog(t, 0.0, c0[0] + 1.0))
    if kr > 0:
        n = 80
        ctx.move_to(*river_pt(0))
        for i in range(1, int(n * kr) + 1):
            ctx.line_to(*river_pt(i / n))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(*hexc("#2E8FE0"))
        ctx.set_line_width(70)
        ctx.stroke_preserve()
        ctx.set_source_rgba(*hexc("#6CC3FF"))
        ctx.set_line_width(40)
        ctx.stroke()
    sea(ctx, 1330, gt, amp=10)
    # salts travelling down the river
    if t > c0[0] + 0.6:
        for j in range(18):
            s = ((gt - c0[0]) * 0.16 + j / 18) % 1.0
            x, y = river_pt(s)
            salt(ctx, x + math.sin(j * 2.1) * 12, y + math.cos(j * 1.3) * 8, 10, gt * 2 + j)
    kt = ease_back(prog(t, c0[0], c0[0] + 0.5))
    rich_line(ctx, [("Terbawa ", hexc("#FFFFFF")), ("sungai", hexc("#FFE14D"))], W / 2, 210, 92, scale=kt)
    kl = ease_back(prog(t, c0[0] + 1.6, c0[0] + 2.0))
    bubble(ctx, 830, 760, 300, 90, hexc("#2E8FE0"), scale=kl)
    text(ctx, "ke laut", 830, 760, 46, (1, 1, 1, 1), "black", scale=kl)
    # underwater volcano / vent
    kv = ease_back(prog(t, c1[0] + 0.1, c1[0] + 0.6))
    if kv > 0:
        ctx.save()
        ctx.translate(860, 1620)
        ctx.scale(kv, kv)
        ctx.move_to(-130, 60)
        ctx.line_to(-35, -70)
        ctx.line_to(35, -70)
        ctx.line_to(130, 60)
        ctx.close_path()
        ctx.set_source_rgba(*hexc("#3A2F4A"))
        ctx.fill()
        ctx.move_to(-30, -66)
        ctx.line_to(30, -66)
        ctx.line_to(18, -40)
        ctx.line_to(-18, -40)
        ctx.close_path()
        ctx.set_source_rgba(*hexc("#FF6A3D"))
        ctx.fill()
        ctx.restore()
        for j in range(10):
            k = ((gt * 0.5 + j / 10) % 1.0)
            x = 860 + math.sin(j * 1.7 + gt * 2) * 30 * k
            y = 1550 - k * 230
            if j % 2:
                ctx.arc(x, y, 8 + 6 * k, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.6 * (1 - k) * kv)
                ctx.set_line_width(3)
                ctx.stroke()
            else:
                salt(ctx, x, y, 9, gt + j, alpha=(1 - k) * kv)
        kl2 = ease_back(prog(t, c1[0] + 0.8, c1[0] + 1.2))
        bubble(ctx, 380, 1490, 460, 96, (1, 1, 1, 0.97), scale=kl2)
        text(ctx, "gunung api bawah laut", 380, 1490, 38, NAVY, "black", scale=kl2)


def sc_evap(ctx, t, sc, gt, m):
    c0, c1, c2 = sc["cues"]
    vgrad(ctx, [(0, hexc("#3FA9FF")), (1, hexc("#CDEBFF"))])
    sun(ctx, 860, 300, 90, gt)
    sea_top = 1080
    sea(ctx, sea_top, gt)
    # salt stays inside the sea
    glow = ease_out(prog(t, c1[0] + 1.0, c1[0] + 1.6))
    for (x, ph, rot, s) in SALT[:45]:
        y = sea_top + 80 + ph * 520
        if glow > 0:
            ctx.arc(x, y, s * 2.2, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 0.7, 0.35 * glow * (0.6 + 0.4 * math.sin(gt * 6 + rot)))
            ctx.fill()
        salt(ctx, x + math.sin(gt * 1.5 + rot) * 8, y + math.cos(gt * 1.2 + rot) * 6, s, rot + gt * 0.5)
    # vapor rising from the sea to the cloud
    kv = prog(t, c0[0] + 0.5, c0[0] + 1.2)
    cx, cy = 330, 380
    if kv > 0:
        for (x, ph) in VAPOR:
            k = (gt * 0.35 + ph) % 1.0
            px = x + (cx - x) * ease_io(k)
            py = sea_top - 20 + (cy + 60 - sea_top + 20) * k
            drop(ctx, px, py, 0.6, (0.85, 0.95, 1, 0.75 * kv * (1 - k * 0.6)))
    kc = ease_out(prog(t, c0[0] + 1.0, c2[0]))
    cloud(ctx, cx, cy, 1.0 + 1.0 * kc, 0.97, lerpc((1, 1, 1, 1), (0.86, 0.9, 0.97, 1), kc))
    kt = ease_back(prog(t, c0[0], c0[0] + 0.5))
    text(ctx, "Air menguap", W / 2, 170, 88, hexc("#FFFFFF"), "black", stroke=NAVY, sw=14, scale=kt)
    kl = ease_back(prog(t, c0[0] + 1.5, c0[0] + 1.9))
    bubble(ctx, 760, 620, 300, 90, (1, 1, 1, 0.95), scale=kl)
    text(ctx, "uap air", 760, 620, 44, hexc("#1E6BFF"), "black", scale=kl)
    kg = ease_back(prog(t, c1[0] + 0.6, c1[0] + 1.1))
    bubble(ctx, W / 2, 1230, 640, 110, hexc("#FF5C8A"), scale=kg)
    text(ctx, "Garam tertinggal!", W / 2, 1230, 56, (1, 1, 1, 1), "black", stroke=NAVY, sw=8, scale=kg)
    # fresh rain falls back on land (left side)
    if t > c2[0] + 0.6:
        kr = prog(t, c2[0] + 0.6, c2[0] + 1.2)
        for j in range(14):
            x = cx - 160 + (j * 53) % 320
            y = cy + 100 + ((gt * 700 + j * 77) % 420)
            drop(ctx, x, y, 0.7, (0.6, 0.85, 1, 0.9 * kr))
        kh = ease_back(prog(t, c2[0] + 1.4, c2[0] + 1.8))
        bubble(ctx, 330, 970, 360, 90, hexc("#4DD97A"), scale=kh)
        text(ctx, "hujan tawar", 330, 970, 44, (1, 1, 1, 1), "black", stroke=NAVY, sw=7, scale=kh)


def hourglass(ctx, x, y, s, t, k):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.pi * ease_io(clamp((t % 2.4 - 1.9) / 0.5)))
    ctx.scale(s, s)
    for sy in (-1, 1):
        rrect(ctx, -110, sy * 150 - 14, 220, 28, 12)
        ctx.set_source_rgba(*hexc("#B06A3B"))
        ctx.fill()
    ctx.move_to(-90, -136)
    ctx.line_to(90, -136)
    ctx.line_to(12, 0)
    ctx.line_to(90, 136)
    ctx.line_to(-90, 136)
    ctx.line_to(-12, 0)
    ctx.close_path()
    ctx.set_source_rgba(0.85, 0.95, 1, 0.5)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.9)
    ctx.set_line_width(6)
    ctx.stroke()
    f = (t % 2.4) / 1.9 if t % 2.4 < 1.9 else 1.0
    top = 1 - f
    ctx.move_to(-80 * top, -120 * top + 0)
    ctx.line_to(80 * top, -120 * top)
    ctx.line_to(0, -4)
    ctx.close_path()
    ctx.set_source_rgba(*hexc("#FFE14D"))
    ctx.fill()
    ctx.move_to(-85, 130)
    ctx.line_to(85, 130)
    ctx.line_to(85 * (1 - f * 0.6), 130 - 100 * f)
    ctx.line_to(-85 * (1 - f * 0.6), 130 - 100 * f)
    ctx.close_path()
    ctx.fill()
    if f < 1:
        ctx.move_to(0, 0)
        ctx.line_to(0, 128)
        ctx.set_line_width(4)
        ctx.stroke()
    ctx.restore()


def sc_years(ctx, t, sc, gt, m):
    c0, c1, c2 = sc["cues"]
    vgrad(ctx, [(0, hexc("#0D3B66")), (1, hexc("#1A7BB8"))])
    rays_bg(ctx, W / 2, 700, gt, (1, 1, 1, 0.05))
    k0 = ease_back(prog(t, c0[0], c0[0] + 0.5))
    k1 = prog(t, c1[0] - 0.3, c1[0] + 0.3)
    if k1 < 1 and k0 > 0.001:
        hourglass(ctx, W / 2, 900, 1.6 * k0, t, k0)
        text(ctx, "Jutaan tahun…", W / 2, 360, 96, hexc("#FFE14D"), "black", stroke=NAVY, sw=14,
             scale=k0, alpha=1 - k1)
    # tank getting saltier
    if k1 > 0:
        a = ease_out(k1)
        x0, y0, w0, h0 = 140, 420, 640, 620
        ctx.push_group()
        rrect(ctx, x0, y0, w0, h0, 40)
        ctx.set_source_rgba(1, 1, 1, 0.15)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(8)
        ctx.stroke()
        rrect(ctx, x0 + 12, y0 + 120, w0 - 24, h0 - 132, 30)
        ctx.set_source_rgba(*hexc("#2EA8E6", 0.85))
        ctx.fill()
        ks = prog(t, c1[0], c1[1])
        n = int(8 + 82 * ks)
        for (x, ph, rot, s) in SALT[:n]:
            px = x0 + 40 + (x / W) * (w0 - 80)
            py = y0 + 160 + ph * (h0 - 200)
            salt(ctx, px + math.sin(gt + rot) * 5, py, s * 0.8, rot)
        # salinity meter
        mx, my, mh = 860, 420, 620
        rrect(ctx, mx, my, 70, mh, 35)
        ctx.set_source_rgba(1, 1, 1, 0.25)
        ctx.fill()
        fh = (mh - 20) * (0.1 + 0.85 * ease_io(ks))
        rrect(ctx, mx + 10, my + mh - 10 - fh, 50, fh, 25)
        ctx.set_source_rgba(*hexc("#FF5C8A"))
        ctx.fill()
        text(ctx, "Keasinan", mx + 35, my - 40, 34, (1, 1, 1, 1), "black")
        text(ctx, "Garam menumpuk", W / 2, 300, 76, hexc("#FFFFFF"), "black", stroke=NAVY, sw=12)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
    # 1 litre ≈ 35 g ≈ 2 tablespoons
    k2 = ease_back(prog(t, c2[0] + 0.2, c2[0] + 0.7))
    if k2 > 0:
        bubble(ctx, W / 2, 1300, 960, 390, (1, 1, 1, 0.97), scale=k2)
        ctx.save()
        ctx.translate(W / 2, 1300)
        ctx.scale(k2, k2)
        # bottle
        rrect(ctx, -400, -120, 170, 250, 34)
        ctx.set_source_rgba(*hexc("#2EA8E6"))
        ctx.fill()
        rrect(ctx, -355, -170, 80, 60, 14)
        ctx.set_source_rgba(*hexc("#1E6BFF"))
        ctx.fill()
        text(ctx, "1 L", -315, 10, 52, (1, 1, 1, 1), "black")
        text(ctx, "≈ 35 gram", 40, -95, 64, hexc("#FF4D6D"), "black")
        ks2 = ease_back(prog(t, c2[0] + 2.6, c2[0] + 3.0))
        for i in range(2 if ks2 > 0.001 else 0):
            sx = -60 + i * 230
            ctx.save()
            ctx.translate(sx, 60)
            ctx.scale(ks2, ks2)
            ctx.save()
            ctx.scale(1, 0.72)
            ctx.arc(0, 0, 66, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(*hexc("#C0C6D6"))
            ctx.fill()
            rrect(ctx, 50, -10, 120, 20, 10)
            ctx.fill()
            ctx.move_to(-52, 0)
            ctx.curve_to(-36, -70, 36, -70, 52, 0)
            ctx.close_path()
            ctx.set_source_rgba(1, 1, 1, 1)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.6, 0.7, 0.85, 1)
            ctx.set_line_width(3)
            ctx.stroke()
            ctx.restore()
        text(ctx, "≈ 2 sendok makan", 90, 145, 40, NAVY, "black", scale=ks2)
        ctx.restore()


def monas(ctx, x, base, h):
    """Simple silhouette of a tall national monument with a flame on top."""
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.rectangle(x - 80, base - 40, 160, 40)
    ctx.fill()
    ctx.move_to(x - 22, base - 40)
    ctx.line_to(x - 12, base - h + 40)
    ctx.line_to(x + 12, base - h + 40)
    ctx.line_to(x + 22, base - 40)
    ctx.close_path()
    ctx.fill()
    ctx.rectangle(x - 24, base - h + 30, 48, 14)
    ctx.fill()
    ctx.move_to(x, base - h - 30)
    ctx.curve_to(x + 22, base - h, x + 12, base - h + 30, x, base - h + 30)
    ctx.curve_to(x - 12, base - h + 30, x - 22, base - h, x, base - h - 30)
    ctx.set_source_rgba(*hexc("#FFC93C"))
    ctx.fill()


def sc_outro(ctx, t, sc, gt, m):
    vgrad(ctx, [(0, hexc("#5B2BFF")), (0.55, hexc("#8E4BFF")), (1, hexc("#24C6FF"))])
    rays_bg(ctx, W / 2, 700, gt)
    c0, c1, c2, c3 = sc["cues"]
    k0 = ease_back(prog(t, c0[0], c0[0] + 0.5))
    bubble(ctx, W / 2, 320, 920, 240, (1, 1, 1, 0.97), scale=k0)
    text(ctx, "Laut asin karena garam", W / 2, 270, 50, NAVY, "black", scale=k0)
    text(ctx, "dari daratan terbawa ke laut", W / 2, 330, 44, hexc("#1E6BFF"), "black", scale=k0)
    text(ctx, "& tertinggal saat air menguap", W / 2, 388, 44, NAVY, "semi", scale=k0)
    # fact: salt layer vs monument
    kf = ease_out(prog(t, c1[0] + 0.3, c1[0] + 1.8))
    fade = 1 - prog(t, c3[0] - 0.3, c3[0] + 0.2)
    if kf > 0 and fade > 0:
        ctx.push_group()
        base = 1020
        ph = 470 * kf
        rrect(ctx, 200, base - ph, 300, ph, 12)
        ctx.set_source_rgba(1, 1, 1, 0.96)
        ctx.fill()
        for j in range(int(ph / 40)):
            ctx.move_to(210, base - j * 40 - 20)
            ctx.line_to(490, base - j * 40 - 20)
        ctx.set_source_rgba(0.6, 0.75, 0.95, 0.6)
        ctx.set_line_width(2)
        ctx.stroke()
        text(ctx, "garam laut", 350, base + 40, 36, (1, 1, 1, 1), "black")
        text(ctx, "> 150 m", 350, base - ph - 40, 52, hexc("#FFE14D"), "black", stroke=NAVY, sw=10,
             alpha=prog(kf, 0.8, 1))
        km = ease_back(prog(t, c1[0] + 3.0, c1[0] + 3.5))
        if km > 0:
            monas(ctx, 760, base, max(80, 410 * km))
            text(ctx, "Monas 132 m", 760, base + 40, 36, (1, 1, 1, 1), "black", scale=km)
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


SCENE_FN = dict(intro=sc_intro, beach=sc_beach, rain=sc_rain, river=sc_river, evap=sc_evap,
                years=sc_years, outro=sc_outro)


if __name__ == "__main__":
    run(SCENES, SCENE_FN, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ep02-kenapa-laut-asin.mp4"))
