## Basic ARS simulator

This simulator will simulate a number of epochs and data requests. It will calculate identity eligibility and model whether an identity has enough collateral to available to solve a data request. It also models ARS reputation gains and expiration.

## Usage

```
./simulator -h
```

Example of a run command:
```
./simulator --collateral-timeout=2000 --ars-size=5000 --start-epoch=500 --simulation-epochs=10000
```
