"""
Rubik's Cube implementation with state management and move mechanics.

Cube representation:
- 3×3×3 cube with 6 faces
- Each face has 9 stickers
- Standard notation: U (Up), D (Down), L (Left), R (Right), F (Front), B (Back)
- Each face can rotate: clockwise (90°), 180°, counter-clockwise (270°)
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import copy


class Face(Enum):
    """Cube faces."""
    U = "U"  # Up (top)
    D = "D"  # Down (bottom)
    L = "L"  # Left
    R = "R"  # Right
    F = "F"  # Front
    B = "B"  # Back


class Rotation(Enum):
    """Rotation types."""
    CW = 90    # Clockwise
    HALF = 180  # 180 degrees
    CCW = 270   # Counter-clockwise


@dataclass
class Move:
    """Represents a single cube move."""
    face: Face
    rotation: Rotation

    def __str__(self):
        if self.rotation == Rotation.CW:
            return self.face.value
        elif self.rotation == Rotation.HALF:
            return f"{self.face.value}2"
        else:  # CCW
            return f"{self.face.value}'"

    def __hash__(self):
        return hash((self.face, self.rotation))

    def __eq__(self, other):
        return (isinstance(other, Move) and
                self.face == other.face and
                self.rotation == other.rotation)

    @staticmethod
    def from_string(move_str: str) -> 'Move':
        """Parse move from string like 'U', 'R2', 'F'' """
        move_str = move_str.strip().upper()

        if move_str.endswith("2"):
            face = Face(move_str[0])
            rotation = Rotation.HALF
        elif move_str.endswith("'"):
            face = Face(move_str[0])
            rotation = Rotation.CCW
        else:
            face = Face(move_str[0])
            rotation = Rotation.CW

        return Move(face, rotation)


class RubiksCube:
    """
    Rubik's Cube implementation.

    State representation:
    - Each face is a 3×3 array
    - Colors: W(hite), Y(ellow), R(ed), O(range), B(lue), G(reen)
    - Standard color scheme:
      * U (Up): White
      * D (Down): Yellow
      * L (Left): Orange
      * R (Right): Red
      * F (Front): Green
      * B (Back): Blue
    """

    def __init__(self):
        """Initialize solved cube."""
        # Each face is a 3×3 list
        self.faces = {
            Face.U: [['W']*3 for _ in range(3)],  # White (top)
            Face.D: [['Y']*3 for _ in range(3)],  # Yellow (bottom)
            Face.L: [['O']*3 for _ in range(3)],  # Orange (left)
            Face.R: [['R']*3 for _ in range(3)],  # Red (right)
            Face.F: [['G']*3 for _ in range(3)],  # Green (front)
            Face.B: [['B']*3 for _ in range(3)],  # Blue (back)
        }

    def copy(self) -> 'RubiksCube':
        """Create a deep copy of the cube."""
        new_cube = RubiksCube()
        new_cube.faces = {
            face: [row[:] for row in grid]
            for face, grid in self.faces.items()
        }
        return new_cube

    def apply_move(self, move: Move) -> 'RubiksCube':
        """Apply a move to the cube (returns self for chaining)."""
        # Rotate the face itself
        self._rotate_face(move.face, move.rotation)

        # Update adjacent faces
        self._update_adjacent_faces(move.face, move.rotation)

        return self

    def _rotate_face(self, face: Face, rotation: Rotation):
        """Rotate a face clockwise by specified amount."""
        grid = self.faces[face]

        if rotation == Rotation.CW:
            # Rotate 90° clockwise
            self.faces[face] = [
                [grid[2][0], grid[1][0], grid[0][0]],
                [grid[2][1], grid[1][1], grid[0][1]],
                [grid[2][2], grid[1][2], grid[0][2]]
            ]
        elif rotation == Rotation.HALF:
            # Rotate 180°
            self._rotate_face(face, Rotation.CW)
            self._rotate_face(face, Rotation.CW)
        else:  # CCW
            # Rotate 270° = 3× 90° clockwise
            self._rotate_face(face, Rotation.CW)
            self._rotate_face(face, Rotation.CW)
            self._rotate_face(face, Rotation.CW)

    def _update_adjacent_faces(self, face: Face, rotation: Rotation):
        """Update adjacent faces after rotating a face."""
        if rotation == Rotation.HALF:
            # For 180°, apply twice
            self._update_adjacent_faces(face, Rotation.CW)
            self._update_adjacent_faces(face, Rotation.CW)
            return
        elif rotation == Rotation.CCW:
            # For CCW, apply 3 times
            for _ in range(3):
                self._update_adjacent_faces(face, Rotation.CW)
            return

        # Handle CW rotation for each face
        if face == Face.U:
            temp = self.faces[Face.F][0][:]
            self.faces[Face.F][0] = self.faces[Face.R][0][:]
            self.faces[Face.R][0] = self.faces[Face.B][0][:]
            self.faces[Face.B][0] = self.faces[Face.L][0][:]
            self.faces[Face.L][0] = temp

        elif face == Face.D:
            temp = self.faces[Face.F][2][:]
            self.faces[Face.F][2] = self.faces[Face.L][2][:]
            self.faces[Face.L][2] = self.faces[Face.B][2][:]
            self.faces[Face.B][2] = self.faces[Face.R][2][:]
            self.faces[Face.R][2] = temp

        elif face == Face.L:
            temp = [self.faces[Face.U][i][0] for i in range(3)]
            for i in range(3):
                self.faces[Face.U][i][0] = self.faces[Face.B][2-i][2]
            for i in range(3):
                self.faces[Face.B][2-i][2] = self.faces[Face.D][i][0]
            for i in range(3):
                self.faces[Face.D][i][0] = self.faces[Face.F][i][0]
            for i in range(3):
                self.faces[Face.F][i][0] = temp[i]

        elif face == Face.R:
            temp = [self.faces[Face.U][i][2] for i in range(3)]
            for i in range(3):
                self.faces[Face.U][i][2] = self.faces[Face.F][i][2]
            for i in range(3):
                self.faces[Face.F][i][2] = self.faces[Face.D][i][2]
            for i in range(3):
                self.faces[Face.D][i][2] = self.faces[Face.B][2-i][0]
            for i in range(3):
                self.faces[Face.B][2-i][0] = temp[i]

        elif face == Face.F:
            temp = self.faces[Face.U][2][:]
            for i in range(3):
                self.faces[Face.U][2][i] = self.faces[Face.L][2-i][2]
            for i in range(3):
                self.faces[Face.L][i][2] = self.faces[Face.D][0][i]
            for i in range(3):
                self.faces[Face.D][0][i] = self.faces[Face.R][2-i][0]
            for i in range(3):
                self.faces[Face.R][i][0] = temp[i]

        elif face == Face.B:
            temp = self.faces[Face.U][0][:]
            for i in range(3):
                self.faces[Face.U][0][i] = self.faces[Face.R][i][2]
            for i in range(3):
                self.faces[Face.R][i][2] = self.faces[Face.D][2][2-i]
            for i in range(3):
                self.faces[Face.D][2][i] = self.faces[Face.L][i][0]
            for i in range(3):
                self.faces[Face.L][2-i][0] = temp[i]

    def is_solved(self) -> bool:
        """Check if cube is in solved state."""
        for face, grid in self.faces.items():
            # All stickers on a face should be the same color
            first_color = grid[0][0]
            for row in grid:
                for color in row:
                    if color != first_color:
                        return False
        return True

    def get_state_string(self) -> str:
        """Get string representation of cube state (for hashing)."""
        state = []
        for face in [Face.U, Face.D, Face.L, Face.R, Face.F, Face.B]:
            for row in self.faces[face]:
                state.extend(row)
        return ''.join(state)

    def __str__(self) -> str:
        """Pretty print the cube."""
        u = self.faces[Face.U]
        d = self.faces[Face.D]
        l = self.faces[Face.L]
        r = self.faces[Face.R]
        f = self.faces[Face.F]
        b = self.faces[Face.B]

        lines = []
        # Top face (U)
        for row in u:
            lines.append("      " + " ".join(row))

        # Middle row (L F R B)
        for i in range(3):
            line = " ".join(l[i]) + " " + " ".join(f[i]) + " " + " ".join(r[i]) + " " + " ".join(b[i])
            lines.append(line)

        # Bottom face (D)
        for row in d:
            lines.append("      " + " ".join(row))

        return "\n".join(lines)

    @staticmethod
    def scramble(num_moves: int = 20) -> 'RubiksCube':
        """Create a scrambled cube with random moves."""
        import random
        cube = RubiksCube()
        moves = []

        all_moves = [
            Move(face, rotation)
            for face in Face
            for rotation in Rotation
        ]

        for _ in range(num_moves):
            move = random.choice(all_moves)
            cube.apply_move(move)
            moves.append(str(move))

        print(f"Scramble: {' '.join(moves)}")
        return cube


