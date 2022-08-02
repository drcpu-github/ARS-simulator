#!/usr/bin/python3

import logging
import optparse
import random
import sys
import time

from ARS import ARS
from logger import create_logger

def read_data_requests_file(data_request_file):
    data_requests = {}

    f = open(data_request_file, "r")
    first_line = True
    for line in f:
        # Read and transform CSV data
        epoch, data_request_hash, witnesses, collateral = line.split(",")
        epoch, witnesses, collateral = int(epoch), int(witnesses), int(collateral) / 1E9

        # Normalize epoch
        if first_line:
            first_epoch = epoch
            first_line = False
        epoch -= first_epoch

        # Add to the dictionary
        if epoch not in data_requests:
            data_requests[epoch] = []
        data_requests[epoch].append((witnesses, collateral))
    f.close()

    return data_requests

def generate_block(avg_data_requests, std_data_requests):
    return max(0, round(random.gauss(avg_data_requests, std_data_requests)))

def simulate_block(logger, mode, ars, epoch, data_requests, leftover_reputation):
    # All reputation gained
    all_witnesses = []
    witnessing_acts = 0
    eligibilities = ars.calculate_eligibilities()
    for data_request, (witnesses, collateral) in enumerate(data_requests):
        logger.info(f"{mode}, epoch {epoch}, data request {data_request + 1}")

        success, data_request_witnesses, insufficient_collateral_witnesses = ars.select_witnesses(eligibilities, witnesses, epoch, collateral)
        if success:
            all_witnesses.extend(list(data_request_witnesses))
            witnessing_acts += len(data_request_witnesses)
        else:
            logger.warning(f"Could not solve data request, only {len(data_request_witnesses)} witnesses found, {len(insufficient_collateral_witnesses)} witnesses had insufficient available collateral")

    if witnessing_acts > 0:
        created_reputation = ars.get_ARS_created_reputation(witnessing_acts, epoch)
        expired_reputation = ars.get_ARS_expired_reputation(witnessing_acts, epoch)
        leftover_reputation = ars.update_ARS_reputation(
            all_witnesses,
            created_reputation + leftover_reputation + expired_reputation,
            epoch
        )

    return leftover_reputation

