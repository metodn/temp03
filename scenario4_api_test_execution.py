"""
Complex Scenario 1: API Integration Test Suite Execution with Dependencies

Problem: Execute a comprehensive API integration test suite where tests have:
- Dependencies (test B requires test A's output)
- Setup/teardown requirements
- Shared state and data
- Parallel execution limits
- Retry logic for flaky tests
- Resource cleanup requirements

This is significantly more complex than unit testing due to:
- Tests aren't independent
- State management between tests
- Real API rate limits
- Test data dependencies
- Partial failure handling
"""

from typing import List, Set, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestCase:
    """Represents an API integration test."""
    id: str
    name: str
    endpoint: str
    depends_on: List[str]  # Other test IDs that must pass first
    requires_data_from: List[str]  # Tests that provide data (e.g., user ID)
    setup_required: Optional[str]  # Setup fixture needed
    cleanup_required: bool  # Needs cleanup after execution
    estimated_time: int  # Seconds
    priority: int  # 1-5, higher = more critical
    can_run_parallel: bool  # Can run in parallel with others
    max_retries: int  # For flaky tests

    # Runtime data
    actual_retries: int = 0
    execution_time: int = 0
    output_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.output_data is None:
            self.output_data = {}


@dataclass
class TestAction:
    """Represents executing a test."""
    test: TestCase
    parallel_slot: int  # Which parallel slot to use

    def __str__(self):
        return f"execute({self.test.id} in slot {self.parallel_slot})"

    def __eq__(self, other):
        return (isinstance(other, TestAction) and
                self.test.id == other.test.id)

    def __hash__(self):
        return hash(self.test.id)

    def __repr__(self):
        return str(self)


