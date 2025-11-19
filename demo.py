#!/usr/bin/env python3
"""
Simple demonstration of MAKER system solving Towers of Hanoi.

This script shows how to use MAKER to solve a small Towers of Hanoi puzzle
and demonstrates the key concepts from the paper.
"""

import os
import sys
from maker import MAKER, MAKERConfig
from towers_of_hanoi import get_optimal_solution


def check_prerequisites():
    """Check if prerequisites are met."""
    # Check litellm
    try:
        import litellm
        print("✓ litellm installed")
    except ImportError:
        print("✗ litellm not installed")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        return False

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("✗ OPENAI_API_KEY not set")
        print("\nPlease set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("\nOr use another provider supported by LiteLLM:")
        print("  https://docs.litellm.ai/docs/")
        return False

    print("✓ OPENAI_API_KEY set")
    return True


def demonstrate_concepts():
    """Demonstrate key concepts from the MAKER paper."""
    print("\n" + "="*80)
    print("MAKER SYSTEM DEMONSTRATION")
    print("Concepts from: 'Solving a Million-Step LLM Task with Zero Errors'")
    print("="*80)

    print("\n📚 KEY CONCEPTS:")
    print("\n1. Maximal Agentic Decomposition (MAD)")
    print("   - Break task into single-step subtasks")
    print("   - Each agent makes one simple decision")
    print("   - Reduces cumulative error propagation")

    print("\n2. First-to-Ahead-by-k Voting")
    print("   - Multiple agents vote on each step")
    print("   - Continue until one option leads by k votes")
    print("   - Voting margin k grows logarithmically: Θ(ln s)")

    print("\n3. Red-Flagging")
    print("   - Detect and discard unreliable responses")
    print("   - Check for: length, format, failure patterns")
    print("   - Reduces correlated errors")

    print("\n" + "="*80)


def run_demo():
    """Run the demonstration."""
    print("\n🎯 DEMONSTRATION: Solving 3-Disk Towers of Hanoi")
    print("-" * 80)

    # Configuration
    num_disks = 3
    expected_moves = 2**num_disks - 1  # 7 moves

    print(f"\nTask: Move {num_disks} disks from peg A to peg C")
    print(f"Expected optimal solution: {expected_moves} moves")
    print(f"Total possible states: Large!")
    print(f"Challenge: Find exact sequence with zero errors")

    # Show optimal solution first
    print(f"\n📖 OPTIMAL SOLUTION:")
    optimal = get_optimal_solution(num_disks)
    for i, (from_peg, to_peg) in enumerate(optimal, 1):
        print(f"  {i}. {from_peg} → {to_peg}")

    # Configure MAKER
    k = MAKERConfig.compute_k_for_steps(expected_moves)
    print(f"\n⚙️  MAKER CONFIGURATION:")
    print(f"  Model: gpt-4o-mini (cheaper model works well per paper)")
    print(f"  Voting margin k: {k} (logarithmic scaling)")
    print(f"  Red-flagging: Enabled")
    print(f"  Temperature: 0.7 (for diversity)")

    config = MAKERConfig(
        model="gpt-4o-mini",
        k=k,
        verbose=True,
        temperature=0.7
    )

    # Create MAKER and solve
    print(f"\n🚀 STARTING MAKER SOLVER...")
    print("-" * 80)

    maker = MAKER(config)
    success, moves, stats = maker.solve_towers_of_hanoi(num_disks)

    # Results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    print(f"\n✓ Success: {success}")
    print(f"✓ Moves taken: {len(moves)}")
    print(f"✓ Expected moves: {expected_moves}")
    print(f"✓ Optimal solution: {'Yes' if len(moves) == expected_moves else 'No'}")

    if success and len(moves) == expected_moves:
        print("\n🎉 PERFECT! MAKER found the optimal solution with zero errors!")
    elif success:
        print(f"\n⚠️  Solution found but not optimal (+{len(moves) - expected_moves} extra moves)")
    else:
        print("\n❌ Failed to solve")

    print(f"\n📊 STATISTICS:")
    print(f"  Total steps: {stats['total_steps']}")
    print(f"  Failed steps: {stats.get('failed_steps', 0)}")

    # Compare solutions
    if success:
        print(f"\n📋 SOLUTION COMPARISON:")
        print(f"\n  Optimal:  {' → '.join([f'{f}->{t}' for f, t in optimal])}")
        print(f"  MAKER:    {' → '.join([f'{f}->{t}' for f, t in moves])}")

        if moves == optimal:
            print("\n  ✓ Exact match with optimal solution!")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print(" "*25 + "MAKER DEMONSTRATION")
    print("="*80)

    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please install requirements first.")
        return 1

    # Demonstrate concepts
    demonstrate_concepts()

    # Ask user if they want to run
    print("\n" + "="*80)
    print("⚠️  NOTE: This will make API calls to OpenAI (costs ~$0.01-0.05)")
    print("="*80)

    try:
        response = input("\nProceed with demo? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("\nDemo cancelled.")
            return 0
    except (KeyboardInterrupt, EOFError):
        print("\nDemo cancelled.")
        return 0

    # Run demo
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "="*80)
    print("✓ Demo complete!")
    print("\nNext steps:")
    print("  - Run full test suite: python test_maker.py")
    print("  - Try larger puzzles: modify num_disks in maker.py")
    print("  - Read concepts: cat MAKER_CONCEPTS.md")
    print("  - Read paper: https://arxiv.org/html/2511.09030v1")
    print("="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
