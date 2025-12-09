#!python3
# -*- coding: UTF-8 -*-
from bdfparser import Font
from font_map import FONT_MAP

def_get_font = """
def get_font(char):
    index = FONT_MAP.find(char)
    if not fonts or index == -1:
        return

    cache = fonts_cache.get(index)
    if cache:
        return cache

    fonts.seek(GLYPH_INFO_SIZE * index)
    glyph_info = fonts.read(GLYPH_INFO_SIZE).hex()

    offset = int(glyph_info[:6], 16)
    size = int(glyph_info[6:8], 16)
    dwidth = int(glyph_info[8:10], 16)
    bbw = int(glyph_info[10:12], 16)
    bbh = int(glyph_info[12:14], 16)
    bbxoff = int(glyph_info[14:16], 16)
    bbyoff = int(glyph_info[16:], 16)

    if bbxoff > 200:
        bbxoff -= 255

    if bbyoff > 200:
        bbyoff -= 255

    bitmap = False
    if size != 0:
        fonts.seek(BITMAP_OFFSET + offset)
        bitmap = memoryview(bytearray(fonts.read(size)))

    return bitmap, dwidth, bbw, bbh, bbxoff, bbyoff
"""


def compile(font, dist):
    offset = 0
    glyph_info_map = bytearray()
    font_bitmap = bytearray()
    font_map = ""

    def hexNum(num, length):
        if num < 0:
            num = 255 + num
        return ("0" * length + hex(num)[2:])[-length:]

    glyph_info_size = 0
    for glyph in font.iterglyphs():
        if (
            glyph.cp() < 0
            or FONT_MAP.find(glyph.chr()) == -1
            or font_map.find(glyph.chr()) != -1
        ):
            continue

        meta = glyph.meta

        font_buf = bytearray()
        for data in meta["hexdata"]:
            font_buf += bytes.fromhex(data)

        size = len(font_buf)
        glyph_info = bytes.fromhex(
            hexNum(offset, 6)
            + hexNum(size, 2)
            + hexNum(meta["dwx0"], 2)
            + hexNum(meta["bbw"], 2)
            + hexNum(meta["bbh"], 2)
            + hexNum(meta["bbxoff"], 2)
            + hexNum(meta["bbyoff"], 2)
        )
        glyph_info_size = len(glyph_info)
        glyph_info_map += glyph_info
        font_bitmap += font_buf
        font_map += glyph.chr()
        offset += size

    bounding_box = (
        font.headers["fbbx"],
        font.headers["fbby"],
        font.headers["fbbxoff"],
        font.headers["fbbyoff"],
    )
    pointsize = font.headers["pointsize"]

    with open(f"{dist}.py", "w") as config_file:
        config_file.write("from micropython import const\n\n")
        config_file.write(f"POINTSIZE = const({pointsize})\n")
        config_file.write(f"GLYPH_INFO_SIZE = const({glyph_info_size})\n")
        config_file.write(f"BITMAP_OFFSET = const({len(glyph_info_map)})\n")
        config_file.write(
            f"BOUNDING_BOX = (const({bounding_box[0]}), const({bounding_box[1]}), const({bounding_box[2]}), const({bounding_box[3]}))\n"
        )
        config_file.write(f'FONT_MAP = """{font_map}"""\n\n')
        config_file.write("fonts_cache = {}\n")
        config_file.write("fonts = None\n")
        config_file.write(
            f'try:\n    fonts = open("/res/{dist.split("/")[-1]}.bmp", "rb")\n'
        )
        config_file.write('except:\n    print("load font bitmap failed.")\n\n')
        config_file.write(def_get_font)

    with open(f"{dist}.bmp", "wb") as font_file:
        font_file.write(glyph_info_map)
        font_file.write(font_bitmap)

    return font_map


font_map1 = compile(Font("./wqy-bitmapsong/wenquanyi_9pt.bdf"), "./dist/font12")
font_map2 = compile(Font("./wqy-bitmapsong/wenquanyi_12pt.bdf"), "./dist/font16")

# Remove characters that are not in both fonts
font_map = ""
for c in font_map1:
    if c in font_map2:
        font_map += c

with open("./dist/font_map.py", "w") as map_file:
    map_file.write(f'FONT_MAP = """{font_map}"""\n')
