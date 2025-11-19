"""
Example: Solving Sudoku using Generalized MAKER

Demonstrates how to adapt MAKER to a new task (Sudoku).
"""

from typing import List, Tuple, Optional, Any
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


class SudokuAction:
    """Represents placing a number in a Sudoku cell."""

    def __init__(self, row: int, col: int, num: int):
        self.row = row
        self.col = col
        self.num = num

    def __str__(self):
        return f"({self.row},{self.col})={self.num}"

    def __eq__(self, other):
        return (isinstance(other, SudokuAction) and
                self.row == other.row and
                self.col == other.col and
                self.num == other.num)

    def __hash__(self):
        return hash((self.row, self.col, self.num))

    def __repr__(self):
        return str(self)


class SudokuTask(DecomposableTask):
    """Sudoku task adapted for MAKER."""

    def __init__(self, initial_grid: List[List[int]]):
        """
        Initialize Sudoku puzzle.

        Args:
            initial_grid: 9x9 grid where 0 represents empty cell
        """
        self.grid = [row[:] for row in initial_grid]  # Deep copy
        self.initial_grid = [row[:] for row in initial_grid]
        self.history = []

    def get_current_state(self) -> List[List[int]]:
        """Get current grid state."""
        return self.grid

    def _find_next_empty_cell(self) -> Optional[Tuple[int, int]]:
        """Find next empty cell (0 value)."""
        for row in range(9):
            for col in range(9):
                if self.grid[row][col] == 0:
                    return (row, col)
        return None

    def _is_valid_placement(self, row: int, col: int, num: int) -> bool:
        """Check if placing num at (row, col) is valid."""

        # Check row
        if num in self.grid[row]:
            return False

        # Check column
        if num in [self.grid[r][col] for r in range(9)]:
            return False

        # Check 3x3 box
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for r in range(box_row, box_row + 3):
            for c in range(box_col, box_col + 3):
                if self.grid[r][c] == num:
                    return False

        return True

    def get_possible_actions(self) -> List[SudokuAction]:
        """Get valid numbers for next empty cell."""
        next_cell = self._find_next_empty_cell()
        if next_cell is None:
            return []

        row, col = next_cell
        valid_actions = []

        for num in range(1, 10):
            if self._is_valid_placement(row, col, num):
                valid_actions.append(SudokuAction(row, col, num))

        return valid_actions

    def apply_action(self, action: Any) -> bool:
        """Place number in cell if valid."""
        if not isinstance(action, SudokuAction):
            return False

        # Validate
        if not self._is_valid_placement(action.row, action.col, action.num):
            return False

        # Apply
        self.grid[action.row][action.col] = action.num
        self.history.append(action)
        return True

    def is_complete(self) -> bool:
        """Check if all cells filled."""
        return self._find_next_empty_cell() is None

    def _format_grid(self) -> str:
        """Pretty print grid."""
        lines = []
        for i, row in enumerate(self.grid):
            if i % 3 == 0 and i != 0:
                lines.append("------+-------+------")

            row_str = ""
            for j, val in enumerate(row):
                if j % 3 == 0 and j != 0:
                    row_str += "| "
                row_str += str(val) if val != 0 else "."
                row_str += " "
            lines.append(row_str.strip())

        return "\n".join(lines)

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        next_cell = self._find_next_empty_cell()
        if next_cell is None:
            return "Grid complete!"

        row, col = next_cell
        valid_actions = self.get_possible_actions()
        valid_nums = [a.num for a in valid_actions]

        # Get constraints
        row_values = [n for n in self.grid[row] if n != 0]
        col_values = [self.grid[r][col] for r in range(9) if self.grid[r][col] != 0]

        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        box_values = []
        for r in range(box_row, box_row + 3):
            for c in range(box_col, box_col + 3):
                if self.grid[r][c] != 0:
                    box_values.append(self.grid[r][c])

        return f"""You are solving Sudoku. This is step {step_num}.

Current grid:
{self._format_grid()}

Next cell to fill: Row {row + 1}, Column {col + 1}
Valid numbers: {valid_nums}

Current constraints:
- Row {row + 1} has: {row_values}
- Column {col + 1} has: {col_values}
- 3x3 box has: {box_values}

Rules:
- Each row must have 1-9 exactly once
- Each column must have 1-9 exactly once
- Each 3x3 box must have 1-9 exactly once

Which number should go in Row {row + 1}, Column {col + 1}?
Respond ONLY with the number (one of: {valid_nums}). No explanation."""

    def parse_action(self, response: str) -> Optional[SudokuAction]:
        """Parse LLM response into action."""
        # Extract number from response
        import re
        numbers = re.findall(r'\d', response)

        if not numbers:
            return None

        try:
            num = int(numbers[0])
            if num < 1 or num > 9:
                return None

            # Get current empty cell
            next_cell = self._find_next_empty_cell()
            if next_cell is None:
                return None

            row, col = next_cell
            return SudokuAction(row, col, num)

        except ValueError:
            return None

    def get_progress(self) -> float:
        """Calculate completion percentage."""
        total_cells = 81
        filled = sum(1 for row in self.grid for val in row if val != 0)
        return filled / total_cells

    def estimate_steps(self) -> int:
        """Estimate steps needed (number of empty cells)."""
        return sum(1 for row in self.grid for val in row if val == 0)

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate completed Sudoku."""
        if not self.is_complete():
            return False, "Grid not complete"

        # Check all rows
        for row in range(9):
            if sorted(self.grid[row]) != list(range(1, 10)):
                return False, f"Row {row + 1} invalid"

        # Check all columns
        for col in range(9):
            column = [self.grid[row][col] for row in range(9)]
            if sorted(column) != list(range(1, 10)):
                return False, f"Column {col + 1} invalid"

        # Check all boxes
        for box_row in range(0, 9, 3):
            for box_col in range(0, 9, 3):
                box = []
                for r in range(box_row, box_row + 3):
                    for c in range(box_col, box_col + 3):
                        box.append(self.grid[r][c])
                if sorted(box) != list(range(1, 10)):
                    return False, f"Box at ({box_row},{box_col}) invalid"

        return True, "Sudoku solved correctly!"


# ============================================================================
# Example Usage
# ============================================================================

def create_easy_sudoku():
    """Create an easy Sudoku puzzle."""
    return [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]


def create_very_easy_sudoku():
    """Create a very easy Sudoku (only 5 empty cells)."""
    return [
        [5, 3, 4, 6, 7, 8, 9, 1, 2],
        [6, 7, 2, 1, 9, 5, 3, 4, 8],
        [1, 9, 8, 3, 4, 2, 5, 6, 7],
        [8, 5, 9, 7, 6, 1, 4, 2, 3],
        [4, 2, 6, 8, 5, 3, 7, 9, 1],
        [7, 1, 3, 9, 2, 4, 8, 5, 6],
        [9, 6, 0, 5, 3, 7, 2, 8, 4],  # (6, 2) = 1
        [2, 8, 7, 4, 1, 9, 6, 3, 5],
        [3, 4, 5, 2, 8, 6, 0, 7, 9]   # (8, 6) = 1
    ]


if __name__ == "__main__":
    print("Sudoku Solver using Generalized MAKER")
    print("=" * 60)

    # Create puzzle (use very easy for quick demo)
    grid = create_very_easy_sudoku()

    # Create task
    task = SudokuTask(grid)

    print("\nInitial puzzle:")
    print(task._format_grid())
    print(f"\nEmpty cells: {task.estimate_steps()}")

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=None,  # Auto-compute based on difficulty
        task_type="sudoku",
        verbose=True,
        max_response_length=50,  # Sudoku answers are short
    )

    # Add custom validator for Sudoku
    def validate_sudoku_response(response: str, context: dict) -> Tuple[bool, str]:
        """Validate response is a single digit 1-9."""
        import re
        numbers = re.findall(r'\d', response)
        if not numbers:
            return False, "No number found in response"
        if len(numbers) > 1:
            return False, "Multiple numbers in response"
        num = int(numbers[0])
        if num < 1 or num > 9:
            return False, f"Number {num} out of range (1-9)"
        return True, ""

    config.custom_validators = [validate_sudoku_response]

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    # Display results
    if success:
        print("\n" + "=" * 60)
        print("SOLUTION:")
        print("=" * 60)
        print(task._format_grid())
        print(f"\nSteps taken: {len(actions)}")
        print(f"Actions: {actions}")
    else:
        print("\nFailed to solve puzzle")

    print("\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
