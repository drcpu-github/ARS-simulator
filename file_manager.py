import bz2
import os

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

def open_stats_file():
    results_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "results")
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)
    stats_counters = [int(f.split(".")[-1]) for f in os.listdir(results_dir) if f.startswith("sim.stats.")]
    if len(stats_counters) == 0:
        count = 0
    else:
        count = max(stats_counters) + 1
    return open(os.path.join(results_dir, "sim.stats." + str(count)), "w+")
