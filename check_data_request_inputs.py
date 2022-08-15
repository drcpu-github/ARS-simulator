#!/usr/bin/python3

import bz2
import os

def main():
    for f in sorted(os.listdir("input")):
        if f.startswith("data_requests"):
            f_dr = bz2.open(os.path.join("input", f))
            data_requests = {}
            for line in f_dr:
                epoch = int(line.decode("utf-8").split(",")[0])
                if epoch not in data_requests:
                    data_requests[epoch] = 0
                data_requests[epoch] += 1
            f_dr.close()

            min_epoch, max_epoch = min(data_requests.keys()), max(data_requests.keys())
            for epoch in range(min_epoch, max_epoch):
                if epoch not in data_requests:
                    data_requests[epoch] = 0

            dr_histo = {}
            for epoch, drs in data_requests.items():
                if drs not in dr_histo:
                    dr_histo[drs] = 0
                dr_histo[drs] += 1

            total_epochs = max_epoch - min_epoch

            print(f)
            print("\n".join(f"\tBlocks with {key} data requests: {value / total_epochs * 100:.2f}%" for key, value in sorted(dr_histo.items())))
            print(f"Average number of data requests per block: {sum([key * value / total_epochs for key, value in dr_histo.items()])}")

if __name__ == "__main__":
    main()