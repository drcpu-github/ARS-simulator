import random
import string

from dataclasses import dataclass
from dataclasses import field

from typing import List
from typing import Tuple

from logger import create_logger

@dataclass
class Identity:
    # Name
    def generate_identity() -> str:
        return "wit1" + "".join([random.choice(string.ascii_lowercase + string.digits) for n in range(38)])
    name: str = field(default_factory=generate_identity)

    # Reputation
    total_reputation: int = 0
    reputation_gains: List[Tuple[int, int]] = field(default_factory=lambda: []) # List of (expiry time, reputation amount) items

    # Balance
    available_collateral: List[Tuple[int, int]] = field(default_factory=lambda: []) # List of (collaterizable epoch, collateral amount) items

    # Statistics
    solved_data_requests: int = 0
    eligible_no_collateral: int = 0

    # Logger
    logger = create_logger(__name__)

    def can_witness(self, epoch, required_collateral):
        collaterizable_balance = sum([collateral[1] for collateral in self.available_collateral if collateral[0] <= epoch])
        if collaterizable_balance >= required_collateral:
            self.logger.debug(f"{self.name} can witness at epoch {epoch}")
            return True

        self.logger.debug(f"{self.name} can witness at epoch {epoch} but does not have enough collateral: {self.available_collateral}")
        self.eligible_no_collateral += 1

        return False

    def mark_collateral(self, epoch, required_collateral, used_until):
        assert self.can_witness(epoch, required_collateral)

        counter, sum_collateral = 0, 0
        while counter < len(self.available_collateral):
            sum_collateral += self.available_collateral[counter][1]
            current_collateral_age = self.available_collateral[counter][0]
            if sum_collateral >= required_collateral:
                # Remove current picked values
                del self.available_collateral[0:counter+1]
                # Add used collateral to the back of the list
                self.available_collateral.append((used_until, required_collateral))
                # Add the remainder back to the head of the list
                if sum_collateral > required_collateral:
                    self.available_collateral.insert(0, (current_collateral_age, sum_collateral - required_collateral))
                self.logger.debug(f"{self.name} updated collateral UTXOs @ epoch {epoch}: {self.available_collateral}")
                break
            counter += 1

        self.solved_data_requests += 1

    def update_reputation(self, reputation_expire, witnessing_acts, reputation, epoch):
        if len(self.reputation_gains) > 0:
            assert self.reputation_gains[0][0] >= witnessing_acts - reputation_expire
        self.reputation_gains.append((witnessing_acts, reputation))
        self.total_reputation = sum(reputation_gain[1] for reputation_gain in self.reputation_gains)
        self.logger.debug(f"{self.name} gained new reputation @ epoch {epoch}, {witnessing_acts}: {self.reputation_gains}")
        self.logger.debug(f"{self.name} new total reputation @ epoch {epoch}, {witnessing_acts}: {self.total_reputation}")

    def get_expired_reputation(self, witness_acts_expired, epoch, total_witness_acts):
        counter, reputation_expired = 0, 0
        while counter < len(self.reputation_gains):
            if self.reputation_gains[counter][0] < witness_acts_expired:
                self.logger.debug(f"{self.name} reputation expired @ epoch {epoch}, {total_witness_acts} ({witness_acts_expired}): {self.reputation_gains[counter]}")
                reputation_expired += self.reputation_gains[counter][1]
            else:
                break
            counter += 1
        del self.reputation_gains[0:counter]

        self.total_reputation = sum(reputation_gain[1] for reputation_gain in self.reputation_gains)
        self.logger.debug(f"{self.name} new total reputation @ epoch {epoch}: {self.total_reputation}")

        return reputation_expired

    def clear_stats(self):
        self.solved_data_requests = 0
        self.eligible_no_collateral = 0
