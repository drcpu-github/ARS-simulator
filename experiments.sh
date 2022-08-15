#!/bin/bash

# Real world workload, collateral locked for one week, simulating two weeks warmup and four weeks detailed
for b in {1000..5000..1000}
do
    rm -f simulation.log
    ~/pypy3.9-v7.3.9-linux64/bin/pypy3 ./simulator.py --ars-file input/ars_20220804.csv.bz2 --data-requests-file input/data_requests_202206.csv.bz2,input/data_requests_202207.csv.bz2 --collateral-locked 13440 --warmup-epochs 26880 --simulation-epochs 53760 --balance ${b}
done

# Real world workload, collateral locked for one week, simulating two weeks warmup and four weeks detailed
for b in {1000..5000..1000}
do
    rm -f simulation.log
    ~/pypy3.9-v7.3.9-linux64/bin/pypy3 ./simulator.py --ars-file input/ars_20220804.csv.bz2 --data-requests-file input/data_requests_202206.csv.bz2,input/data_requests_202207.csv.bz2 --collateral-locked 26880 --warmup-epochs 26880 --simulation-epochs 53760 --balance ${b}
done

# Synthetic workload with 2 data requests per second, collateral locked for one week, simulating two weeks warmup and four weeks detailed
for b in {1000..5000..1000}
do
    rm -f simulation.log
    ~/pypy3.9-v7.3.9-linux64/bin/pypy3 ./simulator.py --ars-file input/ars_20220804.csv.bz2 --avg-data-requests 2 --collateral-locked 13440 --warmup-epochs 26880 --simulation-epochs 53760 --balance ${b}
done

# Synthetic workload with 2 data requests per second, collateral locked for two weeks, simulating two weeks warmup and four weeks detailed
for b in {1000..8000..1000}
do
    rm -f simulation.log
    ~/pypy3.9-v7.3.9-linux64/bin/pypy3 ./simulator.py --ars-file input/ars_20220804.csv.bz2 --avg-data-requests 2 --collateral-locked 26880 --warmup-epochs 26880 --simulation-epochs 53760 --balance ${b}
done

# Synthetic workload with 4 data requests per second, collateral locked for one week, simulating two weeks warmup and four weeks detailed
for b in {1000..5000..1000}
do
    rm -f simulation.log
    ~/pypy3.9-v7.3.9-linux64/bin/pypy3 ./simulator.py --ars-file input/ars_20220804.csv.bz2 --avg-data-requests 4 --collateral-locked 13440 --warmup-epochs 26880 --simulation-epochs 53760 --balance ${b}
done

# Synthetic workload with 4 data requests per second, collateral locked for two weeks, simulating two weeks warmup and four weeks detailed
for b in {1000..8000..1000}
do
    rm -f simulation.log
    ~/pypy3.9-v7.3.9-linux64/bin/pypy3 ./simulator.py --ars-file input/ars_20220804.csv.bz2 --avg-data-requests 4 --collateral-locked 26880 --warmup-epochs 26880 --simulation-epochs 53760 --balance ${b}
done
