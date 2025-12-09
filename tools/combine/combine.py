#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
The MIT License (MIT)
Copyright © 2022 Walkline Wang (https://walkline.wang)
Gitee: https://gitee.com/walkline/micropython-resource-manager

Append user resource files to specified partition of MicroPython firmware
"""

import argparse
import os
from pathlib import Path

try:
    from littlefs import LittleFS, LittleFSError
except ImportError:
    print(
        """
Please install littlefs-python first!

    pip3 install littlefs-python"""
    )
    exit(0)


LITTLEFS_IMAGE_TEMP = "littlefs.img"
BLOCK_SIZE = 4096
PROG_SIZE = 256
DISK_VERSION = 0x0002_0000  # "2.0"


def __is_file_folder_exists(name, is_folder=False):
    if is_folder:
        return os.path.exists(name) and os.path.isdir(name)
    else:
        return os.path.exists(name) and os.path.isfile(name)


# https://github.com/jrast/littlefs-python/blob/master/examples/mkfsimg.py
def __generate_littlefs_partition(folder, size):
    block_count = size // BLOCK_SIZE

    if block_count * BLOCK_SIZE != size:
        print("Failed, image size should be a multiple of block size.")
        exit(1)

    fs = LittleFS(
        block_size=BLOCK_SIZE,
        block_count=block_count,
        prog_size=PROG_SIZE,
        disk_version=DISK_VERSION,
    )

    folder_path = Path(folder)
    print(f"Add files from {folder_path}")

    for filename in folder_path.rglob("*"):
        lfs_filename = f"/{filename.relative_to(folder_path).as_posix()}"

        if filename.is_file() and not lfs_filename.endswith(".DS_Store"):
            with open(filename, "rb") as src_file:
                # use the relative path to source as the littlefs filename
                print(f"- Adding {lfs_filename}")

                try:
                    with fs.open(lfs_filename, "wb") as lfs_file:
                        lfs_file.write(src_file.read())
                except LittleFSError as lfse:
                    if lfse.code == LittleFSError.Error.LFS_ERR_NOSPC:
                        print("\nFailed, not enough space left.")
                        exit(1)
                    else:
                        print(f"Failed, {lfse}")
        elif filename.is_dir():
            fs.mkdir(lfs_filename)

    with open(LITTLEFS_IMAGE_TEMP, "wb") as image_file:
        image_file.write(fs.context.buffer)


def combine(args):
    if __is_file_folder_exists(args.firmware) and __is_file_folder_exists(
        args.dir, True
    ):
        __generate_littlefs_partition(args.dir, int(args.size, 16))

        with (
            open(args.firmware, "rb") as input_file,
            open(args.out, "wb") as output_file,
            open(LITTLEFS_IMAGE_TEMP, "rb") as partition_file,
        ):
            # 复制固件内容到输出文件并移动指针到资源分区起始处
            output_file.write(input_file.read())
            output_file.seek(int(args.offset, 16))

            if args.esp32:
                output_file.seek(-0x1000, 1)

            # 写入资源分区文件
            output_file.write(partition_file.read())
            output_file.flush()

        try:
            os.remove(LITTLEFS_IMAGE_TEMP)
        except:
            pass

        print(f"\nCompleted, saved to {args.out}.")
    else:
        print("\nFailed, firmware or resource folder not exists.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combine resource to firmware.",
    )
    parser.add_argument("--dir", required=True, help="resource folder path")
    parser.add_argument(
        "--offset",
        default=hex(0x300000),
        help="Combine resource address offset (default: 0x300000)",
    )
    parser.add_argument(
        "--size",
        default=hex(0x100000),
        help="Combine resource size (default: 0x100000)",
    )
    parser.add_argument("--esp32", action="store_true", help="ESP32 or ESP32-S2")
    parser.add_argument("firmware", help="firmware path")
    parser.add_argument("out", help="out path")
    args = parser.parse_args()

    combine(args)
