# Kenapa Begini? Kenapa Begitu? — Eps. 1: Kenapa Langit Berwarna Biru?

Video pendek vertikal (1080×1920, 30 fps, ±88 detik) untuk Shorts / Reels / TikTok.

![thumbnail](thumbnail.jpg)

- **Video:** [`ep01-kenapa-langit-biru.mp4`](ep01-kenapa-langit-biru.mp4)
- **Pembawa acara:** Tanya, si anak penasaran
- **Topik sains:** hamburan Rayleigh (kenapa langit biru & senja jingga)

## Naskah

| # | Adegan | Narasi |
|---|--------|--------|
| 1 | Pembuka — judul acara, Tanya melambai | Halo, teman-teman! Selamat datang di Kenapa Begini, Kenapa Begitu! Hari ini kita bahas sesuatu yang kita lihat setiap hari. |
| 2 | Pertanyaan — Tanya menatap langit | Pernah nggak, kamu bertanya… kenapa langit berwarna biru? Kenapa bukan hijau, atau merah muda? |
| 3 | Prisma — cahaya putih terurai jadi pelangi | Cahaya matahari memang terlihat putih. Tapi sebenarnya, di dalamnya ada banyak warna: merah, jingga, kuning, hijau, biru, dan ungu! |
| 4 | Partikel udara — gelombang merah lurus, biru terpantul | Saat masuk ke udara, cahaya menabrak partikel udara yang sangat kecil. Cahaya merah gelombangnya panjang, jadi terus lurus. Tapi cahaya biru gelombangnya pendek, jadi mudah terpantul ke segala arah! |
| 5 | Langit jadi biru | Cahaya biru yang tersebar ini memenuhi seluruh langit. Ke mana pun kita memandang, yang sampai ke mata adalah biru. Ungu juga tersebar, tapi mata kita lebih peka pada warna biru. |
| 6 | Bonus: senja — jalur pendek vs jalur panjang | Lalu, kenapa langit sore berwarna jingga? Saat matahari terbenam, cahayanya menempuh jalan yang jauh lebih panjang. Birunya sudah habis tersebar di jalan, tinggal merah dan jingga yang sampai ke mata kita. |
| 7 | Rangkuman & penutup | Jadi, langit biru karena cahaya biru paling banyak dihamburkan oleh udara. Para ilmuwan menyebutnya hamburan Rayleigh! Punya pertanyaan lain? Tulis di kolom komentar ya. Sampai jumpa! |

## Membuat ulang video

Animasi (pycairo), narasi suara neural Indonesia `id-ID-GadisNeural` via edge-tts
(otomatis fallback ke espeak-ng + MBROLA bila offline), musik & efek suara (numpy), encoding (ffmpeg).

```bash
sudo apt-get install -y ffmpeg espeak-ng mbrola-id1 libcairo2-dev pkg-config
pip install numpy pycairo edge-tts
python3 make_video.py            # -> ep01-kenapa-langit-biru.mp4
python3 make_video.py --stills   # satu PNG per adegan untuk dicek
```

Naskah ada di daftar `SCENES` di `make_video.py`; ubah teksnya, timing animasi & subtitle ikut menyesuaikan.
Ganti suara: `KBKB_VOICE=id-ID-ArdiNeural python3 make_video.py` (suara pria). Paksa mode offline: `KBKB_TTS=espeak`.
