"""
Generalized MAKER implementation that works with any DecomposableTask.

This is the framework from the paper, abstracted to work with any sequential task.
"""

import math
from typing import List, Tuple, Optional, Dict, Any, Callable
from dataclasses import dataclass
from collections import Counter
from abc import ABC, abstractmethod

try:
    from litellm import completion
except ImportError:
    completion = None


@dataclass
class MAKERConfig:
    """Configuration for generalized MAKER system."""
    model: str = "gpt-4o-mini"
    k: Optional[int] = None  # Auto-compute if None
    temperature: float = 0.7
    max_agents_per_vote: int = 50
    verbose: bool = True

    # Red-flagging defaults
    max_response_length: int = 300
    min_response_length: int = 1
    max_resamples: int = 5

    # Task-specific settings
    task_type: str = "generic"
    custom_validators: List[Callable] = None

    def __post_init__(self):
        if self.custom_validators is None:
            self.custom_validators = []


class DecomposableTask(ABC):
    """
    Abstract base for tasks compatible with MAKER.

    Implement these methods to make your task MAKER-compatible.
    """

    @abstractmethod
    def get_current_state(self) -> Any:
        """Get current task state."""
        pass

    @abstractmethod
    def get_possible_actions(self) -> List[Any]:
        """Get valid actions from current state."""
        pass

    @abstractmethod
    def apply_action(self, action: Any) -> bool:
        """Apply action and update state. Return success."""
        pass

    @abstractmethod
    def is_complete(self) -> bool:
        """Check if task is complete."""
        pass

    @abstractmethod
    def format_for_agent(self, step_num: int) -> str:
        """Format state as prompt for voting agent."""
        pass

    def parse_action(self, response: str) -> Optional[Any]:
        """
        Parse LLM response into an action.
        Override for task-specific parsing.
        """
        return response.strip()

    def get_progress(self) -> float:
        """Get completion percentage (0.0 to 1.0)."""
        return 0.0

    def estimate_steps(self) -> int:
        """Estimate total steps needed."""
        return 100

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate final solution."""
        if self.is_complete():
            return True, "Solution complete"
        return False, "Task incomplete"


class RedFlagger:
    """Red-flagging for anomaly detection."""

    def __init__(self, config: MAKERConfig, task: DecomposableTask):
        self.config = config
        self.task = task

    def should_flag(self, response: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if response should be red-flagged."""

        # Length checks
        if len(response) > self.config.max_response_length:
            return True, f"Too long ({len(response)} chars)"

        if len(response) < self.config.min_response_length:
            return True, f"Too short ({len(response)} chars)"

        # Empty check
        if not response.strip():
            return True, "Empty response"

        # Failure patterns
        failure_patterns = [
            "i cannot", "i can't", "i don't know",
            "i'm sorry", "i apologize", "error:", "invalid:"
        ]

        response_lower = response.lower()
        for pattern in failure_patterns:
            if pattern in response_lower:
                return True, f"Failure pattern: {pattern}"

        # Custom validators
        for validator in self.config.custom_validators:
            is_valid, reason = validator(response, context)
            if not is_valid:
                return True, reason

        return False, ""


class VotingAgent:
    """Individual agent that votes on next action."""

    def __init__(self, config: MAKERConfig, task: DecomposableTask, agent_id: int):
        self.config = config
        self.task = task
        self.agent_id = agent_id
        self.red_flagger = RedFlagger(config, task)

    def get_vote(self, step_num: int) -> Optional[Any]:
        """Get this agent's vote for next action."""

        if completion is None:
            raise RuntimeError("litellm not installed")

        # Get prompt from task
        prompt = self.task.format_for_agent(step_num)

        # Try multiple times if red-flagged
        for attempt in range(self.config.max_resamples):
            try:
                response = completion(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=200
                )

                response_text = response.choices[0].message.content.strip()

                # Red-flag check
                should_flag, reason = self.red_flagger.should_flag(
                    response_text,
                    {"step": step_num, "state": self.task.get_current_state()}
                )

                if should_flag:
                    if self.config.verbose:
                        print(f"  [Agent {self.agent_id}] Red-flagged: {reason}")
                    continue

                # Parse action
                action = self.task.parse_action(response_text)
                if action is None:
                    if self.config.verbose:
                        print(f"  [Agent {self.agent_id}] Failed to parse: '{response_text}'")
                    continue

                # Validate action is in possible set
                possible = self.task.get_possible_actions()
                if action not in possible:
                    if self.config.verbose:
                        print(f"  [Agent {self.agent_id}] Action not in possible set: {action}")
                    continue

                return action

            except Exception as e:
                if self.config.verbose:
                    print(f"  [Agent {self.agent_id}] Error: {e}")
                continue

        return None