def main():
    start = time.perf_counter()

    parser = optparse.OptionParser()

    # Configurable consensus constants
    parser.add_option("--collateral-locked", type="int", dest="collateral_locked", default=1000, help="Time in epochs collateral will be locked after being used")

    # Number of identities to create and their balance
    parser.add_option("--identities", type="int", dest="identities", default=1000, help="Number of identities to create")
    parser.add_option("--balance", type="int", dest="balance", default=100, help="Balance of each ARS identity in WIT")

    # Options to generate a random ARS
    parser.add_option("--create-random-ars", action="store_true", dest="create_random_ars", help="Create random ARS using below distribution parameters")
    parser.add_option("--max-reputation", type="int", dest="max_reputation", default=10000, help="Maximum reputation the top identity in the ARS can have")
    parser.add_option("--zero-reputation-ratio", type="int", dest="zero_reputation_ratio", default=50, help="Percentage of ARS members that have zero reputation")

    # Options to generate a distribution of data requests
    parser.add_option("--avg-data-requests", type="int", dest="avg_data_requests", default=4, help="Average number of data requests in a block")
    parser.add_option("--std-data-requests", type="int", dest="std_data_requests", default=2, help="Standard deviation of the average number of data requests in a block")
    parser.add_option("--witnesses", type="int", dest="witnesses", default=10, help="Number of witnesses in a data request")
    parser.add_option("--collateral", type="int", dest="collateral", default=5, help="Collateral required by data request")

    # Simulation parameters
    parser.add_option("--offset-epochs", type="int", dest="offset_epochs", default=0, help="Epoch offset for when to start the simulation")
    parser.add_option("--warmup-epochs", type="int", dest="warmup_epochs", default=0, help="Number of epochs for which to warmup the ARS")
    parser.add_option("--simulation-epochs", type="int", dest="detailed_epochs", default=1000, help="Number of epochs for which the ARS simulation runs")

    # Options to create a simulation based on the actual network
    parser.add_option("--ars-file", type="string", dest="ars_file", help="Read and build ARS based on a file")
    parser.add_option("--data-requests-file", type="string", dest="data_request_file", help="Read and simulate data requests from a file")

    options, args = parser.parse_args()

    if options.create_random_ars:
        ars = ARS(options.collateral_locked)
        ars.initialize_random_ARS(
            options.identities,
            options.max_reputation,
            options.zero_reputation_ratio,
            options.balance,
        )
    elif options.ars_file:
        ars = ARS(options.collateral_locked)
        ars.initialize_ARS_from_file(
            options.ars_file,
            options.balance,
        )
        if options.warmup_epochs < 1000:
            print("You should warmup the simulation for at least 1000 epochs to make sure the collateral and reputation expiry lists contain reasonable values.")
    else:
        ars = ARS(options.collateral_locked)
        ars.initialize_zero_reputation_ARS(
            options.identities,
            options.balance,
        )

    data_requests_per_epoch = {}
    if options.data_request_file:
        data_requests_per_epoch = read_data_requests_file(options.data_request_file)

    logger = create_logger(__name__)

    # Run a warmup phase in the simulation
    total_warmup_data_requests, leftover_reputation = 0, 0
    for epoch in range(options.offset_epochs, options.offset_epochs + options.warmup_epochs):
        if data_requests_per_epoch == {}:
            num_data_requests = generate_block(avg_data_requests, std_data_requests)
            data_requests = [(options.witnesses, options.collateral) * num_data_requests]

            total_warmup_data_requests += num_data_requests

            leftover_reputation = simulate_block(
                logger,
                "Warmup",
                ars,
                epoch,
                data_requests,
                leftover_reputation,
            )
        else:
            if epoch in data_requests_per_epoch:
                total_warmup_data_requests += len(data_requests_per_epoch[epoch])

                leftover_reputation = simulate_block(
                    logger,
                    "Warmup",
                    ars,
                    epoch,
                    data_requests_per_epoch[epoch],
                    leftover_reputation,
                )
            else:
                logger.info(f"Warmup, epoch {epoch}, 0 data requests")

    if options.warmup_epochs > 0:
        # assert that the reputation statistics make sense
        for identity in ars.identities.values():
            assert identity.total_reputation == sum(reputation[1] for reputation in identity.reputation_gains)

        ars.print_ARS()

    if options.detailed_epochs > 0:
        ars.clear_stats()
    else:
        print(f"Data requests simulated in warmup: {total_warmup_data_requests}, {total_warmup_data_requests / (options.warmup_epochs or 1)} / epoch")
        ars.collect_stats()

    # Run the actual simulation
    total_detailed_data_requests, leftover_reputation = 0, 0
    epochs_before = options.offset_epochs + options.warmup_epochs
    for epoch in range(epochs_before, epochs_before + options.detailed_epochs):
        if data_requests_per_epoch == {}:
            num_data_requests = generate_block(avg_data_requests, std_data_requests)
            data_requests = [(options.witnesses, options.collateral) * num_data_requests]

            total_detailed_data_requests += num_data_requests

            leftover_reputation= simulate_block(
                logger,
                "Detailed",
                ars,
                epoch,
                data_requests,
                leftover_reputation,
            )
        else:
            if epoch in data_requests_per_epoch:
                total_detailed_data_requests += len(data_requests_per_epoch[epoch])

                leftover_reputation = simulate_block(
                    logger,
                    "Detailed",
                    ars,
                    epoch,
                    data_requests_per_epoch[epoch],
                    leftover_reputation,
                )
            else:
                logger.info(f"Detailed, epoch {epoch}, 0 data requests")

    if options.detailed_epochs > 0:
        # assert that the reputation statistics make sense
        for identity in ars.identities.values():
            assert identity.total_reputation == sum(reputation[1] for reputation in identity.reputation_gains)

        ars.print_ARS()

    if options.detailed_epochs > 0:
        print(f"Data requests simulated in warmup: {total_warmup_data_requests}, {total_warmup_data_requests / (options.warmup_epochs or 1)} / epoch")
        print(f"Data requests simulated in detailed: {total_detailed_data_requests}, {total_detailed_data_requests / (options.detailed_epochs or 1)} / epoch")

    if options.detailed_epochs > 0:
        ars.collect_stats()

    print(f"The simulation took {time.perf_counter() - start:.2f} seconds")

if __name__ == "__main__":
    main()
