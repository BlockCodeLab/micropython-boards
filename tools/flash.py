#!python3
# -*- coding: UTF-8 -*-
import argparse
import os

import yaml

# add arguments
#
parser = argparse.ArgumentParser(description="MicroPython Board flasher.")
parser.add_argument("board", help="board name")
parser.add_argument("-p", "--port", help="device port")
parser.add_argument("-P", action="store_true", help="use default device port")
parser.add_argument("-e", "--erase", action="store_true", help="erase device flash")
parser.add_argument("-f", "--firmware", help="firmware path")
args = parser.parse_args()

# show help
if not args.board:
    parser.print_help()
    exit(0)


def is_exists(path):
    return os.path.exists(path)


def load_yaml(file):
    data = None
    try:
        if is_exists(file):
            with open(file) as yaml_file:
                data = yaml.safe_load(yaml_file)
    except:
        pass
    return data


# esp32 flash firmware
#
def esp32_flash(board_info, firmware_path):
    if args.erase:
        print("cleaning flash...\n")
        if args.P:
            os.system("esptool.py --chip auto erase_flash")
        else:
            os.system(f"esptool.py --chip auto --port {args.port} erase_flash")

    if not firmware_path:
        firmware_dir = "dist"
        firmware_path = f"{firmware_dir}/{args.board}.{board_info['version']}.bin"

    if not is_exists(firmware_path):
        print(f"{firmware_path} does not exist.\n")
        exit(1)

    print(f"{firmware_path} is ready.\n")

    print(f"uploading firmware...\n")

    flash_address = board_info["flash address"] if "flash address" in board_info else 0
    if args.P:
        print(f"esptool.py --chip auto write_flash -z {flash_address} {firmware_path}")
        os.system(
            f"esptool.py --chip auto write_flash -z {flash_address} {firmware_path}"
        )
    else:
        os.system(
            f"esptool.py --chip auto --port {args.port} write_flash -z {flash_address} {firmware_path}"
        )


if __name__ == "__main__":
    board = args.board.upper()
    board_info = load_yaml(f"boards/{board}/boardinfo.yml")

    if board_info["port"] == "esp32" and (args.port or args.P):
        esp32_flash(board_info, args.firmware)