class FirstToAheadByKVoting:
    """First-to-ahead-by-k voting mechanism."""

    def __init__(self, config: MAKERConfig, task: DecomposableTask):
        self.config = config
        self.task = task

    def vote(self, step_num: int) -> Optional[Any]:
        """
        Run voting to determine next action.

        Returns winning action or None if no consensus.
        """
        votes: Dict[Any, int] = Counter()
        agents_sampled = 0
        k = self.config.k

        while agents_sampled < self.config.max_agents_per_vote:
            # Create agent and get vote
            agent = VotingAgent(self.config, self.task, agents_sampled)
            action = agent.get_vote(step_num)

            if action is not None:
                votes[action] += 1

                # Check for k-vote lead
                if votes:
                    sorted_votes = votes.most_common()
                    leader, leader_count = sorted_votes[0]
                    second_count = sorted_votes[1][1] if len(sorted_votes) > 1 else 0

                    if leader_count - second_count >= k:
                        if self.config.verbose:
                            print(f"  Consensus after {agents_sampled + 1} agents: {leader} ({leader_count} votes)")
                        return leader

            agents_sampled += 1

        # No strong consensus - return most common
        if votes:
            leader = votes.most_common(1)[0][0]
            if self.config.verbose:
                print(f"  No strong consensus. Using most common: {leader}")
            return leader

        return None


class GeneralizedMAKER:
    """
    Generalized MAKER implementation.

    Works with any DecomposableTask.
    """

    def __init__(self, config: MAKERConfig, task: DecomposableTask):
        self.config = config
        self.task = task
        self.voting = FirstToAheadByKVoting(config, task)

        # Auto-compute k if not provided
        if self.config.k is None:
            estimated_steps = task.estimate_steps()
            self.config.k = self._compute_k(estimated_steps)

        self.stats = {
            "total_steps": 0,
            "total_agents": 0,
            "failed_steps": 0,
            "red_flags": 0
        }

    @staticmethod
    def _compute_k(num_steps: int) -> int:
        """Compute voting margin based on expected steps (logarithmic)."""
        if num_steps <= 10:
            return 2
        elif num_steps <= 100:
            return 3
        elif num_steps <= 1000:
            return 4
        else:
            return max(3, int(math.log(num_steps)) + 1)

    def solve(self) -> Tuple[bool, List[Any], Dict]:
        """
        Solve the task using MAKER approach.

        Returns:
            (success, action_history, stats)
        """
        print(f"\n{'='*60}")
        print(f"Generalized MAKER Solver")
        print(f"Task type: {self.config.task_type}")
        print(f"Expected steps: {self.task.estimate_steps()}")
        print(f"Voting margin k: {self.config.k}")
        print(f"Model: {self.config.model}")
        print(f"{'='*60}\n")

        action_history = []
        step = 0
        max_steps = self.task.estimate_steps() * 3  # Safety limit

        while not self.task.is_complete() and step < max_steps:
            step += 1
            self.stats["total_steps"] = step

            if self.config.verbose:
                progress = self.task.get_progress()
                print(f"\n--- Step {step} (Progress: {progress:.1%}) ---")

            # Vote on next action
            action = self.voting.vote(step)

            if action is None:
                print(f"ERROR: Could not determine action at step {step}")
                self.stats["failed_steps"] += 1
                break

            # Apply action
            success = self.task.apply_action(action)

            if not success:
                print(f"ERROR: Failed to apply action at step {step}: {action}")
                self.stats["failed_steps"] += 1
                break

            action_history.append(action)

            if self.config.verbose:
                print(f"Applied: {action}")

        # Check completion
        if self.task.is_complete():
            print(f"\n{'='*60}")
            print(f"SUCCESS! Completed in {step} steps")
            print(f"{'='*60}\n")

            # Validate solution
            is_valid, message = self.task.validate_solution()
            print(f"Validation: {message}\n")

            return is_valid, action_history, self.stats
        else:
            print(f"\nFAILED: Could not complete within {max_steps} steps")
            return False, action_history, self.stats


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("Generalized MAKER Framework")
    print("="*60)
    print("\nThis is the base implementation.")
    print("To use it, create a DecomposableTask and pass it to GeneralizedMAKER.\n")
    print("See TASK_TEMPLATE.py for how to create your own task.")
    print("See EXAMPLES.md for concrete examples.\n")
    print("Example:")
    print("""
    from maker_base import GeneralizedMAKER, MAKERConfig
    from my_task import MyTask

    # Create task instance
    task = MyTask(problem_instance)

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=None,  # Auto-compute
        task_type="my_task",
        verbose=True
    )

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()
    """)
