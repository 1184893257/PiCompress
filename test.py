from pi import Compressor
from io import BytesIO
import timeit


# test if run correctly
a = Compressor("Pi.txt")
with open("test.bin", "wb") as f:
    a.compress(BytesIO(b'243f'), f)

out = BytesIO()
with open("test.bin", "rb") as f:
    a.uncompress(f, out)
print(out.getvalue())


# test speed
# def compress1():
#     b = Compressor("Pi.txt")
#     with open("pi.bin", "wb") as f_out:
#         with open("pi.py", "rb") as f_in:
#             b.compress(f_in, f_out)
#
#
# print(timeit.timeit('Compressor("Pi.txt")', 'from pi import Compressor', number=1))
# print(timeit.timeit('compress1()', 'from __main__ import compress1', number=1))
