#!/usr/bin/env python3
"""
Kenapa Begini? Kenapa Begitu? — Episode 1: Kenapa Langit Berwarna Biru?

Vertical (1080x1920) short. Engine (character, narration, music, render) lives in ../kbkb.py;
this file holds only the episode script and its scene drawings.

Usage: python3 make_video.py [--out episode.mp4] [--preview SECONDS] [--stills]
"""
import math
import os
import sys

import cairo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kbkb import *  # noqa: E402,F401,F403
from kbkb import rnd  # noqa: E402

# --------------------------------------------------------------------------
# Script. Each line: (subtitle text, text sent to TTS or None = same)
# --------------------------------------------------------------------------
SCENES = [
    dict(key="intro", lead=1.3, label="Eps. 1 · Langit Biru", lines=[
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
PARTICLES = [(rnd.uniform(80, W - 80), rnd.uniform(620, 1480), rnd.uniform(9, 17),
              rnd.uniform(0, 6.28)) for _ in range(46)]
SKYDOTS = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0, 6.28), rnd.uniform(60, 170),
            rnd.uniform(5, 11)) for _ in range(150)]


# --------------------------------------------------------------------------
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



if __name__ == "__main__":
    run(SCENES, SCENE_FN, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ep01-kenapa-langit-biru.mp4"))
