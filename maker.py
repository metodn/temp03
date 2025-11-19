"""
MAKER: Massively Decomposed Agentic Processes for solving long-task LLM problems.

Implements:
1. Maximal Agentic Decomposition (MAD)
2. First-to-ahead-by-k Voting
3. Red-Flagging (Anomaly Detection)
"""

import os
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from collections import Counter
import re
import math

try:
    from litellm import completion
except ImportError:
    print("Warning: litellm not installed. Install with: pip install litellm")
    completion = None

from towers_of_hanoi import GameState, parse_move, verify_solution


@dataclass
class MAKERConfig:
    """Configuration for MAKER system."""
    model: str = "gpt-4o-mini"  # Model to use (as per paper, cheaper models work better)
    k: int = 3  # Voting margin (grows with ln(steps))
    max_response_length: int = 200  # For red-flagging
    min_response_length: int = 1  # For red-flagging
    temperature: float = 0.7  # Sampling temperature
    max_resamples: int = 5  # Max resamples if red-flagged
    verbose: bool = True  # Print progress

    @staticmethod
    def compute_k_for_steps(num_steps: int) -> int:
        """Compute voting margin k based on number of steps (logarithmic growth)."""
        if num_steps <= 10:
            return 2
        elif num_steps <= 100:
            return 3
        elif num_steps <= 1000:
            return 4
        else:
            # k grows as Θ(ln s)
            return max(3, int(math.log(num_steps)) + 1)


