"""
Towers of Hanoi game implementation for testing MAKER concepts.

The Towers of Hanoi puzzle has:
- 3 pegs (A, B, C)
- N disks of different sizes
- Goal: Move all disks from source peg to target peg
- Rules:
  1. Only one disk can be moved at a time
  2. A disk can only be placed on top of a larger disk
  3. Only the top disk of a stack can be moved
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class GameState:
    """Represents the current state of the Towers of Hanoi game."""
    pegs: dict[str, List[int]]  # Maps peg name to list of disks (bottom to top)
    num_disks: int
    source: str = 'A'
    target: str = 'C'
    auxiliary: str = 'B'

    def __init__(self, num_disks: int, source: str = 'A', target: str = 'C', auxiliary: str = 'B'):
        """Initialize game with all disks on source peg."""
        self.num_disks = num_disks
        self.source = source
        self.target = target
        self.auxiliary = auxiliary
        self.pegs = {
            source: list(range(num_disks, 0, -1)),  # [n, n-1, ..., 2, 1]
            target: [],
            auxiliary: []
        }

    def copy(self) -> 'GameState':
        """Create a deep copy of the game state."""
        new_state = GameState.__new__(GameState)
        new_state.num_disks = self.num_disks
        new_state.source = self.source
        new_state.target = self.target
        new_state.auxiliary = self.auxiliary
        new_state.pegs = {
            peg: disks.copy() for peg, disks in self.pegs.items()
        }
        return new_state

    def is_valid_move(self, from_peg: str, to_peg: str) -> bool:
        """Check if a move is valid according to game rules."""
        if from_peg not in self.pegs or to_peg not in self.pegs:
            return False

        if not self.pegs[from_peg]:  # No disk to move
            return False

        if not self.pegs[to_peg]:  # Empty peg
            return True

        # Can only place smaller disk on larger disk
        return self.pegs[from_peg][-1] < self.pegs[to_peg][-1]

    def apply_move(self, from_peg: str, to_peg: str) -> bool:
        """Apply a move if valid. Returns True if successful."""
        if not self.is_valid_move(from_peg, to_peg):
            return False

        disk = self.pegs[from_peg].pop()
        self.pegs[to_peg].append(disk)
        return True

    def is_solved(self) -> bool:
        """Check if the puzzle is solved."""
        return (len(self.pegs[self.target]) == self.num_disks and
                not self.pegs[self.source] and
                not self.pegs[self.auxiliary])

    def __str__(self) -> str:
        """Pretty print the game state."""
        lines = []
        max_height = max(len(disks) for disks in self.pegs.values())

        for level in range(max_height - 1, -1, -1):
            line_parts = []
            for peg_name in [self.source, self.auxiliary, self.target]:
                disks = self.pegs[peg_name]
                if level < len(disks):
                    disk_size = disks[level]
                    line_parts.append(f"{disk_size:2d}")
                else:
                    line_parts.append("  ")
            lines.append(" | ".join(line_parts))

        lines.append("-" * (len(lines[0]) if lines else 0))
        lines.append(" | ".join([self.source, self.auxiliary, self.target]))
        return "\n".join(lines)

    def get_state_string(self) -> str:
        """Get a compact string representation of the state."""
        return f"{self.source}:{self.pegs[self.source]}, {self.auxiliary}:{self.pegs[self.auxiliary]}, {self.target}:{self.pegs[self.target]}"


def parse_move(move_str: str) -> Optional[Tuple[str, str]]:
    """
    Parse a move string like 'A->B' or 'A to B' into (from_peg, to_peg).
    Returns None if parsing fails.
    """
    move_str = move_str.strip().upper()

    # Try different formats
    for separator in ['->', ' TO ', ' to ', ',', ' ']:
        if separator in move_str:
            parts = move_str.split(separator)
            if len(parts) >= 2:
                from_peg = parts[0].strip()
                to_peg = parts[1].strip()

                # Extract single letter
                if from_peg and to_peg:
                    from_peg = from_peg[0] if from_peg[0].isalpha() else None
                    to_peg = to_peg[0] if to_peg[0].isalpha() else None

                    if from_peg and to_peg:
                        return (from_peg, to_peg)

    # Try single format like "AB" or "A B"
    letters = [c for c in move_str if c.isalpha()]
    if len(letters) == 2:
        return (letters[0], letters[1])

    return None


def get_optimal_solution(num_disks: int, source: str = 'A', target: str = 'C',
                        auxiliary: str = 'B') -> List[Tuple[str, str]]:
    """
    Generate the optimal solution for Towers of Hanoi.
    Returns list of moves as (from_peg, to_peg) tuples.
    """
    moves = []

    def hanoi(n: int, src: str, tgt: str, aux: str):
        if n == 1:
            moves.append((src, tgt))
        else:
            hanoi(n - 1, src, aux, tgt)
            moves.append((src, tgt))
            hanoi(n - 1, aux, tgt, src)

    hanoi(num_disks, source, target, auxiliary)
    return moves


def verify_solution(num_disks: int, moves: List[Tuple[str, str]]) -> Tuple[bool, str]:
    """
    Verify if a sequence of moves solves the puzzle.
    Returns (success, error_message).
    """
    state = GameState(num_disks)

    for i, (from_peg, to_peg) in enumerate(moves):
        if not state.apply_move(from_peg, to_peg):
            return False, f"Invalid move at step {i + 1}: {from_peg}->{to_peg}. State: {state.get_state_string()}"

    if not state.is_solved():
        return False, f"Puzzle not solved. Final state: {state.get_state_string()}"

    return True, "Solution verified successfully!"


if __name__ == "__main__":
    # Test the implementation
    print("Testing Towers of Hanoi implementation\n")

    # Test with 3 disks
    num_disks = 3
    print(f"Solving {num_disks}-disk puzzle:")

    state = GameState(num_disks)
    print(f"\nInitial state:\n{state}\n")

    solution = get_optimal_solution(num_disks)
    print(f"Optimal solution requires {len(solution)} moves:")
    print(f"Expected: {2**num_disks - 1} moves\n")

    for i, (from_peg, to_peg) in enumerate(solution, 1):
        state.apply_move(from_peg, to_peg)
        print(f"Move {i}: {from_peg}->{to_peg}")
        if i <= 5 or i == len(solution):  # Show first few and last
            print(state)
            print()

    print(f"Solved: {state.is_solved()}")

    # Verify solution
    success, message = verify_solution(num_disks, solution)
    print(f"\nVerification: {message}")

    # Test move parsing
    print("\n" + "="*50)
    print("Testing move parsing:")
    test_moves = ["A->B", "A to B", "AB", "A B", "a->c", "B,C"]
    for move_str in test_moves:
        parsed = parse_move(move_str)
        print(f"'{move_str}' -> {parsed}")
