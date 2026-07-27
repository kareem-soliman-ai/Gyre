"""Meta-bandit L7 controller (machinery F1 from the formal-machinery taxonomy).

Treats each loop-controller as an arm and learns which one gives the best
net value, without making any world-model assumptions.  This is the
principled alternative to ``AdaptiveEVController``, which requires a
specifiable world model and is brittle under misspecification.

Implementation:
    UCB1-bandit over the registered controllers.  Each controller is an
    arm.  The reward for playing an arm is the realised net value of its
    route decision in the current context.  Reward = stakes - cost of the
    route action, where the cost is taken from ControlContext.  A
    controller is played when the meta-bandit selects it, and its route
    decision is returned as the ExitReason for this iteration.

    The meta-bandit is *not* a meta-controller that runs other controllers.
    It is a controller that selects from a menu of controllers and returns
    the selected controller's route decision.  The outer scaffold runs
    the meta-bandit, which selects a controller, and that controller is
    applied to the current verdicts.

    In practice, the fitler is that UCB1 visits each controller once before
    exploiting.  After the exploration period, the controller with the
    highest average reward is selected greedily.

    The meta-bandit is stateless (it does not own the outer scaffold's state)
    and carries its own cross-iteration state (visit counts, running rewards)
    for the arms.  ``reset()`` clears the bandit's state for an independent
    episode.

    The meta-bandit does NOT "know" what the underlying controllers do.  It
    only knows which controller produced which reward.  That is its
    advantage: it makes no world-model assumption.

Parameters
----------
controllers : list[MetaController]
    The controllers to bandit over.  Each is treated as an arm.
UCB1 : use the UCB1 algorithm for exploration/exploitation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

from gyre.control import ControlContext, MetaController
from gyre.interfaces import ExitReason, LoopVerdict


@dataclass
class _ArmState:
    """State for a single arm in the bandit."""
    controller: MetaController
    visits: int = 0
    total_reward: float = 0.0
    avg_reward: float = 0.0

    def update(self, reward: float) -> None:
        self.visits += 1
        self.total_reward += reward
        self.avg_reward = self.total_reward / self.visits


class MetaBanditController:
    """L7 meta-controller: a UCB1 bandit over a menu of controllers.

    It watches the same verdicts a single controller would see, and selects
    the controller whose past rewards are highest (adjusted for
    exploration).  No world-model assumption.

    Parameters
    ----------
    controllers : list[MetaController]
        The trainable arms (controllers).  Must be non-empty.
    exploration_coefficient : float
        The UCB1 constant.  Default 1.414 (sqrt(2)).  Lower = exploit more;
        higher = explore more.
    reward_weights : dict[str, float]
        Mapping from ExitReason value to a reward multiplier.  Defaults to
        a uniform assignment.  Override to reflect that, say, CONTINUE is
        more valuable than REFRAME.
    """

    name = "meta-bandit"

    def __init__(
        self,
        controllers: list[MetaController] | None = None,
        *default_controllers: MetaController,
        exploration_coefficient: float = 1.414,
        reward_weights: dict[str, float] | None = None,
    ) -> None:
        if controllers is not None:
            self._arms: list[_ArmState] = [_ArmState(c) for c in controllers]
        elif default_controllers:
            self._arms = [_ArmState(c) for c in default_controllers]
        else:
            self._arms = []
        if not self._arms:
            raise ValueError("MetaBanditController needs at least one controller (arm)")
        self._exploration_coefficient = exploration_coefficient
        self._reward_weights = reward_weights or {}
        self._total_steps = 0
        self._last_arm_index: int = 0

    def _ucb1_score(self, arm: _ArmState) -> float:
        """UCB1 score for an arm: avg_reward + C * sqrt(log(total_steps) / arm.visits)."""
        if arm.visits == 0:
            return float("inf")  # never visited → infinite score
        return arm.avg_reward + self._exploration_coefficient * math.sqrt(
            math.log(self._total_steps) / arm.visits
        )

    def _compute_reward(
        self, route: ExitReason, context: ControlContext
    ) -> float:
        """Compute the realised reward for a decision.

        Reward = stakes - cost of the chosen route action.  An action with
        lower cost gives higher reward.  A CONTINUE action costs step_cost.
        A REFRAME costs reframe_cost.  An ESCALATE costs escalation_cost.
        ABANDON costs 0.  RUPTURE costs 0 (pre-empted).
        """
        routing_costs = {
            ExitReason.CONTINUE: context.step_cost,
            ExitReason.REFRAME: context.reframe_cost,
            ExitReason.ESCALATE: context.escalation_cost,
            ExitReason.ABANDON: 0.0,
            ExitReason.RUPTURE: 0.0,
        }
        return context.stakes - routing_costs.get(route, 0.0)

    def route(
        self, verdicts: Sequence[LoopVerdict], context: ControlContext
    ) -> ExitReason:
        """Select the best controller (UCB1) and return its route.

        The meta-bandit does NOT run all controllers.  It selects ONE
        and returns its route.  This is the advantage of the bandit:
        we pay the cost of running only one controller, not all.

        After each visit, the controller's reward is computed and stored.
        This is the standard multi-armed bandit loop.
        """
        # Inspect for RUPTURE (which must be fast)
        for v in verdicts:
            if v.exit_reason is ExitReason.RUPTURE:
                return ExitReason.RUPTURE

        if self._total_steps == 0:
            # Cold start: UCB1 will visit each arm once before exploiting
            pass

        self._total_steps += 1

        # Select the arm with the highest UCB1 score
        best_index = max(range(len(self._arms)), key=lambda i: self._ucb1_score(self._arms[i]))
        self._last_arm_index = best_index

        # Play the arm
        route = self._arms[best_index].controller.route(verdicts, context)

        # Compute reward and update the arm
        reward = self._compute_reward(route, context)
        self._arms[best_index].update(reward)

        return route

    def reset(self) -> None:
        """Reset all arms and counters for a new episode."""
        self._total_steps = 0
        for arm in self._arms:
            arm.visits = 0
            arm.total_reward = 0.0
            arm.avg_reward = 0.0
        # Also reset each underlying controller
        for arm in self._arms:
            arm.controller.reset()

    def arm_report(self) -> list[dict]:
        """Return a summary of each arm: controller name, visits, avg_reward,
        instant reward.  Useful for debugging and for bench tests."""
        return [
            {
                "name": arm.controller.name,
                "visits": arm.visits,
                "avg_reward": arm.avg_reward,
                "total_reward": arm.total_reward,
            }
            for arm in self._arms
        ]

    def with_controllers(self, controllers: list[MetaController]) -> "MetaBanditController":
        """Return a new MetaBanditController with a different menu of controllers."""
        return MetaBanditController(
            controllers=controllers,
            exploration_coefficient=self._exploration_coefficient,
            reward_weights=self._reward_weights,
        )


def register_controllers(register: Callable[[str, Callable[[], MetaController]], None]) -> None:
    """Auto-discovered by control/proprietary/__init__.register_all."""
    from gyre.control import FixedRouteController
    from gyre.interfaces import ExitReason

    register(
        "meta-bandit:default",
        lambda: MetaBanditController(controllers=[
            FixedRouteController(ExitReason.REFRAME),
            FixedRouteController(ExitReason.ESCALATE),
            FixedRouteController(ExitReason.ABANDON),
        ]),
    )
    register(
        "meta-bandit:l5-informed",
        lambda: MetaBanditController(controllers=[
            FixedRouteController(ExitReason.REFRAME),
            FixedRouteController(ExitReason.ESCALATE),
            # L5RouteController is not stateless; it needs to be instantiated fresh.
            # It is NOT included here because the bandit needs to be able to run
            # each arm independently of the others.
        ]),
    )