# micropython-boards

编译 MicroPython 固件以支持自制开发板。

## 关于本代码库

本代码库的各级目录功能如下：

- [boards](boards/): 各种芯片主核的开发板
- [cmodules](cmodules/): C 语言编写的 MicroPython 驱动和库
- [examples](examples/): 示例代码
- [lib](lib/): 第三方库引用
- [micropython](micropython/): MicroPython 引用
- [modules](modules/): MicroPython 编写的 MicroPython 驱动和库
- [tools](tools/): 工具脚本
  - [combine](tools/combine/): 固件分区资源合并脚本
  - [fonts](tools/fonts/): 像素字转换脚本

## 工具

### 编译

```bash
$ get_idf
$ ./tools/build.py -h
usage: build.py [-h] [-c] [-p PORT] [-P] [-e] board

MicroPython Board builder.

positional arguments:
  board                 board name

optional arguments:
  -h, --help            show this help message and exit
  -c, --clean           clean built
  -p PORT, --port PORT  device port
  -P                    use default device port
  -e, --erase           erase device flash

examples:
  ./tools/build.py s3_camera
  ./tools/build.py -c -P s3_camera
  ./tools/build.py -c -P -e s3_camera
```

其中，`get_idf` 是一个用于获取 ESP-IDF 工具链的脚本。
