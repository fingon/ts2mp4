#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2020 Markus Stenberg
#
# Created:       Thu Dec 31 09:20:57 2020 mstenber
# Last modified: Thu Dec 31 09:34:12 2020 mstenber
# Edit time:     7 min
#
"""

"""

from ts2mp4 import VideoConverter

TEST_INPUT_1 = """
    Stream #0:0[0x13a]: Video: h264 (Main) ([27][0][0][0] / 0x001B), yuv420p(tv, bt709, top first), 1920x1080 [SAR 1:1 DAR 16:9], 25 fps, 50 tbr, 90k tbn, 50 tbc
    Stream #0:1[0x366](swe): Audio: ac3 (AC-3 / 0x332D4341), 48000 Hz, 5.1(side), fltp, 448 kb/s
    Stream #0:2[0xc37](fin): Subtitle: dvb_subtitle ([6][0][0][0] / 0x0006)
    Stream #0:4[0xc4f](swe): Subtitle: dvb_subtitle ([6][0][0][0] / 0x0006) (hearing impaired)
    Stream #0:5[0x13ec](fin): Subtitle: dvb_teletext ([6][0][0][0] / 0x0006)
"""


def test_video_converter():
    vc = VideoConverter(filename="test.ts")
    l = list(vc._parse_streams(TEST_INPUT_1))
    exp = [
        {'input': '0',
         'stream': '0',
         'lang': None,
         'rest': '(Main) ([27][0][0][0] / 0x001B), yuv420p(tv, bt709, top first), 1920x1080 [SAR 1:1 DAR 16:9], 25 fps, 50 tbr, 90k tbn, 50 tbc',
         'subtype': 'h264',
         'type': 'Video',
         },
        {'input': '0',
         'lang': 'swe',
         'rest': '(AC-3 / 0x332D4341), 48000 Hz, 5.1(side), fltp, 448 kb/s',
         'stream': '1',
         'subtype': 'ac3',
         'type': 'Audio'},
        {'input': '0',
         'lang': 'fin',
         'rest': '([6][0][0][0] / 0x0006)',
         'stream': '2',
         'subtype': 'dvb_subtitle',
         'type': 'Subtitle'},
        {'input': '0',
         'lang': 'swe',
         'rest': '([6][0][0][0] / 0x0006) (hearing impaired)',
         'stream': '4',
         'subtype': 'dvb_subtitle',
         'type': 'Subtitle'},
        {'input': '0',
         'lang': 'fin',
         'rest': '([6][0][0][0] / 0x0006)',
         'stream': '5',
         'subtype': 'dvb_teletext',
         'type': 'Subtitle'},
    ]
    assert exp == l
