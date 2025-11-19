"""
Real-World Scenario 1: Dependency Resolution & Build Order

Problem: Given a software project with multiple modules/packages that depend on
each other, determine the correct build order to satisfy all dependencies.

This is the classic "topological sort with constraints" problem that build systems
like Make, Gradle, and Bazel solve.
"""

from typing import List, Set, Dict, Tuple, Optional, Any
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


class BuildAction:
    """Represents building a single module."""

    def __init__(self, module_name: str):
        self.module_name = module_name

    def __str__(self):
        return f"build({self.module_name})"

    def __eq__(self, other):
        return isinstance(other, BuildAction) and self.module_name == other.module_name

    def __hash__(self):
        return hash(self.module_name)

    def __repr__(self):
        return str(self)


class DependencyResolutionTask(DecomposableTask):
    """
    Resolve dependencies and determine build order.

    Real-world use cases:
    - Package management (npm, pip, cargo)
    - Build systems (Make, Gradle, Bazel)
    - Deployment orchestration (Kubernetes resources)
    - Infrastructure as Code (Terraform)
    """

    def __init__(self, modules: List[str], dependencies: Dict[str, List[str]]):
        """
        Initialize dependency resolution task.

        Args:
            modules: List of module names
            dependencies: Dict mapping module -> list of dependencies
                Example: {"app": ["lib1", "lib2"], "lib1": ["core"]}
        """
        self.modules = modules
        self.dependencies = dependencies
        self.built = set()
        self.build_order = []

        # Validate no circular dependencies
        self._validate_no_cycles()

    def _validate_no_cycles(self):
        """Check for circular dependencies."""
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)

            for dep in self.dependencies.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for module in self.modules:
            if module not in visited:
                if has_cycle(module):
                    raise ValueError(f"Circular dependency detected involving {module}")

    def get_current_state(self) -> Tuple[Set[str], List[str]]:
        """Get current build state."""
        return self.built, self.build_order

    def get_possible_actions(self) -> List[BuildAction]:
        """Get modules that can be built (all dependencies satisfied)."""
        buildable = []

        for module in self.modules:
            if module in self.built:
                continue

            # Check if all dependencies are built
            deps = self.dependencies.get(module, [])
            if all(dep in self.built for dep in deps):
                buildable.append(BuildAction(module))

        return buildable

    def apply_action(self, action: Any) -> bool:
        """Build a module."""
        if not isinstance(action, BuildAction):
            return False

        module = action.module_name

        # Verify module not already built
        if module in self.built:
            return False

        # Verify dependencies satisfied
        deps = self.dependencies.get(module, [])
        if not all(dep in self.built for dep in deps):
            return False

        # Build module
        self.built.add(module)
        self.build_order.append(module)
        return True

    def is_complete(self) -> bool:
        """Check if all modules built."""
        return len(self.built) == len(self.modules)

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()
        possible_names = [a.module_name for a in possible]

        # Show dependency info for buildable modules
        dep_info = []
        for action in possible:
            module = action.module_name
            deps = self.dependencies.get(module, [])
            if deps:
                dep_info.append(f"  - {module} (depends on: {deps})")
            else:
                dep_info.append(f"  - {module} (no dependencies)")

        return f"""You are determining build order for a software project. Step {step_num}/{len(self.modules)}.

Already built: {sorted(self.built) if self.built else "none"}
Remaining: {sorted(set(self.modules) - self.built)}

Modules ready to build (all dependencies satisfied):
{chr(10).join(dep_info) if dep_info else "  (none ready)"}

Which module should be built next?
Options: {possible_names}

Respond ONLY with the module name. No explanation."""

    def parse_action(self, response: str) -> Optional[BuildAction]:
        """Parse LLM response into action."""
        # Extract module name
        response = response.strip()

        # Check if response matches a possible action
        possible = self.get_possible_actions()
        for action in possible:
            if action.module_name.lower() in response.lower():
                return action

        return None

    def get_progress(self) -> float:
        """Calculate completion percentage."""
        return len(self.built) / len(self.modules)

    def estimate_steps(self) -> int:
        """Estimate steps needed."""
        return len(self.modules)

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate build order is correct."""
        if not self.is_complete():
            return False, "Not all modules built"

        # Verify dependencies satisfied at each step
        built_so_far = set()
        for module in self.build_order:
            deps = self.dependencies.get(module, [])
            for dep in deps:
                if dep not in built_so_far:
                    return False, f"Module {module} built before dependency {dep}"
            built_so_far.add(module)

        return True, f"Valid build order: {' -> '.join(self.build_order)}"


# ============================================================================
# Example Usage
# ============================================================================

def create_simple_project():
    """Create a simple project with dependencies."""
    modules = ["core", "utils", "lib1", "lib2", "app"]
    dependencies = {
        "core": [],
        "utils": ["core"],
        "lib1": ["core", "utils"],
        "lib2": ["core"],
        "app": ["lib1", "lib2", "utils"]
    }
    return modules, dependencies


def create_complex_project():
    """Create a more complex project."""
    modules = [
        "logger", "config", "database", "cache", "auth",
        "api-core", "api-users", "api-products", "api-orders",
        "frontend", "tests", "docs"
    ]
    dependencies = {
        "logger": [],
        "config": [],
        "database": ["config", "logger"],
        "cache": ["config", "logger"],
        "auth": ["database", "config"],
        "api-core": ["config", "logger", "database", "cache"],
        "api-users": ["api-core", "auth"],
        "api-products": ["api-core", "database"],
        "api-orders": ["api-core", "api-users", "api-products"],
        "frontend": ["api-users", "api-products", "api-orders"],
        "tests": ["frontend", "api-orders"],
        "docs": ["frontend"]
    }
    return modules, dependencies


if __name__ == "__main__":
    print("="*80)
    print("SCENARIO 1: Dependency Resolution & Build Order")
    print("="*80)

    # Create project
    modules, dependencies = create_complex_project()

    print(f"\nProject structure:")
    print(f"Modules: {len(modules)}")
    print(f"Dependencies: {sum(len(deps) for deps in dependencies.values())} edges")

    # Create task
    task = DependencyResolutionTask(modules, dependencies)

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=None,  # Auto-compute
        task_type="dependency_resolution",
        verbose=False,  # Keep it concise
        max_response_length=100
    )

    # Custom validator
    def validate_module_name(response: str, context: dict) -> Tuple[bool, str]:
        """Validate response is a valid module name."""
        possible = context.get("possible_modules", [])
        if not any(module in response for module in possible):
            return False, "Response doesn't contain a valid module name"
        return True, ""

    # Note: Would need to pass possible modules through context in real implementation

    print("\n" + "="*80)
    print("Solving with MAKER...")
    print("="*80)

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    if success:
        print("\n✓ Successfully determined build order!")
        print(f"\nBuild order ({len(task.build_order)} steps):")
        for i, module in enumerate(task.build_order, 1):
            deps = dependencies.get(module, [])
            deps_str = f" (after: {deps})" if deps else " (no deps)"
            print(f"  {i:2d}. {module:15s} {deps_str}")

        # Verify correctness
        is_valid, message = task.validate_solution()
        print(f"\nValidation: {message}")
    else:
        print("\n✗ Failed to determine build order")

    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Show optimal solution for comparison
    print("\n" + "="*80)
    print("Note: For this problem, there may be multiple valid build orders.")
    print("Any topological sort of the dependency graph is correct.")
    print("="*80)
