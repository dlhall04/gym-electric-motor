import numpy as np

from ..core import RewardFunction
from ..utils import set_state_array
import warnings


class WeightedSumOfErrors(RewardFunction):
    """
    Reward Function that calculates the reward as the weighted sum of errors with a certain power.

    .. math:
        `reward = - reward_weights * (abs(state - reference)/ state_length) ** reward_power `
    .. math:
        ` limit\_violation\_reward = -1 / (1 - \gamma)`

    | state_length[i] = 1 for states with positive values only.
    | state_length[i] = 2 for states with positive and negative values.
    """

    def __init__(self, reward_weights=None, normed=False, observed_states=None, gamma=0.9, reward_power=1, **__):
        """
        Args:
            reward_weights(dict/list/ndarray(float)): Dict mapping state names to reward_weights, 0 otherwise.
                Or an array with the reward_weights on the position of the state_names.
            normed(bool): If True, the reward weights will be normalized to 1.
            observed_states(list(str)): List of state names of which the limit are observed. Default: no observation.
            gamma(float): Discount factor for the reward punishment. Should equal agents' discount factor gamma.
            reward_power(dict/list(float)/float): Reward power for each of the systems states.
        """
        self._n = reward_power
        self._reward_weights = reward_weights
        self._state_length = None
        self._normed = normed
        self._gamma = gamma
        super().__init__(observed_states)

    def set_modules(self, physical_system, reference_generator):
        super().set_modules(physical_system, reference_generator)
        self._state_length = self._physical_system.state_space.high - self._physical_system.state_space.low
        self._n = set_state_array(self._n, self._physical_system.state_names)
        referenced_states = reference_generator.referenced_states
        if self._reward_weights is None:
            reward_weights = dict.fromkeys(
                np.array(physical_system.state_names)[referenced_states],
                1/len(np.array(physical_system.state_names)[referenced_states])
            )
        else:
            reward_weights = self._reward_weights
        self._reward_weights = set_state_array(reward_weights, self._physical_system.state_names)
        if sum(self._reward_weights) == 0:
            warnings.warn("All reward weights sum up to zero", Warning, stacklevel=2)
        rw_sum = sum(self._reward_weights)
        if self._normed:
            self._reward_weights /= rw_sum
            self.reward_range = (-1, 0)
        else:
            self.reward_range = (-rw_sum, 0)

    def _limit_violation_reward(self, state):
        return self.reward_range[0] / (1 - self._gamma)

    def _reward(self, state, reference, *_):
        return -np.sum(self._reward_weights * (abs(state - reference) / self._state_length)**self._n)


class ShiftedWeightedSumOfErrors(WeightedSumOfErrors):
    """
    Weighted Sum of Errors shifted by the maximum negative reward to obtain rewards in the positive range.

    .. math::
        reward = max\_reward - reward\_weights * (abs(state - reference)/ state\_length) ** reward\_power
    .. math::
        limit~violation~reward = 0`

    | state_length[i] = 1 for states with positive values only.
    | state_length[i] = 2 for states with positive and negative values.

    """

    def _reward(self, state, reference, *_):
        return self.reward_range[1] + super()._reward(state, reference)

    def _limit_violation_reward(self, state):
        return 0.0

    def set_modules(self, physical_system, reference_generator):
        super().set_modules(physical_system, reference_generator)
        self.reward_range = (0, -self.reward_range[0])
