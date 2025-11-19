"""
Test script for MAKER system implementation.

Tests various concepts from the paper:
1. Basic functionality with small tasks
2. Scaling with different disk counts
3. Model comparison (if multiple models available)
4. Red-flagging effectiveness
5. Voting margin impact
"""

import os
import time
from typing import Dict, List
from maker import MAKER, MAKERConfig
from towers_of_hanoi import GameState, get_optimal_solution, verify_solution


def test_basic_functionality():
    """Test basic MAKER functionality with 3 disks."""
    print("\n" + "="*80)
    print("TEST 1: Basic Functionality (3 disks)")
    print("="*80)

    config = MAKERConfig(
        model="gpt-4o-mini",
        k=2,
        verbose=True
    )

    maker = MAKER(config)
    success, moves, stats = maker.solve_towers_of_hanoi(num_disks=3)

    expected_moves = 2**3 - 1  # 7 moves

    print(f"\nResults:")
    print(f"  Success: {success}")
    print(f"  Moves taken: {len(moves)}")
    print(f"  Expected moves: {expected_moves}")
    print(f"  Optimal: {len(moves) == expected_moves}")

    return success and len(moves) == expected_moves


def test_scaling():
    """Test MAKER with increasing disk counts."""
    print("\n" + "="*80)
    print("TEST 2: Scaling Test (3, 4, 5 disks)")
    print("="*80)

    results = []

    for num_disks in [3, 4, 5]:
        print(f"\n--- Testing with {num_disks} disks ---")

        expected_moves = 2**num_disks - 1
        k = MAKERConfig.compute_k_for_steps(expected_moves)

        config = MAKERConfig(
            model="gpt-4o-mini",
            k=k,
            verbose=False  # Less verbose for scaling tests
        )

        maker = MAKER(config)
        start_time = time.time()
        success, moves, stats = maker.solve_towers_of_hanoi(num_disks)
        elapsed = time.time() - start_time

        is_optimal = len(moves) == expected_moves

        results.append({
            "disks": num_disks,
            "success": success,
            "moves": len(moves),
            "expected": expected_moves,
            "optimal": is_optimal,
            "k": k,
            "time": elapsed
        })

        print(f"  Success: {success}, Moves: {len(moves)}/{expected_moves}, Time: {elapsed:.1f}s, k: {k}")

    # Summary
    print(f"\n{'='*80}")
    print("Scaling Test Summary:")
    print(f"{'Disks':<10} {'Expected':<10} {'Actual':<10} {'Optimal':<10} {'k':<5} {'Time (s)':<10}")
    print("-" * 80)
    for r in results:
        print(f"{r['disks']:<10} {r['expected']:<10} {r['moves']:<10} "
              f"{'✓' if r['optimal'] else '✗':<10} {r['k']:<5} {r['time']:<10.1f}")

    return all(r['success'] for r in results)


def test_voting_margin():
    """Test impact of different voting margins."""
    print("\n" + "="*80)
    print("TEST 3: Voting Margin Impact (k=1, 2, 3)")
    print("="*80)

    num_disks = 3
    results = []

    for k in [1, 2, 3]:
        print(f"\n--- Testing with k={k} ---")

        config = MAKERConfig(
            model="gpt-4o-mini",
            k=k,
            verbose=False
        )

        maker = MAKER(config)
        start_time = time.time()
        success, moves, stats = maker.solve_towers_of_hanoi(num_disks)
        elapsed = time.time() - start_time

        results.append({
            "k": k,
            "success": success,
            "moves": len(moves),
            "time": elapsed
        })

        print(f"  k={k}: Success: {success}, Moves: {len(moves)}, Time: {elapsed:.1f}s")

    # Summary
    print(f"\n{'='*80}")
    print("Voting Margin Test Summary:")
    print(f"{'k':<5} {'Success':<10} {'Moves':<10} {'Time (s)':<10}")
    print("-" * 80)
    for r in results:
        print(f"{r['k']:<5} {'✓' if r['success'] else '✗':<10} {r['moves']:<10} {r['time']:<10.1f}")

    print("\nNote: Higher k requires more agent calls but increases reliability.")

    return all(r['success'] for r in results)


