# ts2mp4

## What is it?

This is minimal tool mostly for my own use, which converts .ts files I get
off terrestial (DVB-C) television in Finland using tvheadend + Hauppauge
dual tuner USB stick running in Raspberry Pi 4. For video conversion, I use
Mac, as x265 conversion on RPi with reasonable quality is about 0.0x frames
per second.

What tvheadend produces seems to be at (at least for me):

- H264 video stream
- AC3 audio stream (sometimes also some other format(s))
- DVB subtitle stream(s)
- DVB teletext stream (dropped by the conversion)
- EPG entry or entries

This script uses ccextractor and ffmpeg to produce libx265 encoded video
stream with original audio, and OCR'd "nicely readable" subtitle
track. Additionally original subtitle tracks are also included, but they're
unfortunately encoded as dvd subtexts (= images, not text). The 'current'
EPG entry is saved into separate .epg.xml file if applicable, but it seems
to be frequently wrong.

## How to use it

- install ccextractor ( https://www.ccextractor.org ) *with* tesseract
support (tesseract is required to make OCR of DVB subtitles possible)

- install ffmpeg ( https://ffmpeg.org )

- run `python3 ts2mp4.py file.ts` and get `file.mp4` (and potentially also `file.srt` and `file.epg.xml`) .. eventually

## Support or lack of it

This isn't really supported piece of software, but as I couldn't find
anyone else packaging the 'full experience' of OTA .TS to something I would
like to archive, I had to make the package for my own use.
