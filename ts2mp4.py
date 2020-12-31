#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2020 Markus Stenberg
#
# Created:       Wed Dec 30 21:03:16 2020 mstenber
# Last modified: Thu Dec 31 09:59:25 2020 mstenber
# Edit time:     97 min
#
"""

This is utility script which converts raw .TS from terrestial
broadcast to something more sane using ffmpeg.

"""

import tempfile
import bz2
import shutil
import subprocess
from pathlib import Path
import re

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


class VideoConverter:
    def __init__(self, *, filename, force=False):
        self.force = force
        self.filename = filename
        self.preset = "slow"  # ~12fps on test material
        # self.preset = "slower"  # ~3fps on test material
        # self.preset = "veryslow" ~2fps on test material
        self.codec = "libx265"
        self.video_suffix = ".mp4"
        self.dvdsub = False

    def _get_streams(self):
        output = subprocess.run(["ffprobe", self.filename],
                                capture_output=True, check=True).stderr.decode()
        yield from self._parse_streams(output)

    def _parse_streams(self, output):
        for line in output.split("\n"):
            m = stream_re.match(line)
            if m is not None:
                yield m.groupdict()

    def _convert_video(self, tmp_dir):
        src_path = Path(self.filename)
        dst_path = src_path.with_suffix(self.video_suffix)
        self._archive_epg_srt()
        sub_path = src_path.with_suffix(".srt")
        if dst_path.exists() and not self.force:
            return
        tmp_path = tmp_dir / f"video{self.video_suffix}"
        cmd = ["ffmpeg",
               "-i", self.filename,
               ]
        if self.dvdsub:
            # Fugly DVD subtitles (bitmap, from bitmap dvb_subtitle)
            subtitles = [
                x for x in self._get_streams() if x["type"] == "Subtitle"
            ]
            for i, r in enumerate(subtitles):
                if r["subtype"] == "dvb_teletext":
                    continue
                cmd.extend(["-map", f"0:s:{i}"])
            cmd.extend(["-c:s", "dvdsub"])
        else:
            # Hopefully prettier OCR'd SRT
            cmd.extend(["-i", str(sub_path)])
        cmd.extend([
            # Select all video/audio
            "-map", "0:v",
            "-map", "0:a",
            "-c:v", self.codec, "-preset", self.preset,
            "-c:a", "aac",
        ])
        if not self.dvdsub:
            cmd.extend(["-map", "1:s",
                        "-c:s", "mov_text"])
            lang = None
            for r in self._get_streams():
                if r["type"] == "Subtitle" and r["subtype"] != "dvb_teletext":
                    lang = r["lang"]
                    break
            if lang:
                cmd.extend(["-metadata:s:s:0", f"language={lang}"])
        cmd.extend([
            "-map_metadata", "0",
            "-map_metadata:s:v", "0:s:v",
            "-map_metadata:s:a", "0:s:a",
            str(tmp_path)
        ])
        print(cmd)
        subprocess.run(cmd, check=True)
        tmp_path.rename(dst_path)

    def _archive_epg_srt(self):
        src_path = Path(self.filename)
        src_without_suffix = str(src_path)[:-len(src_path.suffix)]
        dst_path = Path(f"{src_without_suffix}_epg.xml")
        if dst_path.exists() and not self.force:
            return
        cmd = ["ccextractor", self.filename,
               "-codec", "dvbsub",
               "--nofontcolor",
               "-xmltv", "1", "-xmltvonlycurrent"]
        subprocess.run(cmd, check=True)

    def _archive_dvbsub(self, tmp_dir):
        src_path = Path(self.filename)
        dst_path = src_path.with_suffix(".dvbsub.ts.bz2")
        if dst_path.exists() and not self.force:
            return
        tmp_path = tmp_dir / f"dvbsub.{src_path.suffix}"
        cmd = ["ffmpeg",
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
            self._archive_dvbsub(tmp_dir_path)
            self._archive_epg_srt()
            self._convert_video(tmp_dir_path)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("filename", metavar="N", nargs="+",
                   help="Path to .ts file(s) to convert")
    p.add_argument("--force", "-f", action="store_true",
                   help="Redo steps even if results exist")
    args = p.parse_args()
    for filename in args.filename:
        vc = VideoConverter(filename=filename, force=args.force)
        vc.run()
