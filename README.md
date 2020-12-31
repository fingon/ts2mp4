# ts2mp4 #

## What is it?

This is minimal tool mostly for my own amusement, which converts .ts files
I get off terrestial (DVB-C) television in Finland using tvheadend +
Hauppauge dual tuner USB stick running in Raspberry Pi 4.

The output contains:

- h264 video stream
- ac3 audio stream
- dvb subtitle track(s)
- dvb teletext track

And what I want out of it is x265 encoded video stream with aac audio
stream (of moderate bitrate but using default not-so-high-quality encoder).
The tricky part are subtitles; I want them in neat, scalable format instead
of dvb subtitle which is binary.

So what is done is:

- run ccextractor to produce .srt (and grab EPG data out of .ts while at
it)

- ffmpeg the .srt back to new .mp4, alongside the old dvb subtitles as backups
