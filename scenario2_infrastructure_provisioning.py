"""
Real-World Scenario 2: Infrastructure Provisioning (Terraform-like)

Problem: Provision cloud infrastructure resources in the correct order,
respecting dependencies and resource quotas.

This is similar to what Terraform, CloudFormation, and Pulumi do when
applying infrastructure changes.
"""

from typing import List, Set, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


class ResourceType(Enum):
    """Types of cloud resources."""
    VPC = "vpc"
    SUBNET = "subnet"
    SECURITY_GROUP = "security_group"
    IAM_ROLE = "iam_role"
    DATABASE = "database"
    CACHE = "cache"
    LOAD_BALANCER = "load_balancer"
    COMPUTE_INSTANCE = "compute_instance"
    STORAGE_BUCKET = "storage_bucket"


@dataclass
class Resource:
    """Represents a cloud resource."""
    name: str
    type: ResourceType
    depends_on: List[str]
    cost: int  # Cost units per hour
    provision_time: int  # Seconds to provision


class ProvisionAction:
    """Represents provisioning a single resource."""

    def __init__(self, resource: Resource):
        self.resource = resource

    def __str__(self):
        return f"provision({self.resource.name})"

    def __eq__(self, other):
        return (isinstance(other, ProvisionAction) and
                self.resource.name == other.resource.name)

    def __hash__(self):
        return hash(self.resource.name)

    def __repr__(self):
        return str(self)