class APITestSuiteTask(DecomposableTask):
    """
    Execute API integration test suite with complex dependencies.

    Real-world use cases:
    - Microservices integration testing
    - E2E API testing pipelines
    - Multi-service orchestration tests
    - Contract testing between services
    - Performance and load testing with dependencies

    Complexity factors:
    - Test dependencies (auth before user CRUD)
    - Data dependencies (user creation before user update)
    - Parallel execution (max N tests at once)
    - Setup/teardown management
    - Flaky test retries
    - Resource cleanup
    - Rate limiting
    - Partial failures (continue or abort?)
    """

    def __init__(
        self,
        tests: List[TestCase],
        max_parallel: int = 3,
        api_rate_limit: int = 10,  # requests per second
        abort_on_critical_failure: bool = True
    ):
        """
        Initialize API test suite execution task.

        Args:
            tests: List of test cases
            max_parallel: Max tests running simultaneously
            api_rate_limit: API calls per second limit
            abort_on_critical_failure: Stop on high-priority test failure
        """
        self.tests = {t.id: t for t in tests}
        self.max_parallel = max_parallel
        self.api_rate_limit = api_rate_limit
        self.abort_on_critical_failure = abort_on_critical_failure

        # Execution state
        self.test_status = {t.id: TestStatus.PENDING for t in tests}
        self.running_tests = set()
        self.execution_order = []
        self.shared_data = {}  # Data shared between tests
        self.setup_fixtures = {}  # Active setup fixtures

        # Metrics
        self.total_passed = 0
        self.total_failed = 0
        self.total_skipped = 0
        self.total_time = 0
        self.total_retries = 0

        self._validate_dependencies()

    def _validate_dependencies(self):
        """Validate test dependencies exist."""
        for test in self.tests.values():
            for dep in test.depends_on + test.requires_data_from:
                if dep not in self.tests:
                    raise ValueError(
                        f"Test {test.id} depends on unknown test {dep}"
                    )

    def get_current_state(self) -> Dict:
        """Get current test execution state."""
        return {
            "pending": sum(1 for s in self.test_status.values() if s == TestStatus.PENDING),
            "running": len(self.running_tests),
            "passed": self.total_passed,
            "failed": self.total_failed,
            "skipped": self.total_skipped,
            "total_time": self.total_time,
            "coverage": f"{((self.total_passed + self.total_failed) / len(self.tests)) * 100:.1f}%"
        }

    def _can_execute_test(self, test_id: str) -> Tuple[bool, str]:
        """Check if test can be executed."""
        test = self.tests[test_id]

        # Already executed?
        if self.test_status[test_id] != TestStatus.PENDING:
            return False, "Already executed"

        # Check capacity
        if len(self.running_tests) >= self.max_parallel:
            return False, "At capacity"

        # If can't run parallel, must be alone
        if not test.can_run_parallel and len(self.running_tests) > 0:
            return False, "Cannot run in parallel"

        # If others running and they can't be parallel
        for running_id in self.running_tests:
            if not self.tests[running_id].can_run_parallel:
                return False, "Other non-parallel test running"

        # Check dependencies passed
        for dep_id in test.depends_on:
            if self.test_status[dep_id] != TestStatus.PASSED:
                return False, f"Dependency {dep_id} not passed"

        # Check data dependencies available
        for data_dep_id in test.requires_data_from:
            if self.test_status[data_dep_id] != TestStatus.PASSED:
                return False, f"Data dependency {data_dep_id} not passed"
            if data_dep_id not in self.shared_data:
                return False, f"Data from {data_dep_id} not available"

        return True, "Can execute"

    def get_possible_actions(self) -> List[TestAction]:
        """Get tests that can be executed now."""
        actions = []

        # Find executable tests
        for test_id, test in self.tests.items():
            can_execute, reason = self._can_execute_test(test_id)
            if can_execute:
                # Assign to parallel slot
                for slot in range(self.max_parallel):
                    actions.append(TestAction(test, slot))
                    break  # One action per test

        # Sort by priority (higher first) and dependencies (fewer deps first)
        actions.sort(
            key=lambda a: (-a.test.priority, len(a.test.depends_on))
        )

        return actions[:self.max_parallel - len(self.running_tests)]

    def apply_action(self, action: Any) -> bool:
        """Execute a test."""
        if not isinstance(action, TestAction):
            return False

        test = action.test

        # Verify can execute
        can_execute, reason = self._can_execute_test(test.id)
        if not can_execute:
            return False

        # Setup fixture if needed
        if test.setup_required and test.setup_required not in self.setup_fixtures:
            self._setup_fixture(test.setup_required)

        # Execute test (simulated)
        self.running_tests.add(test.id)
        self.test_status[test.id] = TestStatus.RUNNING

        # Simulate execution
        success, output_data = self._simulate_test_execution(test)

        # Update state
        self.running_tests.remove(test.id)

        if success:
            self.test_status[test.id] = TestStatus.PASSED
            self.total_passed += 1

            # Store output data for dependent tests
            if output_data:
                self.shared_data[test.id] = output_data
        else:
            # Retry logic
            if test.actual_retries < test.max_retries:
                test.actual_retries += 1
                self.total_retries += 1
                self.test_status[test.id] = TestStatus.PENDING  # Retry
                return True  # Action succeeded (test will retry)
            else:
                self.test_status[test.id] = TestStatus.FAILED
                self.total_failed += 1

                # Check if critical failure
                if self.abort_on_critical_failure and test.priority >= 4:
                    # Skip all remaining tests
                    for tid, status in self.test_status.items():
                        if status == TestStatus.PENDING:
                            self.test_status[tid] = TestStatus.SKIPPED
                            self.total_skipped += 1

        # Cleanup if needed
        if test.cleanup_required:
            self._cleanup_test_resources(test)

        self.execution_order.append(test.id)
        self.total_time += test.estimated_time

        return True

    def _setup_fixture(self, fixture_name: str):
        """Set up a test fixture."""
        self.setup_fixtures[fixture_name] = True
        # In real implementation, would create database, seed data, etc.

    def _simulate_test_execution(
        self,
        test: TestCase
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Simulate test execution.
        In real implementation, would call actual API.
        """
        # Simulate 95% success rate for normal tests, 80% for flaky
        import random
        success_rate = 0.95 if test.max_retries == 0 else 0.80
        success = random.random() < success_rate

        # Generate mock output data
        output_data = None
        if success and test.id.startswith("create_"):
            # Simulated created resource
            output_data = {
                "id": f"resource_{test.id}_{int(time.time())}",
                "status": "active"
            }

        return success, output_data

    def _cleanup_test_resources(self, test: TestCase):
        """Clean up resources created by test."""
        # In real implementation, would delete created resources
        pass

    def is_complete(self) -> bool:
        """Check if all tests executed (passed, failed, or skipped)."""
        return all(
            status != TestStatus.PENDING
            for status in self.test_status.values()
        )

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()

        if not possible:
            return "No tests ready to execute (waiting on dependencies or at capacity)"

        # Format test options
        test_info = []
        for i, action in enumerate(possible, 1):
            test = action.test
            deps_str = f"depends on: {test.depends_on}" if test.depends_on else "no deps"
            data_deps_str = ""
            if test.requires_data_from:
                data_deps_str = f", needs data from: {test.requires_data_from}"

            parallel_str = "⚡ parallel" if test.can_run_parallel else "🔒 sequential"
            priority_str = "🔴" * test.priority

            test_info.append(
                f"  {i}. {test.id:30s} [{test.endpoint:20s}] {priority_str}\n"
                f"      {deps_str}{data_deps_str}\n"
                f"      {parallel_str}, ~{test.estimated_time}s, retries:{test.actual_retries}/{test.max_retries}"
            )

        state = self.get_current_state()

        return f"""You are executing API integration test suite. Step {step_num}/{len(self.tests)}.

Status:
  Passed: {state['passed']}
  Failed: {state['failed']}
  Skipped: {state['skipped']}
  Running: {state['running']}
  Pending: {state['pending']}
  Coverage: {state['coverage']}
  Total time: {state['total_time']}s

Parallel capacity: {len(self.running_tests)}/{self.max_parallel} slots used

Tests ready to execute:
{chr(10).join(test_info)}

Which test should be executed next?
Respond with just the number (1-{len(possible)}). No explanation."""

    def parse_action(self, response: str) -> Optional[TestAction]:
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
        """Calculate completion percentage."""
        executed = self.total_passed + self.total_failed + self.total_skipped
        return executed / len(self.tests)

    def estimate_steps(self) -> int:
        """Estimate steps needed."""
        return len(self.tests) + sum(t.max_retries for t in self.tests.values())

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate test execution."""
        if not self.is_complete():
            return False, "Not all tests executed"

        # Check if critical tests passed
        critical_failures = [
            test.id for test in self.tests.values()
            if test.priority >= 4 and self.test_status[test.id] == TestStatus.FAILED
        ]

        if critical_failures:
            return False, f"Critical tests failed: {critical_failures}"

        # Generate report
        pass_rate = (self.total_passed / len(self.tests)) * 100

        return True, (
            f"Test suite execution complete.\n"
            f"Passed: {self.total_passed}/{len(self.tests)} ({pass_rate:.1f}%)\n"
            f"Failed: {self.total_failed}\n"
            f"Skipped: {self.total_skipped}\n"
            f"Total retries: {self.total_retries}\n"
            f"Total time: {self.total_time}s\n"
            f"Execution order: {' -> '.join(self.execution_order[:10])}..."
        )


# ============================================================================
# Example Usage
# ============================================================================

def create_api_test_suite():
    """Create a comprehensive API test suite."""
    tests = [
        # Authentication tests (must run first)
        TestCase(
            id="auth_login",
            name="Test user login",
            endpoint="/api/auth/login",
            depends_on=[],
            requires_data_from=[],
            setup_required="database",
            cleanup_required=False,
            estimated_time=5,
            priority=5,  # Critical
            can_run_parallel=False,  # Must be alone
            max_retries=0
        ),
        TestCase(
            id="auth_token_refresh",
            name="Test token refresh",
            endpoint="/api/auth/refresh",
            depends_on=["auth_login"],
            requires_data_from=["auth_login"],
            setup_required="database",
            cleanup_required=False,
            estimated_time=3,
            priority=5,
            can_run_parallel=True,
            max_retries=1
        ),

        # User CRUD tests
        TestCase(
            id="create_user",
            name="Create new user",
            endpoint="/api/users",
            depends_on=["auth_login"],
            requires_data_from=["auth_login"],
            setup_required="database",
            cleanup_required=True,
            estimated_time=4,
            priority=4,
            can_run_parallel=True,
            max_retries=1
        ),
        TestCase(
            id="get_user",
            name="Get user details",
            endpoint="/api/users/:id",
            depends_on=["create_user"],
            requires_data_from=["create_user"],
            setup_required="database",
            cleanup_required=False,
            estimated_time=2,
            priority=3,
            can_run_parallel=True,
            max_retries=0
        ),
        TestCase(
            id="update_user",
            name="Update user",
            endpoint="/api/users/:id",
            depends_on=["create_user"],
            requires_data_from=["create_user"],
            setup_required="database",
            cleanup_required=False,
            estimated_time=3,
            priority=3,
            can_run_parallel=True,
            max_retries=1
        ),
        TestCase(
            id="delete_user",
            name="Delete user",
            endpoint="/api/users/:id",
            depends_on=["create_user", "get_user", "update_user"],
            requires_data_from=["create_user"],
            setup_required="database",
            cleanup_required=False,
            estimated_time=3,
            priority=3,
            can_run_parallel=True,
            max_retries=0
        ),

        # Product tests
        TestCase(
            id="create_product",
            name="Create product",
            endpoint="/api/products",
            depends_on=["auth_login"],
            requires_data_from=["auth_login"],
            setup_required="database",
            cleanup_required=True,
            estimated_time=4,
            priority=4,
            can_run_parallel=True,
            max_retries=1
        ),
        TestCase(
            id="list_products",
            name="List all products",
            endpoint="/api/products",
            depends_on=["create_product"],
            requires_data_from=[],
            setup_required="database",
            cleanup_required=False,
            estimated_time=3,
            priority=2,
            can_run_parallel=True,
            max_retries=2  # Flaky test
        ),

        # Order tests (depend on both user and product)
        TestCase(
            id="create_order",
            name="Create order",
            endpoint="/api/orders",
            depends_on=["create_user", "create_product"],
            requires_data_from=["create_user", "create_product"],
            setup_required="database",
            cleanup_required=True,
            estimated_time=5,
            priority=5,
            can_run_parallel=True,
            max_retries=1
        ),
        TestCase(
            id="get_order",
            name="Get order details",
            endpoint="/api/orders/:id",
            depends_on=["create_order"],
            requires_data_from=["create_order"],
            setup_required="database",
            cleanup_required=False,
            estimated_time=2,
            priority=4,
            can_run_parallel=True,
            max_retries=0
        ),
        TestCase(
            id="cancel_order",
            name="Cancel order",
            endpoint="/api/orders/:id/cancel",
            depends_on=["create_order", "get_order"],
            requires_data_from=["create_order"],
            setup_required="database",
            cleanup_required=False,
            estimated_time=4,
            priority=4,
            can_run_parallel=True,
            max_retries=1
        ),

        # Payment tests
        TestCase(
            id="process_payment",
            name="Process payment",
            endpoint="/api/payments",
            depends_on=["create_order"],
            requires_data_from=["create_order"],
            setup_required="payment_gateway",
            cleanup_required=True,
            estimated_time=6,
            priority=5,
            can_run_parallel=False,  # Payment gateway limitation
            max_retries=2
        ),

        # Analytics tests (low priority)
        TestCase(
            id="get_analytics",
            name="Get analytics data",
            endpoint="/api/analytics",
            depends_on=["create_order", "process_payment"],
            requires_data_from=[],
            setup_required="database",
            cleanup_required=False,
            estimated_time=7,
            priority=1,
            can_run_parallel=True,
            max_retries=2
        ),
    ]

    return tests


if __name__ == "__main__":
    print("="*80)
    print("COMPLEX SCENARIO 1: API Integration Test Suite Execution")
    print("="*80)

    # Create test suite
    tests = create_api_test_suite()

    print(f"\nTest Suite Overview:")
    print(f"Total tests: {len(tests)}")
    print(f"Critical tests (priority 5): {sum(1 for t in tests if t.priority == 5)}")
    print(f"Tests with retries: {sum(1 for t in tests if t.max_retries > 0)}")
    print(f"Non-parallel tests: {sum(1 for t in tests if not t.can_run_parallel)}")
    print(f"Total dependencies: {sum(len(t.depends_on) for t in tests)}")
    print(f"Estimated time (sequential): {sum(t.estimated_time for t in tests)}s")
    print(f"Estimated time (parallel): ~{sum(t.estimated_time for t in tests) // 3}s")

    # Create task
    task = APITestSuiteTask(
        tests=tests,
        max_parallel=3,
        api_rate_limit=10,
        abort_on_critical_failure=True
    )

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=2,  # Lower k for faster execution
        task_type="api_test_suite",
        verbose=False,
        max_response_length=50
    )

    print("\n" + "="*80)
    print("Executing test suite with MAKER...")
    print("="*80)

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    if success:
        print("\n✓ Test suite execution complete!")

        # Show results
        state = task.get_current_state()
        print(f"\nResults:")
        print(f"  Passed: {state['passed']}/{len(tests)} ({(state['passed']/len(tests))*100:.1f}%)")
        print(f"  Failed: {state['failed']}")
        print(f"  Skipped: {state['skipped']}")
        print(f"  Total retries: {task.total_retries}")
        print(f"  Total time: {task.total_time}s")
        print(f"  Coverage: {state['coverage']}")

        # Show execution order
        print(f"\nExecution order (first 10):")
        for i, test_id in enumerate(task.execution_order[:10], 1):
            test = task.tests[test_id]
            status = "✓" if task.test_status[test_id] == TestStatus.PASSED else "✗"
            print(f"  {i:2d}. {status} {test_id:30s} (priority: {test.priority})")

        # Verify correctness
        is_valid, message = task.validate_solution()
        print(f"\nValidation:")
        print(f"  {message}")
    else:
        print("\n✗ Test suite execution failed or incomplete")

    print(f"\nMAKER Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "="*80)
    print("Key Insights:")
    print("- MAKER handles complex test dependencies automatically")
    print("- Parallel execution optimized while respecting constraints")
    print("- Automatic retry logic for flaky tests")
    print("- Critical test failures handled gracefully")
    print("- Data dependencies tracked between tests")
    print("="*80)
