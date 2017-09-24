from io import BufferedIOBase
import io


class ShortSearcher:
    def __init__(self):
        self.next_list = []
        self.first_list = []
        self.byte_first = []
        self.dict = bytearray()

    def find(self, buf: bytearray, no_more: bool) -> list:
        if len(buf) == 1:
            if no_more:
                last_byte = buf[0]
                del buf[0:]
                return [self.byte_first[last_byte], 1]
            return None

        first_short = (buf[0] << 8) + buf[1]
        first_index = self.first_list[first_short]
        max_len = 0
        max_len_index = 0
        while first_index >= 0:
            for i in range(2, len(buf)):
                if buf[i] != get_one_byte(self.dict, first_index + i * 8):
                    if i > max_len:
                        max_len = i
                        max_len_index = first_index
                    break
            else:
                # all match
                if no_more:
                    max_len = len(buf)
                    del buf[0:]
                    return [first_index, max_len]
                return None
            first_index = self.next_list[first_index]
        del buf[0: max_len]
        return [max_len_index, max_len]

    def set_dict(self, array: bytearray):
        self.dict = array
        for i in range(65536):
            self.first_list.append(-1)
        for i in range(len(array) * 8):
            self.next_list.append(-1)
        for i in range((len(array) - 2) * 8, -1, -1):
            two_byte = get_bytes(array, i, 2)
            short_val = (two_byte[0] << 8) + two_byte[1]
            self.next_list[i] = self.first_list[short_val]
            self.first_list[short_val] = i
        for i in self.first_list:
            if i < 0:
                raise RuntimeError("dictionary is too short, not covered [0, 65535]")

        for i in range(256):
            self.byte_first.append(-1)
        filled = 0
        for i in range((len(array) - 1) * 8 + 1):
            one_byte = get_one_byte(array, i)
            if self.byte_first[one_byte] < 0:
                self.byte_first[one_byte] = i
                filled += 1
                if filled == 256:
                    break
        else:
            raise RuntimeError("dictionary is too short, not covered [0, 255]")


class Compressor:
    def __init__(self, dict_path: str, searcher=None, read_len=1024):
        if searcher is None:
            searcher = ShortSearcher()
        self.dict = get_dict(dict_path)
        self.read_len = read_len
        self.buf = bytearray()
        self.searcher = searcher
        self.length = 0
        self.process = 0
        searcher.set_dict(self.dict)

    def compress(self, f_in: BufferedIOBase, f_out: BufferedIOBase):
        self.length = get_file_length(f_in)
        self.process = 0

        self.buf = bytearray()
        while self.__fill_buf(f_in):
            while True:
                pair = self.searcher.find(self.buf, False)
                if pair is None:
                    break
                compress_num(pair, f_out)
        else:
            pair = self.searcher.find(self.buf, True)
            compress_num(pair, f_out)

    def uncompress(self, f_in: BufferedIOBase, f_out: BufferedIOBase):
        while True:
            start = uncompress_num(f_in)
            if start is None:
                break
            byte_len = uncompress_num(f_in)
            # print(hex(start), hex(byte_len))
            f_out.write(get_bytes(self.dict, start, byte_len))

    def __fill_buf(self, f_in: BufferedIOBase) -> bool:
        next_bytes = f_in.read(self.read_len)
        if len(next_bytes) == 0:
            return False

        cur_process = f_in.tell() * 100 // self.length
        if cur_process != self.process:
            self.process = cur_process
            print(str(cur_process) + "%")
        self.buf.extend(next_bytes)
        return True


def get_dict(dict_path: str) -> bytearray:
    with open(dict_path, "r") as f:
        content = f.read()
        array = bytearray()
        for i in range(2, len(content), 2):
            array.append(int(content[i:i+2], 16))
        return array


def get_one_byte(array: bytearray, index: int) -> int:
    byte_index = index >> 3
    offset = index & 7
    extra_byte = 1
    if offset == 0:
        extra_byte = 0
    if byte_index + extra_byte >= len(array):
        return None

    if offset == 0:
        return array[byte_index]
    two_bytes = (array[byte_index] << 8) + array[byte_index + 1]
    return (two_bytes >> (8 - offset)) & 0xFF


def get_bytes(array: bytearray, index: int, byte_len: int) -> bytearray:
    byte_index = index >> 3
    offset = index & 7
    extra_byte = 1
    if offset == 0:
        extra_byte = 0
    if byte_index + byte_len + extra_byte > len(array):
        raise RuntimeError("dictionary is too short, should no small than " + (byte_index + byte_len + extra_byte))

    if offset == 0:
        return array[byte_index: byte_index + byte_len]

    buf = bytearray()
    for i in range(byte_len):
        start = byte_index + i
        two_bytes = (array[start] << 8) + array[start + 1]
        buf.append((two_bytes >> (8 - offset)) & 0xFF)
    return buf


def compress_num(nums: list, f_out: BufferedIOBase):
    # print(hex(nums[0]), hex(nums[1]))
    # use most significant bit to tell the end of a number
    buf = bytearray()
    for num in nums:
        while num >= 128:
            buf.append(num & 0x7F)
            num >>= 7
        else:
            buf.append(num + 128)
    f_out.write(buf)


def uncompress_num(f_in: BufferedIOBase) -> int:
    pos = f_in.tell()
    compressed_num = f_in.read(10)
    if len(compressed_num) == 0:
        return None
    num = 0
    for i in range(len(compressed_num)):
        low = compressed_num[i]
        if low < 128:
            num += low << (i * 7)
        else:
            num += (low - 128) << (i * 7)
            f_in.seek(pos + i + 1)
            return num
    else:
        raise RuntimeError("compressed_num is cut, should enlarge it")


def get_file_length(f_in: BufferedIOBase) -> int:
    pos = f_in.tell()
    f_in.seek(0, io.SEEK_END)
    length = f_in.tell()
    f_in.seek(pos, io.SEEK_SET)
    return length
