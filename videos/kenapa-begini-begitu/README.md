# Kenapa Begini? Kenapa Begitu?

Seri video pendek edukasi sains (vertikal 1080×1920) untuk YouTube Shorts, TikTok, dan Reels,
dibawakan oleh **Tanya**, si anak penasaran.

| Eps. | Judul | Folder |
|------|-------|--------|
| 1 | Kenapa Langit Berwarna Biru? | [`ep01-langit-biru/`](ep01-langit-biru/) |
| 2 | Kenapa Air Laut Asin? | [`ep02-laut-asin/`](ep02-laut-asin/) |
| 3 | Kenapa Bentuk Bulan Berubah-ubah? | [`ep03-bentuk-bulan/`](ep03-bentuk-bulan/) |

## Struktur

- `kbkb.py`: mesin bersama: karakter Tanya, narasi (edge-tts `id-ID-GadisNeural`, fallback espeak-ng),
  musik & SFX, subtitle, transisi, dan render ke MP4.
- `epXX-*/make_video.py`: naskah (`SCENES`) dan gambar tiap adegan untuk satu episode.

## Kebutuhan

```bash
sudo apt-get install -y ffmpeg espeak-ng mbrola-id1 libcairo2-dev pkg-config
pip install numpy pycairo edge-tts
```

Opsi: `KBKB_VOICE=id-ID-ArdiNeural` (suara pria), `KBKB_TTS=espeak` (mode offline).
