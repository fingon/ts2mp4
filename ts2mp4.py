#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2020 Markus Stenberg
#
# Created:       Wed Dec 30 21:03:16 2020 mstenber
# Last modified: Thu Dec 31 10:30:39 2020 mstenber
# Edit time:     119 min
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
        self.copy_metadata = False

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

        streams = list(self._get_streams())
        subtitles = [
            stream for stream in streams if stream["type"] == "Subtitle"]

        tmp_path = tmp_dir / f"video{self.video_suffix}"
        cmd = ["ffmpeg",
               "-hide_banner",
               "-i", self.filename,
               "-i", str(sub_path),
               ]
        cmd.extend([
            # Select all video/audio
            "-map", "0:v",
            "-map", "0:a",
            "-c:v", self.codec, "-preset", self.preset,
            "-c:a", "aac",
            "-b:a", "256k",

            # we take all subtitles only from srt, and selectively
            # non-teletext ones from .ts
            "-map", "1:s",
            "-c:s", "dvdsub",
            "-c:s:0", "mov_text",
        ])
        lang = None
        for subtitle in subtitles:
            if subtitle["subtype"] != "dvb_teletext":
                lang = subtitle["lang"]
                break
        if lang:
            cmd.extend(["-metadata:s:s:0", f"language={lang}"])
        for i, subtitle in enumerate(subtitles):
            if subtitle["subtype"] == "dvb_teletext":
                continue
            lang = subtitle["lang"]
            new_index = i + 1
            cmd.extend(["-map", f"0:s:{i}",
                        f"-metadata:s:s:{new_index}", f"language={lang}"])

        # Add metadata as is
        if self.copy_metadata:
            cmd.extend([
                "-map_metadata", "0",
                "-map_metadata:s:v", "0:s:v",
                "-map_metadata:s:a", "0:s:a",
            ])

        cmd.append(str(tmp_path))

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
        # This is probably bad idea. What we really want to do is
        # actually just store the dvbsubs as dvdsubs as _backups_ in
        # the new file, after the official subs.
        src_path = Path(self.filename)
        dst_path = src_path.with_suffix(".dvbsub.ts.bz2")
        if dst_path.exists() and not self.force:
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