class RedFlagger:
    """Implements red-flagging for anomaly detection."""

    def __init__(self, config: MAKERConfig):
        self.config = config

    def should_flag(self, response: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if a response should be red-flagged.
        Returns (should_flag, reason).
        """
        # Check length
        if len(response) > self.config.max_response_length:
            return True, f"Response too long ({len(response)} chars)"

        if len(response) < self.config.min_response_length:
            return True, f"Response too short ({len(response)} chars)"

        # Check if response is empty or whitespace only
        if not response.strip():
            return True, "Empty response"

        # Check for common failure patterns
        failure_patterns = [
            "I cannot",
            "I can't",
            "I don't know",
            "I'm sorry",
            "I apologize",
            "Error:",
            "ERROR:",
        ]

        response_lower = response.lower()
        for pattern in failure_patterns:
            if pattern.lower() in response_lower:
                return True, f"Failure pattern detected: {pattern}"

        # Check if response contains expected format for move
        # Should contain something like "A->B" or "A to B"
        if not any(char in response.upper() for char in ['A', 'B', 'C']):
            return True, "No peg names (A, B, C) found in response"

        # Check for overly verbose responses (likely hallucination)
        if response.count('\n') > 5:
            return True, "Response too verbose (multiple lines)"

        return False, ""


class VotingAgent:
    """Individual agent that votes on next move."""

    def __init__(self, config: MAKERConfig, agent_id: int = 0):
        self.config = config
        self.agent_id = agent_id
        self.red_flagger = RedFlagger(config)

    def get_next_move(self, state: GameState, step_num: int) -> Optional[Tuple[str, str]]:
        """
        Get the next move for the given state.
        Returns None if unable to get valid response after max resamples.
        """
        if completion is None:
            raise RuntimeError("litellm not installed")

        # Create prompt for single-step decision
        prompt = self._create_prompt(state, step_num)

        for attempt in range(self.config.max_resamples):
            try:
                response = completion(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=100,  # Keep responses short
                )

                response_text = response.choices[0].message.content.strip()

                # Red-flagging check
                should_flag, reason = self.red_flagger.should_flag(
                    response_text,
                    {"state": state, "step": step_num}
                )

                if should_flag:
                    if self.config.verbose:
                        print(f"  [Agent {self.agent_id}] Red-flagged (attempt {attempt + 1}): {reason}")
                    continue

                # Parse the move
                move = parse_move(response_text)
                if move is None:
                    if self.config.verbose:
                        print(f"  [Agent {self.agent_id}] Failed to parse: '{response_text}'")
                    continue

                # Validate move is legal
                if not state.is_valid_move(move[0], move[1]):
                    if self.config.verbose:
                        print(f"  [Agent {self.agent_id}] Invalid move: {move[0]}->{move[1]}")
                    continue

                return move

            except Exception as e:
                if self.config.verbose:
                    print(f"  [Agent {self.agent_id}] Error: {e}")
                continue

        return None

    def _create_prompt(self, state: GameState, step_num: int) -> str:
        """Create a minimal prompt for single-step decision."""
        return f"""You are solving Towers of Hanoi. This is step {step_num}.

Current state:
{state}

Pegs: {state.get_state_string()}

Goal: Move all disks from {state.source} to {state.target}.

What is the next move? Respond ONLY with the move in format: FROM->TO (e.g., "A->B")
Do not explain. Just give the move."""


class FirstToAheadByKVoting:
    """Implements first-to-ahead-by-k voting mechanism."""

    def __init__(self, config: MAKERConfig):
        self.config = config

    def vote_on_move(self, state: GameState, step_num: int) -> Optional[Tuple[str, str]]:
        """
        Get consensus on next move using first-to-ahead-by-k voting.
        Returns the winning move or None if consensus cannot be reached.
        """
        votes: Dict[Tuple[str, str], int] = Counter()
        agents_sampled = 0
        max_agents = 50  # Safety limit

        while agents_sampled < max_agents:
            # Create agent and get vote
            agent = VotingAgent(self.config, agent_id=agents_sampled)
            move = agent.get_next_move(state, step_num)

            if move is not None:
                votes[move] += 1

                # Check if any move is ahead by k
                if votes:
                    sorted_votes = votes.most_common()
                    if len(sorted_votes) >= 1:
                        leader_move, leader_count = sorted_votes[0]
                        second_count = sorted_votes[1][1] if len(sorted_votes) > 1 else 0

                        if leader_count - second_count >= self.config.k:
                            if self.config.verbose:
                                print(f"  Consensus reached after {agents_sampled + 1} agents: {leader_move[0]}->{leader_move[1]} ({leader_count} votes)")
                            return leader_move

            agents_sampled += 1

        # No consensus reached
        if votes:
            # Return most common
            leader_move = votes.most_common(1)[0][0]
            if self.config.verbose:
                print(f"  No strong consensus after {max_agents} agents. Using most common: {leader_move[0]}->{leader_move[1]}")
            return leader_move

        return None


class MAKER:
    """Main MAKER system for solving long-task LLM problems."""

    def __init__(self, config: MAKERConfig):
        self.config = config
        self.voting = FirstToAheadByKVoting(config)
        self.stats = {
            "total_steps": 0,
            "total_agent_calls": 0,
            "red_flags": 0,
            "failed_steps": 0,
        }

    def solve_towers_of_hanoi(self, num_disks: int) -> Tuple[bool, List[Tuple[str, str]], Dict]:
        """
        Solve Towers of Hanoi using MAKER approach.
        Returns (success, moves, stats).
        """
        state = GameState(num_disks)
        moves = []
        expected_moves = 2**num_disks - 1

        print(f"\n{'='*60}")
        print(f"MAKER: Solving {num_disks}-disk Towers of Hanoi")
        print(f"Expected moves: {expected_moves}")
        print(f"Voting margin k: {self.config.k}")
        print(f"Model: {self.config.model}")
        print(f"{'='*60}\n")

        print(f"Initial state:\n{state}\n")

        step = 0
        while not state.is_solved() and step < expected_moves * 2:  # Safety limit
            step += 1
            self.stats["total_steps"] = step

            if self.config.verbose:
                print(f"\n--- Step {step}/{expected_moves} ---")

            # Use voting to determine next move
            move = self.voting.vote_on_move(state, step)

            if move is None:
                print(f"ERROR: Could not determine move at step {step}")
                self.stats["failed_steps"] += 1
                return False, moves, self.stats

            # Apply move
            success = state.apply_move(move[0], move[1])
            if not success:
                print(f"ERROR: Invalid move {move[0]}->{move[1]} at step {step}")
                self.stats["failed_steps"] += 1
                return False, moves, self.stats

            moves.append(move)

            if self.config.verbose:
                print(f"Applied: {move[0]}->{move[1]}")
                if step <= 5 or step % 10 == 0 or state.is_solved():
                    print(f"\n{state}\n")

        # Verify solution
        if state.is_solved():
            print(f"\n{'='*60}")
            print(f"SUCCESS! Solved in {len(moves)} moves")
            print(f"{'='*60}\n")

            # Verify correctness
            is_valid, message = verify_solution(num_disks, moves)
            print(f"Verification: {message}\n")

            return is_valid, moves, self.stats
        else:
            print(f"\nFAILED: Could not solve within {expected_moves * 2} steps")
            return False, moves, self.stats


if __name__ == "__main__":
    # Example usage
    print("MAKER System - Towers of Hanoi Solver")
    print("=" * 60)

    # Configure MAKER
    num_disks = 3
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=MAKERConfig.compute_k_for_steps(2**num_disks - 1),
        verbose=True
    )

    # Create MAKER instance
    maker = MAKER(config)

    # Solve
    success, moves, stats = maker.solve_towers_of_hanoi(num_disks)

    # Print statistics
    print("\nStatistics:")
    print(f"  Total steps: {stats['total_steps']}")
    print(f"  Success: {success}")
    print(f"\nMoves sequence:")
    for i, (from_peg, to_peg) in enumerate(moves, 1):
        print(f"  {i}. {from_peg}->{to_peg}")
