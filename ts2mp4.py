#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2020 Markus Stenberg
#
# Created:       Wed Dec 30 21:03:16 2020 mstenber
# Last modified: Mon Jan  4 09:55:43 2021 mstenber
# Edit time:     201 min
#
"""

This is utility script which converts raw .TS from terrestial
broadcast to something more sane using ffmpeg.

"""

import argparse
import bz2
import pprint
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

stream_re = re.compile(
    r"""(?x)
^
  \s*
  Stream\s+\#(?P<input>\d+):(?P<stream>\d+)
  \[0x[0-9a-f]+\](\((?P<lang>\S+)\))?:\s+
  (?P<type>\S+):\s+(?P<subtype>\S+)\s+
  (?P<rest>.*)
$"""
)


def parse_streams(output):
    for line in output.split("\n"):
        m = stream_re.match(line)
        if m is not None:
            yield m.groupdict()


class VideoConverter:
    def __init__(self, *, args, filename):
        self.args = args
        self.filename = filename

    def _get_streams(self):
        output = subprocess.run(["ffprobe", self.filename],
                                capture_output=True, check=True).stderr.decode()
        yield from parse_streams(output)

    def _convert_video(self, tmp_dir):
        src_path = Path(self.filename)
        dst_path = src_path.with_suffix(self.args.video_suffix)
        if dst_path.exists() and not self.args.force:
            return

        streams = list(self._get_streams())
        subtitles = [
            stream for stream in streams if stream["type"] == "Subtitle"]
        dvb_subtitles = [
            subtitle for subtitle in subtitles if subtitle["subtype"] != "dvb_teletext"
        ]

        sub_path = src_path.with_suffix(".srt")
        if not sub_path.exists() and dvb_subtitles:
            self._archive_epg_srt()

        tmp_path = tmp_dir / f"video{self.args.video_suffix}"
        cmd = ["ffmpeg",
               "-hide_banner",
               "-i", self.filename,
               ]
        if dvb_subtitles:
            cmd.extend([
                "-i", str(sub_path),
            ])

        sti = {}
        subtitles = 0
        dest_index = 0
        for stream in streams:
            input_number = stream["input"]
            stream_number = stream["stream"]
            mapsource = f"{input_number}:{stream_number}"
            type_index = sti.setdefault(stream["type"], 0)
            sti[stream["type"]] = type_index + 1
            metadata = []
            if stream["type"] in ["Video", "Audio"]:
                cmd.extend(["-map", mapsource])
            elif stream["type"] == "Subtitle":
                # Drop teletext on the floor
                if stream["subtype"] == "dvb_teletext":
                    continue
                lang = stream["lang"]
                if type_index == 0:
                    # This is 'bonus' stream not accounted for in the sti
                    cmd.extend([
                        # we take all subtitles only from srt, and selectively
                        # non-teletext ones from .ts
                        "-map", "1:s",
                        "-c:s:0", "mov_text",
                        "-metadata:s:s:0", f"language={lang}",
                    ])
                    dest_index += 1
                subtitles += 1
                cmd.extend(["-map", mapsource,
                            f"-c:s:{subtitles}", "dvdsub"])
            # Add extra metadata we produce (TBD if we ever want to remove any?)
            if metadata:
                for entry in metadata:
                    cmd.extend([f"-metadata:s:{dest_index}", entry])
            dest_index += 1

        cmd.extend([
            # Uniform handling for all video+audio
            "-c:v", self.args.video_codec,

            "-c:a", self.args.audio_codec,

            # ffmpeg bug workaround with few streams - https://trac.ffmpeg.org/ticket/6375
            "-max_muxing_queue_size", "1024",
        ])

        if self.args.video_codec != 'copy':
            cmd.extend(["-preset", self.args.video_preset])
        if self.args.audio_codec != 'copy':
            cmd.extend(["-b:a", self.args.audio_bitrate])

        cmd.extend([
            # "-map_metadata:g", "0:g",  # copy global metadata # default
            "-empty_hdlr_name", "1",  # omit dummy handler name fields
            str(tmp_path)])
        pprint.pprint(cmd)
        subprocess.run(cmd, check=False)
        # Using check=True would be ideal, but sometimes files end
        # with garbage and ffmpeg returns nonzero return code. TBD if
        # there's some way to ignore it, for now, we just assume files
        # don't shrink to sub-percent size and copy those over.
        if tmp_path.exists() and tmp_path.stat().st_size > dst_path.stat().st_size / 100:
            tmp_path.rename(dst_path)
        else:
            sys.exit(1)

    def _archive_epg_srt(self):
        src_path = Path(self.filename)
        src_without_suffix = str(src_path)[:-len(src_path.suffix)]
        srt_path = src_path.with_suffix(".srt")
        dst_path = src_path.with_suffix(".epg.xml")
        if dst_path.exists() and srt_path.exists() and not self.args.force:
            return
        cmd = ["ccextractor", self.filename,
               "-codec", "dvbsub",
               "--nofontcolor",
               "-xmltv", "1", "-xmltvonlycurrent"]
        subprocess.run(cmd, check=True)
        output_path = Path(f"{src_without_suffix}_epg.xml")
        output_path.rename(dst_path)

    def _archive_dvbsub(self, tmp_dir):
        # This is probably bad idea. What we really want to do is
        # actually just store the dvbsubs as dvdsubs as _backups_ in
        # the new file, after the official subs.
        src_path = Path(self.filename)
        dst_path = src_path.with_suffix(".dvbsub.ts.bz2")
        if dst_path.exists() and not self.args.force:
            return
        tmp_path = tmp_dir / f"dvbsub.{src_path.suffix}"
        cmd = ["ffmpeg",
               "-hide_banner",
               "-i", self.filename,
               # Select all video/audio
               "-c", "copy",
               "-map", "0:s",
               str(tmp_path)
               ]
        subprocess.run(cmd, check=True)
        with bz2.open(dst_path, "wb") as dst, open(tmp_path, "rb") as src:
            shutil.copyfileobj(src, dst)

    def run(self):
        with tempfile.TemporaryDirectory(dir=Path(self.filename).parent,
                                         prefix="ts2ffmpeg-tmp-") as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            # self._archive_dvbsub(tmp_dir_path)
            # self._archive_epg_srt()
            self._convert_video(tmp_dir_path)


def main():
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("filename", metavar="TS-FILE", nargs="+",
                   help="Path to .ts file(s) to convert")
    p.add_argument("--video-codec", help="Video codec to use (or 'copy' to leave it unchanged)",
                   default="libx265")
    p.add_argument("--video-preset", help="Video codec preset",
                   default="slow")
    p.add_argument("--video-suffix", help="Video suffix to use",
                   default=".mp4")
    p.add_argument("--audio-codec", help="Audio codec to use (or 'copy' to leave it unchanged)",
                   default="copy")
    p.add_argument("--audio-bitrate", help="Audio bitrate to use (if not 'copy' codec)",
                   default="256k")
    p.add_argument("--force", "-f", action="store_true",
                   help="Redo steps even if results exist")
    args = p.parse_args()
    for filename in args.filename:
        vc = VideoConverter(filename=filename, args=args)
        vc.run()


if __name__ == '__main__':
    main()
