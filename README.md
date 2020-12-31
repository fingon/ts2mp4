# ts2mp4

## What is it?

This is minimal tool mostly for my own amusement, which converts .ts files
I get off terrestial (DVB-C) television in Finland using tvheadend +
Hauppauge dual tuner USB stick running in Raspberry Pi 4. For video
conversion, I use desktop, as x265

What tvheadend produces seems to be at (at least for me):

- h264 video stream
- ac3 audio stream (sometimes also some other format(s))
- dvb subtitle track(s)
- dvb teletext track

This script uses ccextractor and ffmpeg to produce libx265 encoded video
stream with original audio, and OCR'd "nicely readable" subtitle
track. Additionally original subtitle tracks are also included, but they're
unfortunately encoded as dvd subtexts (= images, not text).

## How to use it

- install ccextractor ( https://www.ccextractor.org ) *with* tesseract
support (required to make OCR of DVB subtitles possible)

- install ffmpeg ( https://ffmpeg.org )

- run `python3 ts2mp4.py file.ts` and get `file.mp4` (and potentially also `file.srt` and `file.epg.xml`) .. eventually
