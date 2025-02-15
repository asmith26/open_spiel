# Copyright 2019 DeepMind Technologies Ltd. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for open_spiel.python.algorithms.cfr."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools

from absl.testing import absltest
from absl.testing import parameterized
import numpy as np

from open_spiel.python import policy
from open_spiel.python.algorithms import cfr
from open_spiel.python.algorithms import expected_game_score
from open_spiel.python.algorithms import exploitability
import pyspiel

_KUHN_UNIFORM_POLICY = policy.TabularPolicy(pyspiel.load_game("kuhn_poker"))
_LEDUC_UNIFORM_POLICY = policy.TabularPolicy(pyspiel.load_game("leduc_poker"))


class ModuleLevelFunctionTest(absltest.TestCase):

  def test__update_current_policy(self):
    game = pyspiel.load_game("kuhn_poker")
    tabular_policy = policy.TabularPolicy(game)

    cumulative_regrets = np.arange(0, 12 * 2).reshape((12, 2))
    expected_policy = cumulative_regrets / np.sum(
        cumulative_regrets, axis=-1, keepdims=True)
    nodes_indices = {
        u"0": 0,
        u"0pb": 1,
        u"1": 2,
        u"1pb": 3,
        u"2": 4,
        u"2pb": 5,
        u"1p": 6,
        u"1b": 7,
        u"2p": 8,
        u"2b": 9,
        u"0p": 10,
        u"0b": 11,
    }
    # pylint: disable=g-complex-comprehension
    info_state_nodes = {
        key: cfr._InfoStateNode(
            legal_actions=[0, 1],
            cumulative_regret=dict(enumerate(cumulative_regrets[index])),
            cumulative_policy=None) for key, index in nodes_indices.items()
    }
    # pylint: enable=g-complex-comprehension

    cfr._update_current_policy(tabular_policy, info_state_nodes)

    np.testing.assert_array_equal(expected_policy,
                                  tabular_policy.action_probability_array)