def get_all_possible_moves() -> List[Move]:
    """Get all 18 possible moves."""
    return [
        Move(face, rotation)
        for face in Face
        for rotation in Rotation
    ]


def parse_move_sequence(sequence: str) -> List[Move]:
    """Parse move sequence like 'R U R' U2 F' into Move objects."""
    moves = []
    for move_str in sequence.split():
        try:
            moves.append(Move.from_string(move_str))
        except (ValueError, KeyError):
            print(f"Warning: Could not parse move '{move_str}'")
    return moves


def apply_move_sequence(cube: RubiksCube, sequence: str) -> RubiksCube:
    """Apply a sequence of moves to a cube."""
    moves = parse_move_sequence(sequence)
    for move in moves:
        cube.apply_move(move)
    return cube


if __name__ == "__main__":
    print("="*60)
    print("Rubik's Cube Implementation Test")
    print("="*60)

    # Test 1: Create solved cube
    print("\n1. Solved cube:")
    cube = RubiksCube()
    print(cube)
    print(f"Is solved: {cube.is_solved()}")

    # Test 2: Apply some moves
    print("\n2. After applying R U R' U':")
    cube = RubiksCube()
    apply_move_sequence(cube, "R U R' U'")
    print(cube)
    print(f"Is solved: {cube.is_solved()}")

    # Test 3: Undo moves
    print("\n3. Undo (apply U R U' R'):")
    apply_move_sequence(cube, "U R U' R'")
    print(cube)
    print(f"Is solved: {cube.is_solved()}")

    # Test 4: Scramble
    print("\n4. Scrambled cube (20 random moves):")
    cube = RubiksCube.scramble(20)
    print(cube)
    print(f"Is solved: {cube.is_solved()}")

    # Test 5: All possible moves
    print(f"\n5. Total possible moves: {len(get_all_possible_moves())}")
    print("Move notation:")
    for i, move in enumerate(get_all_possible_moves()[:6], 1):
        print(f"  {i}. {move}")
    print("  ...")
