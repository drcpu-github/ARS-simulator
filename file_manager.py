import bz2

def open_file(filename):
    test_file = open(filename, "rb")
    # Test if file is in bz2 format
    if test_file.read(3) == b"\x42\x5a\x68":
        f = bz2.open(filename, "rt")
    # If not, open it as a normal file
    else:
        f = open(filename, "r")
    test_file.close()

    return f