class CFRTest(parameterized.TestCase, absltest.TestCase):

  @parameterized.parameters(
      list(itertools.product([True, False], [True, False], [True, False])))
  def test_policy_zero_is_uniform(self, linear_averaging, regret_matching_plus,
                                  alternating_updates):
    # We use Leduc and not Kuhn, because Leduc has illegal actions and Kuhn does
    # not.
    game = pyspiel.load_game("leduc_poker")
    cfr_solver = cfr._CFRSolver(
        game,
        regret_matching_plus=regret_matching_plus,
        linear_averaging=linear_averaging,
        alternating_updates=alternating_updates)

    np.testing.assert_array_equal(
        _LEDUC_UNIFORM_POLICY.action_probability_array,
        cfr_solver.policy().action_probability_array)
    np.testing.assert_array_equal(
        _LEDUC_UNIFORM_POLICY.action_probability_array,
        cfr_solver.average_policy().action_probability_array)

  def test_cfr_kuhn_poker(self):
    game = pyspiel.load_game("kuhn_poker")
    cfr_solver = cfr.CFRSolver(game)
    for _ in range(300):
      cfr_solver.evaluate_and_update_policy()
    average_policy = cfr_solver.average_policy()
    average_policy_values = expected_game_score.policy_value(
        game.new_initial_state(), [average_policy] * 2)
    # 1/18 is the Nash value. See https://en.wikipedia.org/wiki/Kuhn_poker
    np.testing.assert_allclose(
        average_policy_values, [-1 / 18, 1 / 18], atol=1e-3)

  def test_cfr_plus_kuhn_poker(self):
    game = pyspiel.load_game("kuhn_poker")
    cfr_solver = cfr.CFRPlusSolver(game)
    for _ in range(200):
      cfr_solver.evaluate_and_update_policy()
    average_policy = cfr_solver.average_policy()
    average_policy_values = expected_game_score.policy_value(
        game.new_initial_state(), [average_policy] * 2)
    # 1/18 is the Nash value. See https://en.wikipedia.org/wiki/Kuhn_poker
    np.testing.assert_allclose(
        average_policy_values, [-1 / 18, 1 / 18], atol=1e-3)

  @parameterized.parameters(
      list(itertools.product([True, False], [True, False], [True, False])))
  def test_cfr_kuhn_poker_runs_with_multiple_players(self, linear_averaging,
                                                     regret_matching_plus,
                                                     alternating_updates):
    num_players = 3

    game = pyspiel.load_game("kuhn_poker",
                             {"players": pyspiel.GameParameter(num_players)})
    cfr_solver = cfr._CFRSolver(
        game,
        regret_matching_plus=regret_matching_plus,
        linear_averaging=linear_averaging,
        alternating_updates=alternating_updates)
    for _ in range(10):
      cfr_solver.evaluate_and_update_policy()
    average_policy = cfr_solver.average_policy()
    average_policy_values = expected_game_score.policy_value(
        game.new_initial_state(), [average_policy] * num_players)
    del average_policy_values

  @parameterized.parameters(list(itertools.product([False, True])))
  def test_simultaneous_two_step_avg_1b_seq_in_kuhn_poker(
      self, regret_matching_plus):
    num_players = 2
    game = pyspiel.load_game("kuhn_poker",
                             {"players": pyspiel.GameParameter(num_players)})
    cfr_solver = cfr._CFRSolver(
        game,
        regret_matching_plus=regret_matching_plus,
        linear_averaging=False,
        alternating_updates=False)

    def check_avg_policy_is_uniform_random():
      avg_policy = cfr_solver.average_policy()
      for player_info_states in avg_policy.states_per_player:
        for info_state in player_info_states:
          state_policy = avg_policy.policy_for_key(info_state)
          np.testing.assert_allclose(state_policy, [1.0 / len(state_policy)] *
                                     len(state_policy))

    check_avg_policy_is_uniform_random()

    cfr_solver.evaluate_and_update_policy()
    check_avg_policy_is_uniform_random()

    cfr_solver.evaluate_and_update_policy()

    # The acting player in 1b is player 1 and they have not acted before, so
    # the probability this player plays to this information state is 1, and
    # the sequence probability of any action is just the probability of that
    # action given the information state. On the first iteration, this
    # probability is 0.5 for both actions. On the second iteration, the
    # current policy is [0, 1], so the average cumulants should be
    # [0.5, 1.5]. Normalizing this gives the average policy.
    normalization = 0.5 + 0.5 + 1
    np.testing.assert_allclose(cfr_solver.average_policy().policy_for_key("1b"),
                               [0.5 / normalization, (0.5 + 1) / normalization])

  def test_policy(self):
    game = pyspiel.load_game("kuhn_poker")
    solver = cfr.CFRPlusSolver(game)

    tabular_policy = solver.policy()
    self.assertLen(tabular_policy.state_lookup, 12)
    for info_state_str in tabular_policy.state_lookup.keys():
      np.testing.assert_equal(
          np.asarray([0.5, 0.5]), tabular_policy.policy_for_key(info_state_str))

  @parameterized.parameters([
      (pyspiel.load_game("kuhn_poker"), pyspiel.CFRSolver, cfr.CFRSolver),
      (pyspiel.load_game("leduc_poker"), pyspiel.CFRSolver, cfr.CFRSolver),
      (pyspiel.load_game("kuhn_poker"), pyspiel.CFRPlusSolver,
       cfr.CFRPlusSolver),
      (pyspiel.load_game("leduc_poker"), pyspiel.CFRPlusSolver,
       cfr.CFRPlusSolver),
  ])
  def test_cpp_algorithms_identical_to_python_algorithm(self, game, cpp_class,
                                                        python_class):
    cpp_solver = cpp_class(game)
    python_solver = python_class(game)

    for _ in range(5):
      cpp_solver.evaluate_and_update_policy()
      python_solver.evaluate_and_update_policy()

      cpp_avg_policy = cpp_solver.average_policy()
      python_avg_policy = python_solver.average_policy()

      # We do not compare the policy directly as we do not have an easy way to
      # convert one to the other, so we use the exploitability as a proxy.
      cpp_expl = pyspiel.nash_conv(game, cpp_avg_policy)
      python_expl = exploitability.nash_conv(game, python_avg_policy)
      self.assertEqual(cpp_expl, python_expl)


class CFRBRTest(parameterized.TestCase, absltest.TestCase):

  @parameterized.parameters(
      list(itertools.product([True, False], [True, False])))
  def test_policy_zero_is_uniform(self, linear_averaging, regret_matching_plus):
    game = pyspiel.load_game("leduc_poker")
    cfr_solver = cfr.CFRBRSolver(
        game,
        regret_matching_plus=regret_matching_plus,
        linear_averaging=linear_averaging)

    np.testing.assert_array_equal(
        _LEDUC_UNIFORM_POLICY.action_probability_array,
        cfr_solver.policy().action_probability_array)
    np.testing.assert_array_equal(
        _LEDUC_UNIFORM_POLICY.action_probability_array,
        cfr_solver.average_policy().action_probability_array)

  def test_policy_and_average_policy(self):
    game = pyspiel.load_game("kuhn_poker")
    cfrbr_solver = cfr.CFRBRSolver(game)
    for _ in range(300):
      cfrbr_solver.evaluate_and_update_policy()
    average_policy = cfrbr_solver.average_policy()
    average_policy_values = expected_game_score.policy_value(
        game.new_initial_state(), [average_policy] * 2)
    # 1/18 is the Nash value. See https://en.wikipedia.org/wiki/Kuhn_poker
    np.testing.assert_allclose(
        average_policy_values, [-1 / 18, 1 / 18], atol=1e-3)

    cfrbr_solver.policy()


if __name__ == "__main__":
  absltest.main()