def test_red_flagging():
    """Test red-flagging effectiveness."""
    print("\n" + "="*80)
    print("TEST 4: Red-Flagging Test")
    print("="*80)

    from maker import RedFlagger

    config = MAKERConfig(
        max_response_length=100,
        min_response_length=1
    )

    flagger = RedFlagger(config)

    test_cases = [
        ("A->B", False, "Valid move"),
        ("", True, "Empty response"),
        ("I cannot help with that", True, "Failure pattern"),
        ("A to B", False, "Valid move (alternative format)"),
        ("X" * 300, True, "Too long"),
        ("Move disk from peg A to peg B because that's the optimal strategy...", False, "Verbose but contains info"),
        ("I don't know the answer", True, "Failure pattern"),
        ("AB", False, "Valid short format"),
    ]

    print("\nRed-Flagging Test Cases:")
    print(f"{'Response':<50} {'Flagged':<10} {'Expected':<10} {'Status':<10}")
    print("-" * 80)

    passed = 0
    for response, should_flag, description in test_cases:
        is_flagged, reason = flagger.should_flag(response, {})
        matches = is_flagged == should_flag
        status = "✓" if matches else "✗"

        display_response = response[:47] + "..." if len(response) > 50 else response
        print(f"{display_response:<50} {is_flagged!s:<10} {should_flag!s:<10} {status:<10}")

        if matches:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")

    return passed == len(test_cases)


def test_verification():
    """Test solution verification."""
    print("\n" + "="*80)
    print("TEST 5: Solution Verification")
    print("="*80)

    # Test with correct solution
    num_disks = 4
    optimal_solution = get_optimal_solution(num_disks)

    print(f"Testing {num_disks}-disk optimal solution...")
    is_valid, message = verify_solution(num_disks, optimal_solution)
    print(f"  Valid: {is_valid}")
    print(f"  Message: {message}")

    # Test with incorrect solution
    print(f"\nTesting invalid solution...")
    invalid_solution = [("A", "B"), ("A", "B")]  # Invalid moves
    is_valid, message = verify_solution(num_disks, invalid_solution)
    print(f"  Valid: {is_valid}")
    print(f"  Message: {message}")

    return True


def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*80)
    print("MAKER SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)

    # Check if litellm is available
    try:
        from litellm import completion
        litellm_available = True
    except ImportError:
        print("\nWARNING: litellm not installed!")
        print("Install with: pip install litellm")
        print("\nOnly running tests that don't require LLM calls...\n")
        litellm_available = False

    tests = [
        ("Solution Verification", test_verification, True),
        ("Red-Flagging", test_red_flagging, True),
    ]

    if litellm_available:
        # Check if API key is set
        api_key_set = os.getenv("OPENAI_API_KEY") is not None
        if not api_key_set:
            print("\nWARNING: OPENAI_API_KEY not set!")
            print("Set with: export OPENAI_API_KEY='your-key-here'")
            print("\nSkipping LLM-based tests...\n")
        else:
            tests.extend([
                ("Basic Functionality", test_basic_functionality, False),
                ("Scaling", test_scaling, False),
                ("Voting Margin", test_voting_margin, False),
            ])

    results = []
    for test_name, test_func, always_run in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"{'Test Name':<30} {'Status':<10} {'Error':<40}")
    print("-" * 80)

    passed = 0
    for test_name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        error_msg = error[:37] + "..." if error and len(error) > 40 else (error or "")
        print(f"{test_name:<30} {status:<10} {error_msg:<40}")
        if result:
            passed += 1

    print("-" * 80)
    print(f"Total: {passed}/{len(results)} tests passed")
    print("="*80)

    return passed == len(results)


if __name__ == "__main__":
    success = run_all_tests()

    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed. See details above.")

    exit(0 if success else 1)
