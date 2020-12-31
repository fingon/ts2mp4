#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2020 Markus Stenberg
#
# Created:       Wed Dec 30 21:03:16 2020 mstenber
# Last modified: Thu Dec 31 12:16:50 2020 mstenber
# Edit time:     151 min
#
"""

This is utility script which converts raw .TS from terrestial
broadcast to something more sane using ffmpeg.

"""

from pathlib import Path

import bz2
import pprint
import re
import shutil
import subprocess
import tempfile

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
        if dst_path.exists() and not self.force:
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

        tmp_path = tmp_dir / f"video{self.video_suffix}"
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
        for stream in streams:
            mapsource = "%s:%s" % (stream["input"], stream["stream"]
                                   )
            type_index = sti.setdefault(stream["type"], 0)
            sti[stream["type"]] = type_index + 1
            if stream["type"] == "Video":
                cmd.extend(["-map", mapsource])
            elif stream["type"] == "Audio":
                cmd.extend(["-map", mapsource])
                lang = stream["lang"]
                if lang:
                    cmd.extend(
                        [f"-metadata:s:a:{type_index}", f"language={lang}"])
            elif stream["type"] == "Subtitle":
                # Drop teletext on the floor
                if stream["subtype"] == "dvb_teletext":
                    continue
                lang = stream["lang"]
                if type_index == 0:
                    cmd.extend([
                        # we take all subtitles only from srt, and selectively
                        # non-teletext ones from .ts
                        "-map", "1:s",
                        "-c:s:0", "mov_text",
                        "-metadata:s:s:0", f"language={lang}",
                    ])
                subtitles += 1
                cmd.extend(["-map", mapsource,
                            f"-c:s:{subtitles}", "dvdsub",
                            f"-metadata:s:s:{subtitles}", f"language={lang}"])

        cmd.extend([
            # Uniform handling for all video+audio
            "-c:v", self.codec, "-preset", self.preset,

            #"-c:a", "aac",
            #"-b:a", "256k",
            # Size of audio track is unlikely to kill the budget anyway
            "-c:a", "copy",

            # ffmpeg bug workaround with few streams - https://trac.ffmpeg.org/ticket/6375
            "-max_muxing_queue_size", "1024",
        ])

        # Add metadata as is
        if self.copy_metadata:
            cmd.extend([
                "-map_metadata", "0",
                "-map_metadata:s:v", "0:s:v",
                "-map_metadata:s:a", "0:s:a",
            ])

        cmd.append(str(tmp_path))
        pprint.pprint(cmd)
        subprocess.run(cmd, check=True)
        tmp_path.rename(dst_path)

    def _archive_epg_srt(self):
        src_path = Path(self.filename)
        src_without_suffix = str(src_path)[:-len(src_path.suffix)]
        srt_path = src_path.with_suffix(".srt")
        dst_path = src_path.with_suffix(".epg.xml")
        if dst_path.exists() and srt_path.exists() and not self.force:
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
            # self._archive_epg_srt()
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
