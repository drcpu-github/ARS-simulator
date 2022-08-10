import logging
import numpy
import operator
import random

from file_manager import open_file
from identity import Identity
from logger import create_logger

class ARS:
    def __init__(self, log_stdout, log_file, collateral_locked):
        self.logger = create_logger("ARS", log_stdout, log_file)
        self.identity_logger = create_logger("identity", log_stdout, log_file)

        self.current_reputation = 0

        # Set consensus constants
        self.total_reputation = 1 << 20
        self.reputation_expire = 20000
        self.commit_rounds = 4

        # Configurable consensus constants
        self.collateral_locked = collateral_locked

    def initialize_zero_reputation_ARS(self, identities, balance):
        # Identities
        self.identities = {}
        self.number_of_identities = identities
        for reputation in range(self.number_of_identities):
            identity = Identity(
                logger=self.identity_logger,
                available_collateral=[(0, balance)],
            )
            self.identities[identity.name] = identity

        self.current_witnessing_acts = 0

    def initialize_ARS_from_file(self, ars_file, balance):
        f = open_file(ars_file)
        identity_lines = [(line.split(",")[0], int(line.split(",")[1])) for line in f]
        f.close()

        # Identities
        self.identities = {}
        self.number_of_identities = len(identity_lines)
        for name, reputation in identity_lines:
            # Each identity gained reputation from witnessing acts at random times (filtering out zero values)
            random_reputation_gain = self.generate_random_list(int(reputation / 10) + 1, reputation, True)
            identity = Identity(
                logger=self.identity_logger,
                name=name,
                total_reputation=reputation,
                reputation_gains=sorted([
                    (random.randint(0, self.reputation_expire), random_reputation_gain[i]) for i in range(len(random_reputation_gain))
                ]),
                available_collateral=[(0, balance)],
            )
            self.identities[identity.name] = identity

        self.current_witnessing_acts = 0

    def initialize_random_ARS(self, identities, max_reputation, zero_reputation_ratio, balance):
        self.number_of_identities = identities

        # Assign random reputations to part of the ARS
        self.all_reputation = random.sample(range(1, max_reputation), int(self.number_of_identities * (1 - zero_reputation_ratio / 100)))
        # Assign some 0 reputation identities according to a predefined ratio
        self.all_reputation.extend([0] * (self.number_of_identities - len(self.all_reputation)))
        # Make sure the sum of all reputations is equal to self.total_reputation
        self.all_reputation = [int(reputation / sum(self.all_reputation) * self.total_reputation) for reputation in self.all_reputation]
        for i in range(0, self.total_reputation - sum(self.all_reputation)):
            self.all_reputation[i] += 1

        for reputation in self.all_reputation:
            # Each identity gained reputation from witnessing acts at random times (filtering out zero values)
            random_reputation_gain = self.generate_random_list(int(reputation / 16) + 1, reputation, True)
            # Each identity has UTXO's that are locked until a random time (filtering out zero values)
            random_utxos = self.generate_random_list(int(reputation / 16) + 1, balance, True)
            # Each identity gained a random amount of reputation
            identity = Identity(
                logger=self.identity_logger,
                total_reputation=reputation,
                reputation_gains=sorted([
                    (random.randint(0, self.reputation_expire), random_reputation_gain[i]) for i in range(len(random_reputation_gain))
                ]),
                available_collateral=sorted([
                    (random.randint(0, self.collateral_locked), random_utxos[i]) for i in range(len(random_utxos))
                ]),
            )

            self.logger.debug(f"Created identity: {identity}")

            self.identities[identity.name] = identity

        # Set current witnessing acts such that a random amount of reputation can expire on the first new data request
        self.current_witnessing_acts = int(self.reputation_expire * 1.1)

    def generate_random_list(self, items, total_sum, filter_zeros):
        random_list = [random.random() for i in range(items)]
        random_list = [int(random_list[i] / sum(random_list) * total_sum) for i in range(items)]
        for i in range(0, total_sum - sum(random_list)):
            random_list[i] += 1
        random_list = list(filter(lambda x: x != 0, random_list))
        assert sum(random_list) == total_sum
        return random_list

    def set_reputations(self, reputations):
        assert len(self.identities) == len(reputations)
        for identity, reputation in zip(self.identities.keys(), reputations):
            self.identities[identity].reputation = reputation

    # Calculate the result of `y = mx + K`
    # The result is rounded and low saturated in 0
    def magic_line(self, x, m, k):
        res = m * x + k
        if res < 0:
            return 0
        else:
            return round(res, 0)

    # List only those identities with reputation greater than zero
    def filter_reputed_identities(self):
        non_zero_reputation_identities = sorted([identity for identity in self.identities.values() if identity.total_reputation > 0], key=operator.attrgetter("total_reputation"), reverse=True)
        total_reputation = sum([identity.total_reputation for identity in self.identities.values()])
        return non_zero_reputation_identities, total_reputation

    # Calculate the values and the total reputation
    # for the upper triangle of the trapezoid
    def calculate_trapezoid_triangle(self, total_active_rep, active_reputed_ids_len, minimum_rep):
        # Calculate parameters for the curve y = mx + k
        # k: 1'5 * average of the total active reputation without the minimum
        average = total_active_rep / active_reputed_ids_len
        k = 1.5 * (average - minimum_rep)
        # m: negative slope with -k
        m = -k / (active_reputed_ids_len - 1)

        triangle_reputation = []
        total_triangle_reputation = 0
        for i in range(0, active_reputed_ids_len):
            calculated_rep = self.magic_line(i, m, k)
            triangle_reputation.append(calculated_rep)
            total_triangle_reputation += calculated_rep

        return triangle_reputation, total_triangle_reputation

    # Use the trapezoid distribution to calculate eligibility for each of the identities
    # in the ARS based on their reputation ranking
    def trapezoidal_eligibility(self):
        active_reputed_ids, total_active_rep = self.filter_reputed_identities()

        if len(active_reputed_ids) == 0:
            return {}, 0

        # Calculate upper triangle reputation in the trapezoidal eligibility
        minimum_rep = active_reputed_ids[-1].total_reputation
        triangle_reputation, total_triangle_reputation = self.calculate_trapezoid_triangle(total_active_rep, len(active_reputed_ids), minimum_rep)

        # To complete the trapezoid, an offset needs to be added (the rectangle at the base)
        remaining_reputation = total_active_rep - total_triangle_reputation
        offset_reputation = remaining_reputation / len(active_reputed_ids)
        ids_with_extra_rep = remaining_reputation % len(active_reputed_ids)

        eligibility = {}
        for i, (ar_id, rep) in enumerate(zip(active_reputed_ids, triangle_reputation)):
            trapezoid_rep = rep + offset_reputation
            if i < ids_with_extra_rep:
                trapezoid_rep += 1
            eligibility[ar_id.name] = int(trapezoid_rep)

        return eligibility, total_active_rep

    # Calculate actual relative eligibilities adding 1 to each of the identities
    def calculate_eligibilities(self):
        eligibility, total_active_rep = self.trapezoidal_eligibility()

        eligibilities = {}
        for identity in self.identities.keys():
            eligibilities[identity] = (eligibility.get(identity, 0) + 1) / (total_active_rep + len(self.identities))

        return eligibilities

    def select_witnesses(self, eligibilities, approximate_eligibility, num_witnesses, epoch, collateral):
        # Select some witnesses based on eligibility
        for commit_round in range(self.commit_rounds):
            # Find eligible witnesses
            eligibile_identities, insufficient_collateral = [], []
            for identity, eligibility in eligibilities.items():
                if approximate_eligibility:
                    is_eligible = random.random() < eligibility * num_witnesses * (2 ** commit_round)
                else:
                    is_eligible = min([random.random() for nw in range(num_witnesses * (2 ** commit_round))]) < eligibility
                if is_eligible:
                    if self.identities[identity].can_witness(epoch, collateral):
                        eligibile_identities.append(identity)
                    else:
                        insufficient_collateral.append(identity)

            # Remove the surplus in witnesses if necessary
            if len(eligibile_identities) >= num_witnesses:
                chosen_eligibile_identities = random.sample(eligibile_identities, num_witnesses)
                self.logger.debug(f"Chose {chosen_eligibile_identities} identities to solve the data request @ epoch {epoch}")
                self.logger.debug(f"{list(set(eligibile_identities) - set(chosen_eligibile_identities))} identities not chosen to solve the data request @ epoch {epoch}")

                # Mark collateral for all used identities as unavailable
                for identity in chosen_eligibile_identities:
                    self.identities[identity].mark_collateral(epoch, collateral, epoch + self.collateral_locked)

                return True, chosen_eligibile_identities, insufficient_collateral

        return False, eligibile_identities, insufficient_collateral

    def get_ARS_created_reputation(self, new_witnessing_acts, epoch):
        created_reputation = min(new_witnessing_acts, self.total_reputation - self.current_reputation)
        self.current_reputation += created_reputation
        self.logger.debug(f"Created {created_reputation} reputation for {new_witnessing_acts} witnessing acts")
        return created_reputation

    def get_ARS_expired_reputation(self, new_witnessing_acts, epoch):
        self.logger.debug("Expiring reputation")

        self.current_witnessing_acts += new_witnessing_acts

        total_reputation_expired = 0
        for identity in self.identities.values():
            total_reputation_expired += identity.get_expired_reputation(self.current_witnessing_acts - self.reputation_expire, epoch, self.current_witnessing_acts)

        self.logger.debug(f"Reputation expired @ epoch {epoch}: {total_reputation_expired}")

        return total_reputation_expired

    def update_ARS_reputation(self, witnesses, distribute_reputation, epoch):
        self.logger.debug("Updating reputation")

        reputation_gain = int(distribute_reputation / len(witnesses))
        for witness in witnesses:
            self.identities[witness].update_reputation(self.reputation_expire, self.current_witnessing_acts, reputation_gain, epoch)
        self.logger.debug(f"Distributed reputation @ epoch {epoch}: {reputation_gain * len(witnesses)}")

        reputation_remainder = distribute_reputation - int(distribute_reputation / len(witnesses)) * len(witnesses)
        self.logger.debug(f"Remaining reputation @ epoch {epoch}: {reputation_remainder}")

        return reputation_remainder

    def print_ARS(self):
        self.logger.info(f"{'Identity':<44}{'Reputation':>12}{'No collateral':>16}{'Data requests':>16}")
        for identity in sorted(list(self.identities.values()), key=operator.attrgetter("total_reputation"), reverse=True):
            self.logger.info(f"{identity.name:<44}{identity.total_reputation:>12}{identity.eligible_no_collateral:>16}{identity.solved_data_requests:>16}")

    def collect_stats(self, f_stats):
        solved_data_requests, eligible_no_collateral = [], []
        for identity in self.identities.values():
            solved_data_requests.append(identity.solved_data_requests)
            eligible_no_collateral.append(identity.eligible_no_collateral)

        f_stats.write(f"Maximum data requests solved by one identity: {max(solved_data_requests)}\n")
        f_stats.write(f"Maximum data requests eligible but not solved: {max(eligible_no_collateral)}\n\n")

        percentiles = range(10, 100, 10)

        # How many data request solved each identity if he solved at least one
        solved_data_requests_without_zeros = list(filter(lambda x: x != 0, solved_data_requests))
        solved_data_request_percentiles = numpy.percentile(solved_data_requests_without_zeros, percentiles)
        for percentile, solved_data_request_percentile in zip(percentiles, solved_data_request_percentiles):
            f_stats.write(f"Data requests solved per identity ({100 - percentile}%): {solved_data_request_percentile:.2f}\n")
        f_stats.write(f"Average data requests solved per identity: {numpy.average(solved_data_requests_without_zeros):.2f}\n\n")

        # Check how many identities where eligible to solve a data request but could not ignoring identities that never solved a data request
        eligible_no_collateral_filtered = []
        for solved, eligible in zip(solved_data_requests, eligible_no_collateral):
            if solved > 0 or eligible > 0:
                eligible_no_collateral_filtered.append(eligible)
        eligible_no_collateral_percentiles = numpy.percentile(eligible_no_collateral_filtered, percentiles)
        for percentile, eligible_no_collateral_percentile in zip(percentiles, eligible_no_collateral_percentiles):
            f_stats.write(f"Data requests eligible but not solved per identity ({100 - percentile}%): {eligible_no_collateral_percentile:.2f}\n")
        f_stats.write(f"Average data requests eligible but not solved per identity: {numpy.average(eligible_no_collateral_filtered):.2f}\n\n")

    def clear_stats(self):
        for identity in self.identities.values():
            identity.clear_stats()
