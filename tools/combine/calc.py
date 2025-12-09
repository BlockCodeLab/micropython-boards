import os


def get_dirsize(dir):
    size = 0
    for root, dirs, files in os.walk(dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    return size


block_size = 4096  # file system block size
total_size = get_dirsize("res")
block_count = total_size // block_size + 10  # at least 10 blocks
image_size = block_count * block_size
print(hex(image_size))