class InfrastructureProvisioningTask(DecomposableTask):
    """
    Provision cloud infrastructure in correct order.

    Real-world use cases:
    - Terraform/CloudFormation deployments
    - Kubernetes cluster setup
    - Multi-region infrastructure
    - Disaster recovery environments
    - CI/CD environment provisioning
    """

    def __init__(self, resources: List[Resource], max_parallel: int = 3):
        """
        Initialize infrastructure provisioning task.

        Args:
            resources: List of resources to provision
            max_parallel: Max resources that can provision simultaneously
        """
        self.resources = {r.name: r for r in resources}
        self.max_parallel = max_parallel

        self.provisioned = set()
        self.provisioning = set()  # Currently provisioning
        self.provision_order = []
        self.total_cost = 0
        self.total_time = 0

        # Resource lookup by name
        self._validate_dependencies()

    def _validate_dependencies(self):
        """Validate all dependencies exist."""
        for resource in self.resources.values():
            for dep in resource.depends_on:
                if dep not in self.resources:
                    raise ValueError(
                        f"Resource {resource.name} depends on unknown resource {dep}"
                    )

    def get_current_state(self) -> Dict:
        """Get current provisioning state."""
        return {
            "provisioned": self.provisioned,
            "provisioning": self.provisioning,
            "remaining": set(self.resources.keys()) - self.provisioned,
            "cost": self.total_cost,
            "time": self.total_time
        }

    def get_possible_actions(self) -> List[ProvisionAction]:
        """Get resources that can be provisioned."""
        # Check capacity
        if len(self.provisioning) >= self.max_parallel:
            return []

        provisionable = []

        for name, resource in self.resources.items():
            # Skip if already provisioned or provisioning
            if name in self.provisioned or name in self.provisioning:
                continue

            # Check if all dependencies are provisioned
            if all(dep in self.provisioned for dep in resource.depends_on):
                provisionable.append(ProvisionAction(resource))

        # Sort by cost (prefer cheaper first) and dependencies (prefer leaf nodes)
        provisionable.sort(
            key=lambda a: (len(a.resource.depends_on), a.resource.cost)
        )

        return provisionable[:self.max_parallel - len(self.provisioning)]

    def apply_action(self, action: Any) -> bool:
        """Provision a resource."""
        if not isinstance(action, ProvisionAction):
            return False

        resource = action.resource

        # Verify not already provisioned
        if resource.name in self.provisioned or resource.name in self.provisioning:
            return False

        # Verify dependencies
        if not all(dep in self.provisioned for dep in resource.depends_on):
            return False

        # Check capacity
        if len(self.provisioning) >= self.max_parallel:
            return False

        # Start provisioning
        self.provisioning.add(resource.name)
        self.provision_order.append(resource.name)

        # Simulate provisioning (in real world, this would be async)
        self.provisioned.add(resource.name)
        self.provisioning.remove(resource.name)

        # Update metrics
        self.total_cost += resource.cost
        self.total_time = max(self.total_time, resource.provision_time)

        return True

    def is_complete(self) -> bool:
        """Check if all resources provisioned."""
        return len(self.provisioned) == len(self.resources)

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()

        # Build resource info
        resource_info = []
        for action in possible:
            r = action.resource
            deps_str = f"depends on: {r.depends_on}" if r.depends_on else "no dependencies"
            resource_info.append(
                f"  - {r.name} ({r.type.value}): {deps_str}, "
                f"cost=${r.cost}/hr, provisions in {r.provision_time}s"
            )

        state = self.get_current_state()

        return f"""You are provisioning cloud infrastructure. Step {step_num}/{len(self.resources)}.

Provisioned: {sorted(state['provisioned']) if state['provisioned'] else "none"}
Currently provisioning: {sorted(state['provisioning']) if state['provisioning'] else "none"}
Remaining: {len(state['remaining'])} resources

Parallel capacity: {len(self.provisioning)}/{self.max_parallel} slots used

Resources ready to provision:
{chr(10).join(resource_info) if resource_info else "  (none ready - waiting on dependencies)"}

Current cost: ${self.total_cost}/hour
Current time: {self.total_time}s

Which resource should be provisioned next?
Options: {[a.resource.name for a in possible]}

Respond ONLY with the resource name. No explanation."""

    def parse_action(self, response: str) -> Optional[ProvisionAction]:
        """Parse LLM response into action."""
        response = response.strip()

        # Check if response matches a possible action
        possible = self.get_possible_actions()
        for action in possible:
            if action.resource.name.lower() in response.lower():
                return action

        return None

    def get_progress(self) -> float:
        """Calculate completion percentage."""
        return len(self.provisioned) / len(self.resources)

    def estimate_steps(self) -> int:
        """Estimate steps needed."""
        return len(self.resources)

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate provisioning order."""
        if not self.is_complete():
            return False, "Not all resources provisioned"

        # Verify dependencies at each step
        provisioned_so_far = set()
        for resource_name in self.provision_order:
            resource = self.resources[resource_name]
            for dep in resource.depends_on:
                if dep not in provisioned_so_far:
                    return False, f"{resource_name} provisioned before dependency {dep}"
            provisioned_so_far.add(resource_name)

        return True, (
            f"Valid provisioning order: {' -> '.join(self.provision_order)}\n"
            f"Total cost: ${self.total_cost}/hour\n"
            f"Total time: {self.total_time}s"
        )


# ============================================================================
# Example Usage
# ============================================================================

def create_simple_infrastructure():
    """Create a simple 3-tier web application infrastructure."""
    return [
        Resource("vpc-main", ResourceType.VPC, [], cost=5, provision_time=30),
        Resource("subnet-public", ResourceType.SUBNET, ["vpc-main"], cost=2, provision_time=20),
        Resource("subnet-private", ResourceType.SUBNET, ["vpc-main"], cost=2, provision_time=20),
        Resource("sg-web", ResourceType.SECURITY_GROUP, ["vpc-main"], cost=0, provision_time=10),
        Resource("sg-db", ResourceType.SECURITY_GROUP, ["vpc-main"], cost=0, provision_time=10),
        Resource("db-primary", ResourceType.DATABASE, ["subnet-private", "sg-db"], cost=50, provision_time=120),
        Resource("cache-redis", ResourceType.CACHE, ["subnet-private", "sg-db"], cost=20, provision_time=60),
        Resource("lb-main", ResourceType.LOAD_BALANCER, ["subnet-public", "sg-web"], cost=30, provision_time=45),
        Resource("app-server-1", ResourceType.COMPUTE_INSTANCE,
                ["subnet-private", "sg-web", "db-primary", "cache-redis"],
                cost=40, provision_time=90),
        Resource("app-server-2", ResourceType.COMPUTE_INSTANCE,
                ["subnet-private", "sg-web", "db-primary", "cache-redis"],
                cost=40, provision_time=90),
    ]


def create_complex_infrastructure():
    """Create a complex multi-region infrastructure."""
    return [
        # Networking
        Resource("vpc-us-east", ResourceType.VPC, [], cost=5, provision_time=30),
        Resource("vpc-eu-west", ResourceType.VPC, [], cost=5, provision_time=30),
        Resource("subnet-us-public", ResourceType.SUBNET, ["vpc-us-east"], cost=2, provision_time=20),
        Resource("subnet-us-private", ResourceType.SUBNET, ["vpc-us-east"], cost=2, provision_time=20),
        Resource("subnet-eu-public", ResourceType.SUBNET, ["vpc-eu-west"], cost=2, provision_time=20),
        Resource("subnet-eu-private", ResourceType.SUBNET, ["vpc-eu-west"], cost=2, provision_time=20),

        # Security
        Resource("sg-web", ResourceType.SECURITY_GROUP, ["vpc-us-east", "vpc-eu-west"], cost=0, provision_time=10),
        Resource("sg-db", ResourceType.SECURITY_GROUP, ["vpc-us-east", "vpc-eu-west"], cost=0, provision_time=10),
        Resource("iam-app-role", ResourceType.IAM_ROLE, [], cost=0, provision_time=15),

        # Storage
        Resource("s3-media", ResourceType.STORAGE_BUCKET, [], cost=10, provision_time=20),
        Resource("s3-logs", ResourceType.STORAGE_BUCKET, [], cost=5, provision_time=20),

        # Databases
        Resource("db-us-primary", ResourceType.DATABASE,
                ["subnet-us-private", "sg-db"], cost=80, provision_time=180),
        Resource("db-eu-replica", ResourceType.DATABASE,
                ["subnet-eu-private", "sg-db", "db-us-primary"], cost=80, provision_time=180),
        Resource("cache-us", ResourceType.CACHE,
                ["subnet-us-private", "sg-db"], cost=30, provision_time=60),
        Resource("cache-eu", ResourceType.CACHE,
                ["subnet-eu-private", "sg-db"], cost=30, provision_time=60),

        # Load Balancers
        Resource("lb-us", ResourceType.LOAD_BALANCER,
                ["subnet-us-public", "sg-web"], cost=40, provision_time=45),
        Resource("lb-eu", ResourceType.LOAD_BALANCER,
                ["subnet-eu-public", "sg-web"], cost=40, provision_time=45),

        # Compute
        Resource("app-us-1", ResourceType.COMPUTE_INSTANCE,
                ["subnet-us-private", "sg-web", "db-us-primary", "cache-us", "iam-app-role", "s3-media"],
                cost=60, provision_time=90),
        Resource("app-us-2", ResourceType.COMPUTE_INSTANCE,
                ["subnet-us-private", "sg-web", "db-us-primary", "cache-us", "iam-app-role", "s3-media"],
                cost=60, provision_time=90),
        Resource("app-eu-1", ResourceType.COMPUTE_INSTANCE,
                ["subnet-eu-private", "sg-web", "db-eu-replica", "cache-eu", "iam-app-role", "s3-media"],
                cost=60, provision_time=90),
        Resource("app-eu-2", ResourceType.COMPUTE_INSTANCE,
                ["subnet-eu-private", "sg-web", "db-eu-replica", "cache-eu", "iam-app-role", "s3-media"],
                cost=60, provision_time=90),
    ]


if __name__ == "__main__":
    print("="*80)
    print("SCENARIO 2: Infrastructure Provisioning (Terraform-like)")
    print("="*80)

    # Create infrastructure
    resources = create_complex_infrastructure()

    print(f"\nInfrastructure to provision:")
    print(f"Total resources: {len(resources)}")
    print(f"Total cost: ${sum(r.cost for r in resources)}/hour")
    print(f"Max parallel: 3 resources")

    # Group by type
    by_type = {}
    for r in resources:
        by_type.setdefault(r.type.value, []).append(r.name)

    print(f"\nBy resource type:")
    for rtype, names in sorted(by_type.items()):
        print(f"  {rtype}: {len(names)}")

    # Create task
    task = InfrastructureProvisioningTask(resources, max_parallel=3)

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=None,  # Auto-compute
        task_type="infrastructure_provisioning",
        verbose=False,
        max_response_length=100
    )

    print("\n" + "="*80)
    print("Provisioning with MAKER...")
    print("="*80)

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    if success:
        print("\n✓ Successfully provisioned all infrastructure!")

        print(f"\nProvisioning order ({len(task.provision_order)} resources):")
        for i, name in enumerate(task.provision_order, 1):
            resource = task.resources[name]
            deps_str = f" (after: {resource.depends_on})" if resource.depends_on else ""
            print(f"  {i:2d}. {name:20s} [{resource.type.value:15s}] ${resource.cost:2d}/hr{deps_str}")

        print(f"\nInfrastructure summary:")
        print(f"  Total monthly cost: ${task.total_cost * 24 * 30:,}/month")
        print(f"  Estimated provision time: {task.total_time}s ({task.total_time // 60}m {task.total_time % 60}s)")

        # Verify correctness
        is_valid, message = task.validate_solution()
        print(f"\nValidation: {message}")
    else:
        print("\n✗ Failed to provision infrastructure")

    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
