"""
Template for adapting MAKER to new tasks.

Copy this file and fill in the TODOs to create a MAKER-compatible task.
"""

from typing import List, Any, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class TaskState:
    """
    Represents the current state of your task.

    TODO: Define what information you need to track.

    Examples:
    - For Sudoku: grid state, empty cells
    - For code refactoring: current code, test status
    - For planning: current location, visited nodes
    - For proof: current statement, applied rules
    """
    # TODO: Add your state fields here
    # Example:
    # grid: List[List[int]]
    # empty_cells: List[Tuple[int, int]]
    pass


class Action:
    """
    Represents a single action/step in your task.

    TODO: Define what an action looks like.

    Examples:
    - For Sudoku: (row, col, value)
    - For code refactoring: ("rename_function", old_name, new_name)
    - For planning: ("move", from_node, to_node)
    - For proof: ("apply_rule", rule_name, arguments)
    """

    def __init__(self, *args, **kwargs):
        # TODO: Store action parameters
        pass

    def __str__(self) -> str:
        """String representation for LLM consumption."""
        # TODO: Format action as string
        # Example: "Move disk 1 from A to B"
        return ""

    def __eq__(self, other) -> bool:
        """Check if two actions are equal (needed for voting)."""
        # TODO: Implement equality check
        return False

    def __hash__(self) -> int:
        """Make actions hashable (needed for voting)."""
        # TODO: Implement hash
        return hash(str(self))


class DecomposableTask(ABC):
    """
    Abstract base class for MAKER-compatible tasks.

    Implement all methods marked with @abstractmethod.
    """

    def __init__(self, problem_instance: Any):
        """
        Initialize task with a specific problem instance.

        Args:
            problem_instance: The specific problem to solve
                (e.g., Sudoku grid, code to refactor, graph to search)
        """
        # TODO: Initialize your task state
        self.state = self._initialize_state(problem_instance)
        self.problem = problem_instance
        self.history = []  # Track actions taken

    @abstractmethod
    def _initialize_state(self, problem_instance: Any) -> TaskState:
        """
        Convert problem instance to initial state.

        TODO: Implement state initialization.

        Example for Sudoku:
            return TaskState(
                grid=problem_instance.grid,
                empty_cells=find_empty_cells(problem_instance.grid)
            )
        """
        pass

    @abstractmethod
    def get_current_state(self) -> TaskState:
        """
        Get the current task state.

        Returns:
            Current state representation
        """
        return self.state

    @abstractmethod
    def get_possible_actions(self) -> List[Action]:
        """
        Get all valid actions from current state.

        TODO: Implement action enumeration.

        This is CRITICAL for MAKER - agents vote over this set.

        Examples:
        - Sudoku: Valid numbers for next empty cell
        - Planning: Reachable nodes from current location
        - Code: Valid refactorings for current code smell

        Returns:
            List of valid actions
        """
        pass

    @abstractmethod
    def apply_action(self, action: Action) -> bool:
        """
        Apply an action and update state.

        TODO: Implement action application and validation.

        Args:
            action: The action to apply

        Returns:
            True if action was valid and applied, False otherwise
        """
        pass

    @abstractmethod
    def is_complete(self) -> bool:
        """
        Check if task is finished.

        TODO: Implement completion check.

        Examples:
        - Sudoku: All cells filled and constraints satisfied
        - Planning: Reached goal location
        - Code: All refactorings applied and tests pass

        Returns:
            True if task is complete
        """
        pass

    def get_progress(self) -> float:
        """
        Get completion percentage (0.0 to 1.0).

        TODO: Implement progress measurement.

        This helps with:
        - Progress tracking
        - Detecting when stuck
        - Adaptive k selection

        Returns:
            Progress as a float between 0.0 and 1.0
        """
        # Default: based on history length
        if not hasattr(self, 'expected_steps'):
            return 0.0
        return min(1.0, len(self.history) / self.expected_steps)

    @abstractmethod
    def format_for_llm(self) -> str:
        """
        Format current state for LLM consumption.

        TODO: Create minimal, clear state representation.

        CRITICAL: Include ONLY what's needed for the next step!
        - Too much context: wastes tokens, confuses agent
        - Too little context: agent can't decide

        Good format:
        - Current state summary
        - Available actions
        - Constraints/rules
        - Progress indicator

        Returns:
            String representation for LLM prompt
        """
        pass

    def validate_solution(self) -> Tuple[bool, str]:
        """
        Validate the complete solution.

        TODO: Implement solution validation.

        This runs after task completion to verify correctness.

        Returns:
            (is_valid, error_message)
        """
        if not self.is_complete():
            return False, "Task not complete"
        return True, "Solution valid"

    def estimate_steps(self) -> int:
        """
        Estimate number of steps needed to complete task.

        TODO: Implement step estimation.

        Used to compute voting margin k.

        Examples:
        - Sudoku: Number of empty cells
        - Planning: Shortest path length estimate
        - Code: Number of refactoring targets

        Returns:
            Estimated number of steps
        """
        return 100  # Default placeholder

    def undo_action(self) -> bool:
        """
        Undo the last action (optional but recommended).

        TODO: Implement undo if needed for backtracking.

        Returns:
            True if undo successful
        """
        if not self.history:
            return False

        last_action = self.history.pop()
        # TODO: Revert state changes from last_action
        return True

    def get_state_hash(self) -> int:
        """
        Get hash of current state (optional but recommended).

        TODO: Implement state hashing for caching.

        Used to:
        - Detect repeated states
        - Cache voting results
        - Implement cycle detection

        Returns:
            Hash of current state
        """
        return hash(str(self.state))


# ============================================================================
# TODO: Implement your specific task by inheriting from DecomposableTask
# ============================================================================

class YourSpecificTask(DecomposableTask):
    """
    TODO: Replace this with your task name and implementation.

    Example: SudokuTask, CodeRefactoringTask, RoutePlanningTask
    """

    def _initialize_state(self, problem_instance: Any) -> TaskState:
        # TODO: Implement
        raise NotImplementedError("TODO: Initialize state from problem instance")

    def get_possible_actions(self) -> List[Action]:
        # TODO: Implement
        raise NotImplementedError("TODO: Return list of valid actions")

    def apply_action(self, action: Action) -> bool:
        # TODO: Implement
        raise NotImplementedError("TODO: Apply action and update state")

    def is_complete(self) -> bool:
        # TODO: Implement
        raise NotImplementedError("TODO: Check if task is complete")

    def format_for_llm(self) -> str:
        # TODO: Implement
        raise NotImplementedError("TODO: Format state for LLM")


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    """
    TODO: Add usage example for your task.
    """

    # Example structure:
    # 1. Create problem instance
    # problem = YourProblemType(...)

    # 2. Create task
    # task = YourSpecificTask(problem)

    # 3. Configure MAKER
    # from maker import MAKER, MAKERConfig
    # config = MAKERConfig(
    #     model="gpt-4o-mini",
    #     k=task.estimate_steps() and compute_k(...),
    #     verbose=True
    # )

    # 4. Solve
    # maker = MAKER(config, task=task)
    # success, solution, stats = maker.solve()

    print("TODO: Implement task and add usage example")
