"""
MAKER-based Rubik's Cube Solver

This solver uses the MAKER approach to solve Rubik's Cube:
- Each step = choosing one move
- Voting determines best move
- Heuristics guide the search
- Progressive solving (edges → corners → orientation)

Note: This is NOT an optimal solver like Kociemba's algorithm.
MAKER explores moves using LLM voting and heuristics.
"""

from typing import List, Tuple, Optional, Any, Dict
from dataclasses import dataclass
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig
from rubiks_cube import RubiksCube, Move, get_all_possible_moves, Face


@dataclass
class CubeMoveAction:
    """Represents applying a move to the cube."""
    move: Move
    estimated_quality: float  # 0-1, higher is better

    def __str__(self):
        return f"{self.move} (quality: {self.estimated_quality:.2f})"

    def __eq__(self, other):
        return isinstance(other, CubeMoveAction) and self.move == other.move

    def __hash__(self):
        return hash(self.move)

    def __repr__(self):
        return str(self)


class RubiksCubeSolverTask(DecomposableTask):
    """
    Solve Rubik's Cube using MAKER approach.

    Strategy:
    - Use heuristics to evaluate cube state
    - Vote on next move among top candidates
    - Track state to avoid loops
    - Progressive solving approach
    """

    def __init__(self, initial_cube: RubiksCube, max_moves: int = 100):
        """
        Initialize Rubik's Cube solving task.

        Args:
            initial_cube: The scrambled cube to solve
            max_moves: Maximum moves allowed
        """
        self.initial_state = initial_cube.get_state_string()
        self.cube = initial_cube.copy()
        self.max_moves = max_moves

        # Tracking
        self.move_history = []
        self.visited_states = {self.initial_state}
        self.best_score = self._evaluate_cube(self.cube)

        # Statistics
        self.states_explored = 1

    def _evaluate_cube(self, cube: RubiksCube) -> float:
        """
        Evaluate how close cube is to solved state.
        Returns score 0.0 (unsolved) to 1.0 (solved).
        """
        if cube.is_solved():
            return 1.0

        total_correct = 0
        total_stickers = 54  # 6 faces × 9 stickers

        # Count correctly positioned stickers
        for face in Face:
            face_grid = cube.faces[face]
            center_color = face_grid[1][1]  # Center never moves

            for row in face_grid:
                for color in row:
                    if color == center_color:
                        total_correct += 1

        return total_correct / total_stickers

    def _count_solved_faces(self, cube: RubiksCube) -> int:
        """Count number of completely solved faces."""
        count = 0
        for face in Face:
            grid = cube.faces[face]
            first_color = grid[0][0]
            if all(color == first_color for row in grid for color in row):
                count += 1
        return count

    def get_current_state(self) -> RubiksCube:
        """Get current cube state."""
        return self.cube

    def get_possible_actions(self) -> List[CubeMoveAction]:
        """
        Get promising moves to try.
        Uses heuristics to filter to top candidates.
        """
        if self.is_complete():
            return []

        all_moves = get_all_possible_moves()
        actions = []

        # Evaluate each possible move
        for move in all_moves:
            # Try the move on a copy
            test_cube = self.cube.copy()
            test_cube.apply_move(move)

            state_str = test_cube.get_state_string()

            # Skip if we've seen this state before (avoid loops)
            if state_str in self.visited_states:
                continue

            # Evaluate resulting state
            score = self._evaluate_cube(test_cube)

            actions.append(CubeMoveAction(move, score))

        # Sort by quality (best first)
        actions.sort(key=lambda a: a.estimated_quality, reverse=True)

        # Return top candidates for voting
        return actions[:6]  # Top 6 moves for voting

    def apply_action(self, action: Any) -> bool:
        """Apply a move to the cube."""
        if not isinstance(action, CubeMoveAction):
            return False

        # Apply move
        self.cube.apply_move(action.move)

        # Track state
        state_str = self.cube.get_state_string()
        self.visited_states.add(state_str)
        self.move_history.append(action.move)
        self.states_explored += 1

        # Update best score
        current_score = self._evaluate_cube(self.cube)
        if current_score > self.best_score:
            self.best_score = current_score

        return True

    def is_complete(self) -> bool:
        """Check if cube is solved or max moves reached."""
        return self.cube.is_solved() or len(self.move_history) >= self.max_moves

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()

        if not possible:
            return "No valid moves available (all lead to visited states)"

        current_score = self._evaluate_cube(self.cube)
        solved_faces = self._count_solved_faces(self.cube)

        # Format move options
        move_info = []
        for i, action in enumerate(possible, 1):
            improvement = (action.estimated_quality - current_score) * 100
            move_info.append(
                f"  {i}. {action.move:6s} → score: {action.estimated_quality:.2f} "
                f"({improvement:+.1f}%)"
            )

        return f"""You are solving a Rubik's Cube. Move {step_num}/{self.max_moves}.

Current state:
  Score: {current_score:.2f} (0.0 = unsolved, 1.0 = solved)
  Solved faces: {solved_faces}/6
  Best score seen: {self.best_score:.2f}
  States explored: {self.states_explored}

Move notation:
  U/D/L/R/F/B = faces (Up, Down, Left, Right, Front, Back)
  Move without symbol = 90° clockwise
  Move with ' = 90° counter-clockwise
  Move with 2 = 180°

Recent moves: {' '.join(str(m) for m in self.move_history[-5:])}

Top move candidates (ordered by estimated improvement):
{chr(10).join(move_info)}

Which move should be applied?
Respond with just the number (1-{len(possible)}). No explanation."""

    def parse_action(self, response: str) -> Optional[CubeMoveAction]:
        """Parse LLM response into action."""
        import re
        numbers = re.findall(r'\d+', response)

        if not numbers:
            return None

        try:
            choice = int(numbers[0])
            possible = self.get_possible_actions()

            if 1 <= choice <= len(possible):
                return possible[choice - 1]
        except (ValueError, IndexError):
            pass

        return None

    def get_progress(self) -> float:
        """Calculate solving progress."""
        return self._evaluate_cube(self.cube)

    def estimate_steps(self) -> int:
        """Estimate steps needed."""
        return self.max_moves

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate cube is solved."""
        if not self.cube.is_solved():
            return False, f"Cube not solved (score: {self._evaluate_cube(self.cube):.2f})"

        return True, (
            f"Cube solved in {len(self.move_history)} moves!\n"
            f"Solution: {' '.join(str(m) for m in self.move_history)}\n"
            f"States explored: {self.states_explored}"
        )


if __name__ == "__main__":
    print("="*80)
    print("Rubik's Cube MAKER Solver")
    print("="*80)

    # Create a scrambled cube
    print("\nScrambling cube with 10 random moves...")
    cube = RubiksCube.scramble(10)

    print("\nInitial state:")
    print(cube)
    print(f"Is solved: {cube.is_solved()}")

    # Create solving task
    task = RubiksCubeSolverTask(initial_cube=cube, max_moves=50)

    initial_score = task._evaluate_cube(cube)
    print(f"\nInitial score: {initial_score:.2f}")
    print(f"Solved faces: {task._count_solved_faces(cube)}/6")

    # Configure MAKER
    print("\nConfiguring MAKER solver...")
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=2,  # Lower k for exploration
        task_type="rubiks_cube",
        verbose=False,  # Too much output for cube solving
        max_response_length=50
    )

    # Add custom validator
    def validate_move_choice(response: str, context: dict) -> Tuple[bool, str]:
        """Validate response is a number."""
        import re
        numbers = re.findall(r'\d+', response)
        if not numbers:
            return False, "No number found in response"
        try:
            num = int(numbers[0])
            if num < 1 or num > 6:
                return False, f"Number {num} out of range (1-6)"
            return True, ""
        except ValueError:
            return False, "Invalid number format"

    config.custom_validators = [validate_move_choice]

    print("\n" + "="*80)
    print("Solving with MAKER...")
    print("="*80)

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    print("\n" + "="*80)
    print("Results")
    print("="*80)

    if success and task.cube.is_solved():
        print("\n✓ Cube SOLVED!")
        print(f"\nSolution ({len(task.move_history)} moves):")
        print(' '.join(str(m) for m in task.move_history))

        print(f"\nFinal state:")
        print(task.cube)

        # Verify solution
        is_valid, message = task.validate_solution()
        print(f"\nValidation: {message}")
    else:
        print("\n✗ Could not solve cube within move limit")
        print(f"Final score: {task._evaluate_cube(task.cube):.2f}")
        print(f"Solved faces: {task._count_solved_faces(task.cube)}/6")
        print(f"Moves tried: {len(task.move_history)}")

    print(f"\nMAKER Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\nCube-specific statistics:")
    print(f"  States explored: {task.states_explored}")
    print(f"  Best score achieved: {task.best_score:.2f}")

    print("\n" + "="*80)
    print("Note: MAKER uses heuristic-guided exploration.")
    print("For optimal solutions (<20 moves), use Kociemba's algorithm.")
    print("MAKER demonstrates how voting can guide complex search problems.")
    print("="*80)
