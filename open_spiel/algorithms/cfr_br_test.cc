// Copyright 2019 DeepMind Technologies Ltd. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "open_spiel/algorithms/cfr_br.h"

#include "open_spiel/algorithms/expected_returns.h"
#include "open_spiel/algorithms/tabular_exploitability.h"
#include "open_spiel/games/kuhn_poker.h"
#include "open_spiel/games/leduc_poker.h"

namespace open_spiel {
namespace algorithms {
namespace {

// Checks that the expected value of the policy is close to the Nash values.
// Assumes two-player zero-sum games.
void CheckNashValues(const Game& game, const Policy& policy,
                     double first_player_nash_value, double tolerance) {
  const std::vector<double> game_value =
      ExpectedReturns(*game.NewInitialState(), policy, -1);
  SPIEL_CHECK_EQ(2, game_value.size());
  SPIEL_CHECK_FLOAT_NEAR(game_value[0], first_player_nash_value, tolerance);
  SPIEL_CHECK_FLOAT_NEAR(game_value[1], -first_player_nash_value, tolerance);
}

void CFRBRTest_KuhnPoker() {
  std::unique_ptr<Game> game = LoadGame("kuhn_poker");
  CFRBRSolver solver(*game);
  for (int i = 0; i < 300; i++) {
    solver.EvaluateAndUpdatePolicy();
  }
  const std::unique_ptr<Policy> average_policy = solver.AveragePolicy();
  // 1/18 is the Nash value. See https://en.wikipedia.org/wiki/Kuhn_poker
  CheckNashValues(*game, *average_policy, -1.0 / 18, 0.001);
  SPIEL_CHECK_LE(Exploitability(*game, *average_policy), 0.05);
}

void CFRBRTest_LeducPoker() {
  std::unique_ptr<Game> game = LoadGame("leduc_poker");
  CFRBRSolver solver(*game);
  int num_iters = 100;
  for (int i = 0; i < num_iters; i++) {
    solver.EvaluateAndUpdatePolicy();
  }
  const std::unique_ptr<Policy> average_policy = solver.AveragePolicy();
  double nash_conv = NashConv(*game, *average_policy);
  std::cout << "Iters " << num_iters << ", nash_conv = "
            << nash_conv << std::endl;
}

}  // namespace
}  // namespace algorithms
}  // namespace open_spiel

namespace algorithms = open_spiel::algorithms;

int main(int argc, char** argv) {
  algorithms::CFRBRTest_KuhnPoker();
  algorithms::CFRBRTest_LeducPoker();
}
