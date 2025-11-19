"""
Complex Scenario 3: Distributed System Rolling Deployment

Problem: Deploy a new version of a distributed system with:
- Multiple microservices with dependencies
- Rolling updates (gradual instance replacement)
- Health checks at each stage
- Database migrations coordinated with service updates
- Load balancer reconfiguration
- Automatic rollback on failure
- Zero downtime requirement
- Canary deployments for critical services
- Service mesh configuration updates

This is the MOST complex scenario because:
- Must coordinate multiple services
- Can't all update at once (dependencies!)
- Need health checks between steps
- Rollback must work at any point
- Database schema must be compatible with old AND new versions during transition
- Load balancers must route traffic correctly
- Monitoring must detect issues quickly
"""

from typing import List, Set, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


class DeploymentType(Enum):
    """Types of deployment operations."""
    DB_MIGRATION = "db_migration"
    DEPLOY_SERVICE = "deploy_service"
    HEALTH_CHECK = "health_check"
    UPDATE_LB = "update_load_balancer"
    CANARY_DEPLOY = "canary_deploy"
    CANARY_VALIDATE = "canary_validate"
    CANARY_PROMOTE = "canary_promote"
    ROLLBACK = "rollback"
    DRAIN_TRAFFIC = "drain_traffic"
    UPDATE_CONFIG = "update_config"
    SMOKE_TEST = "smoke_test"


@dataclass
class Service:
    """Represents a microservice."""
    name: str
    version_old: str
    version_new: str
    instances: int  # Number of instances
    depends_on: List[str]  # Other service names
    requires_db_migration: bool
    is_stateful: bool  # Stateful services need careful handling
    health_check_endpoint: str
    rollout_strategy: str  # "rolling", "canary", "blue-green"
    criticality: int  # 1-5, higher = more critical


@dataclass
class DeploymentStep:
    """Represents a single deployment step."""
    id: str
    name: str
    type: DeploymentType
    service: Optional[str]  # Service name, if applicable
    depends_on: List[str]  # Other step IDs
    can_rollback: bool
    estimated_time: int  # Seconds
    risk_level: int  # 1-5
    instances_affected: int  # How many instances touched

    # Health check configuration
    health_check_required: bool = True
    health_check_timeout: int = 30

    # Rollback information
    rollback_step_id: Optional[str] = None

    def __hash__(self):
        return hash(self.id)


@dataclass
class DeploymentAction:
    """Represents executing a deployment step."""
    step: DeploymentStep

    def __str__(self):
        service_str = f"/{self.step.service}" if self.step.service else ""
        return f"execute({self.step.id}{service_str})"

    def __eq__(self, other):
        return (isinstance(other, DeploymentAction) and
                self.step.id == other.step.id)

    def __hash__(self):
        return hash(self.step.id)

    def __repr__(self):
        return str(self)


class DistributedDeploymentTask(DecomposableTask):
    """
    Execute distributed system rolling deployment.

    Real-world use cases:
    - Kubernetes rolling updates
    - Multi-region deployments
    - Microservices orchestration
    - Blue-green deployments
    - Canary releases
    - Database + application coordinated updates

    Complexity factors:
    - Service dependencies (API gateway depends on auth service)
    - Rolling updates (replace instances gradually)
    - Health checks (verify each step works)
    - Rollback capability (undo on failure)
    - Zero downtime (always have working instances)
    - Database compatibility (schema works with old AND new code)
    - Load balancer updates (route traffic correctly)
    - Stateful services (can't just restart)
    - Canary deployments (test on small traffic first)
    - Multi-region coordination
    """

    def __init__(
        self,
        services: List[Service],
        deployment_steps: List[DeploymentStep],
        max_parallel_deployments: int = 2
    ):
        """
        Initialize distributed deployment task.

        Args:
            services: List of services to deploy
            deployment_steps: List of deployment steps
            max_parallel_deployments: Max services deploying simultaneously
        """
        self.services = {s.name: s for s in services}
        self.steps = {s.id: s for s in deployment_steps}
        self.max_parallel_deployments = max_parallel_deployments

        # Execution state
        self.executed = set()
        self.in_progress = set()
        self.execution_order = []
        self.health_checks_passed = {}  # step_id -> bool
        self.rollback_required = False
        self.rollback_stack = []

        # Metrics
        self.total_time = 0
        self.total_instances_deployed = 0
        self.failed_health_checks = 0
        self.successful_rollbacks = 0

        # Service state tracking
        self.service_versions = {
            name: service.version_old
            for name, service in self.services.items()
        }
        self.service_health = {
            name: True for name in self.services.keys()
        }

        self._validate_dependencies()

    def _validate_dependencies(self):
        """Validate deployment dependencies."""
        for step in self.steps.values():
            for dep in step.depends_on:
                if dep not in self.steps:
                    raise ValueError(
                        f"Step {step.id} depends on unknown step {dep}"
                    )

    def get_current_state(self) -> Dict:
        """Get current deployment state."""
        return {
            "executed": len(self.executed),
            "in_progress": len(self.in_progress),
            "remaining": len(self.steps) - len(self.executed),
            "progress": f"{(len(self.executed) / len(self.steps)) * 100:.1f}%",
            "total_time": self.total_time,
            "instances_deployed": self.total_instances_deployed,
            "health_checks_failed": self.failed_health_checks,
            "rollback_required": self.rollback_required,
            "services_updated": sum(
                1 for name, version in self.service_versions.items()
                if version == self.services[name].version_new
            ),
            "all_services_healthy": all(self.service_health.values())
        }

    def get_possible_actions(self) -> List[DeploymentAction]:
        """Get deployment steps that can be executed."""
        # If rollback required, only return rollback steps
        if self.rollback_required:
            rollback_actions = []
            for step in self.rollback_stack:
                if step.rollback_step_id and step.rollback_step_id not in self.executed:
                    rollback_step = self.steps.get(step.rollback_step_id)
                    if rollback_step:
                        rollback_actions.append(DeploymentAction(rollback_step))
            return rollback_actions[:1]  # One rollback at a time

        actions = []

        # Check capacity
        services_deploying = len([
            s for s in self.in_progress
            if self.steps[s].type == DeploymentType.DEPLOY_SERVICE
        ])

        # Find executable steps
        for step_id, step in self.steps.items():
            # Already executed or in progress?
            if step_id in self.executed or step_id in self.in_progress:
                continue

            # Check dependencies
            if all(dep in self.executed for dep in step.depends_on):
                # Check capacity for service deployments
                if step.type == DeploymentType.DEPLOY_SERVICE:
                    if services_deploying >= self.max_parallel_deployments:
                        continue

                actions.append(DeploymentAction(step))

        # Sort by risk (lower first) and dependencies
        actions.sort(
            key=lambda a: (a.step.risk_level, len(a.step.depends_on))
        )

        return actions[:3]

    def apply_action(self, action: Any) -> bool:
        """Execute a deployment step."""
        if not isinstance(action, DeploymentAction):
            return False

        step = action.step

        # Verify not already executed
        if step.id in self.executed:
            return False

        # Verify dependencies
        if not all(dep in self.executed for dep in step.depends_on):
            return False

        # Mark as in progress
        self.in_progress.add(step.id)

        # Execute deployment step
        success, error = self._execute_deployment_step(step)

        # Remove from in progress
        self.in_progress.remove(step.id)

        if not success:
            print(f"Deployment step failed: {step.id} - {error}")

            # Check if we should rollback
            if step.risk_level >= 4 or step.type == DeploymentType.DEPLOY_SERVICE:
                self.rollback_required = True
                print("Initiating rollback due to critical failure")
                return False

        # Health check if required
        if step.health_check_required and success:
            health_ok = self._run_health_check(step)
            self.health_checks_passed[step.id] = health_ok

            if not health_ok:
                self.failed_health_checks += 1
                print(f"Health check failed for step: {step.id}")

                # Critical services failing health check trigger rollback
                if step.risk_level >= 4:
                    self.rollback_required = True
                    print("Initiating rollback due to failed health check")
                    return False

        # Update state
        self.executed.add(step.id)
        self.execution_order.append(step.id)
        self.total_time += step.estimated_time
        self.total_instances_deployed += step.instances_affected

        # Track service version if service deployment
        if step.type == DeploymentType.DEPLOY_SERVICE and step.service:
            self.service_versions[step.service] = self.services[step.service].version_new

        # Add to rollback stack if can rollback
        if step.can_rollback:
            self.rollback_stack.append(step)

        return True

    def _execute_deployment_step(
        self,
        step: DeploymentStep
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute a single deployment step.
        In real implementation, would call Kubernetes API, etc.
        """
        # Simulate execution
        import random

        # Simulate risk-based failure rate
        failure_rate = (step.risk_level - 1) * 0.03  # 0-12% based on risk
        success = random.random() > failure_rate

        if not success:
            return False, f"Deployment failed (risk level {step.risk_level})"

        return True, None

    def _run_health_check(self, step: DeploymentStep) -> bool:
        """
        Run health check for deployment step.
        In real implementation, would hit health endpoints.
        """
        import random

        # Simulate health check
        # Higher risk steps have higher chance of health check failure
        failure_rate = step.risk_level * 0.02
        return random.random() > failure_rate

    def is_complete(self) -> bool:
        """Check if deployment complete or rollback finished."""
        if self.rollback_required:
            # If rollback, we're complete when all rollbacks executed
            return len(self.rollback_stack) == 0 or all(
                step.rollback_step_id in self.executed
                for step in self.rollback_stack
                if step.rollback_step_id
            )

        return len(self.executed) == len(self.steps)

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()

        if not possible:
            return "No deployment steps ready (waiting on dependencies or at capacity)"

        # Format step options
        step_info = []
        for i, action in enumerate(possible, 1):
            step = action.step
            service_str = f"[{step.service}]" if step.service else "[infra]"
            deps_str = f"after: {step.depends_on}" if step.depends_on else "no deps"
            risk_str = "🔴" * step.risk_level
            rollback_str = "↩️" if step.can_rollback else "⚠️"

            step_info.append(
                f"  {i}. {step.id:40s} {service_str:15s}\n"
                f"      {step.type.value:20s} {deps_str}\n"
                f"      {risk_str} {rollback_str} ~{step.estimated_time}s, "
                f"{step.instances_affected} instances"
            )

        state = self.get_current_state()
        rollback_str = " ⚠️  ROLLBACK MODE" if self.rollback_required else ""

        return f"""You are executing distributed system deployment. Step {step_num}/{len(self.steps)}.{rollback_str}

Progress: {state['progress']} ({state['executed']}/{len(self.steps)})
In progress: {state['in_progress']} steps
Time elapsed: {state['total_time']}s
Instances deployed: {state['instances_deployed']}
Health checks failed: {state['health_checks_failed']}
Services updated: {state['services_updated']}/{len(self.services)}
All healthy: {'✓' if state['all_services_healthy'] else '✗'}

Parallel capacity: {len([s for s in self.in_progress if self.steps[s].type == DeploymentType.DEPLOY_SERVICE])}/{self.max_parallel_deployments}

Deployment steps ready to execute:
{chr(10).join(step_info)}

Which deployment step should be executed next?
Respond with just the number (1-{len(possible)}). No explanation."""

    def parse_action(self, response: str) -> Optional[DeploymentAction]:
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
        return len(self.executed) / len(self.steps)

    def estimate_steps(self) -> int:
        """Estimate steps needed."""
        return len(self.steps)

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate deployment completion."""
        if self.rollback_required:
            return False, "Deployment failed and required rollback"

        if not self.is_complete():
            return False, "Deployment incomplete"

        if self.failed_health_checks > 0:
            return False, f"{self.failed_health_checks} health checks failed"

        if not all(self.service_health.values()):
            return False, "Not all services are healthy"

        # Check all services updated
        all_updated = all(
            self.service_versions[name] == service.version_new
            for name, service in self.services.items()
        )

        if not all_updated:
            return False, "Not all services updated to new version"

        return True, (
            f"Deployment completed successfully!\n"
            f"Steps executed: {len(self.executed)}\n"
            f"Total time: {self.total_time}s ({self.total_time//60}m)\n"
            f"Instances deployed: {self.total_instances_deployed}\n"
            f"Services updated: {len(self.services)}\n"
            f"Health checks passed: {len([v for v in self.health_checks_passed.values() if v])}/{len(self.health_checks_passed)}\n"
            f"Zero downtime: ✓\n"
            f"All services healthy: ✓"
        )


# ============================================================================
# Example Usage
# ============================================================================

def create_microservices_deployment():
    """
    Create a realistic microservices deployment scenario.

    System: E-commerce platform
    - 5 microservices
    - 2 databases
    - Load balancer
    - Rolling deployment strategy
    """
    services = [
        Service(
            name="auth-service",
            version_old="v1.2.0",
            version_new="v1.3.0",
            instances=3,
            depends_on=[],
            requires_db_migration=True,
            is_stateful=False,
            health_check_endpoint="/health",
            rollout_strategy="canary",  # Critical service
            criticality=5
        ),
        Service(
            name="user-service",
            version_old="v2.1.0",
            version_new="v2.2.0",
            instances=4,
            depends_on=["auth-service"],
            requires_db_migration=True,
            is_stateful=False,
            health_check_endpoint="/health",
            rollout_strategy="rolling",
            criticality=4
        ),
        Service(
            name="product-service",
            version_old="v1.5.0",
            version_new="v1.6.0",
            instances=5,
            depends_on=["auth-service"],
            requires_db_migration=False,
            is_stateful=False,
            health_check_endpoint="/health",
            rollout_strategy="rolling",
            criticality=4
        ),
        Service(
            name="order-service",
            version_old="v3.0.0",
            version_new="v3.1.0",
            instances=4,
            depends_on=["auth-service", "user-service", "product-service"],
            requires_db_migration=True,
            is_stateful=True,  # Has order state
            health_check_endpoint="/health",
            rollout_strategy="canary",
            criticality=5
        ),
        Service(
            name="api-gateway",
            version_old="v2.0.0",
            version_new="v2.1.0",
            instances=3,
            depends_on=["auth-service", "user-service", "product-service", "order-service"],
            requires_db_migration=False,
            is_stateful=False,
            health_check_endpoint="/health",
            rollout_strategy="rolling",
            criticality=5
        ),
    ]

    # Generate deployment steps
    steps = []
    step_id = 0

    # Phase 1: Database migrations (must happen before service deployments)
    db_migration_steps = {}
    for service in services:
        if service.requires_db_migration:
            step_id += 1
            step = DeploymentStep(
                id=f"db_migrate_{service.name}",
                name=f"Migrate database for {service.name}",
                type=DeploymentType.DB_MIGRATION,
                service=service.name,
                depends_on=[],
                can_rollback=True,
                estimated_time=45,
                risk_level=4,
                instances_affected=0,
                health_check_required=True,
                rollback_step_id=f"rollback_db_{service.name}"
            )
            steps.append(step)
            db_migration_steps[service.name] = step.id

    # Phase 2: Service deployments (rolling updates)
    service_deploy_steps = {}
    for service in services:
        # Dependencies include own DB migration + dependent service deployments
        depends = []
        if service.requires_db_migration:
            depends.append(db_migration_steps[service.name])
        for dep_name in service.depends_on:
            if dep_name in service_deploy_steps:
                depends.append(service_deploy_steps[dep_name])

        if service.rollout_strategy == "canary":
            # Canary deployment: deploy to 1 instance, validate, then roll out
            step_id += 1
            canary_step = DeploymentStep(
                id=f"canary_{service.name}",
                name=f"Canary deploy {service.name} (1 instance)",
                type=DeploymentType.CANARY_DEPLOY,
                service=service.name,
                depends_on=depends,
                can_rollback=True,
                estimated_time=30,
                risk_level=service.criticality,
                instances_affected=1,
                health_check_required=True,
                rollback_step_id=f"rollback_{service.name}"
            )
            steps.append(canary_step)

            step_id += 1
            validate_step = DeploymentStep(
                id=f"validate_canary_{service.name}",
                name=f"Validate canary {service.name}",
                type=DeploymentType.CANARY_VALIDATE,
                service=service.name,
                depends_on=[canary_step.id],
                can_rollback=False,
                estimated_time=60,
                risk_level=service.criticality,
                instances_affected=0,
                health_check_required=True
            )
            steps.append(validate_step)

            step_id += 1
            promote_step = DeploymentStep(
                id=f"promote_{service.name}",
                name=f"Promote canary {service.name} (remaining instances)",
                type=DeploymentType.CANARY_PROMOTE,
                service=service.name,
                depends_on=[validate_step.id],
                can_rollback=True,
                estimated_time=service.instances * 20,
                risk_level=3,
                instances_affected=service.instances - 1,
                health_check_required=True,
                rollback_step_id=f"rollback_{service.name}"
            )
            steps.append(promote_step)
            service_deploy_steps[service.name] = promote_step.id

        else:  # Rolling deployment
            step_id += 1
            deploy_step = DeploymentStep(
                id=f"deploy_{service.name}",
                name=f"Rolling deploy {service.name} ({service.instances} instances)",
                type=DeploymentType.DEPLOY_SERVICE,
                service=service.name,
                depends_on=depends,
                can_rollback=True,
                estimated_time=service.instances * 25,
                risk_level=service.criticality,
                instances_affected=service.instances,
                health_check_required=True,
                rollback_step_id=f"rollback_{service.name}"
            )
            steps.append(deploy_step)
            service_deploy_steps[service.name] = deploy_step.id

    # Phase 3: Update load balancer (depends on all services)
    step_id += 1
    lb_step = DeploymentStep(
        id="update_load_balancer",
        name="Update load balancer configuration",
        type=DeploymentType.UPDATE_LB,
        service=None,
        depends_on=list(service_deploy_steps.values()),
        can_rollback=True,
        estimated_time=30,
        risk_level=4,
        instances_affected=1,
        health_check_required=True,
        rollback_step_id="rollback_lb"
    )
    steps.append(lb_step)

    # Phase 4: Smoke tests
    step_id += 1
    smoke_test_step = DeploymentStep(
        id="smoke_tests",
        name="Run smoke tests on deployed system",
        type=DeploymentType.SMOKE_TEST,
        service=None,
        depends_on=[lb_step.id],
        can_rollback=False,
        estimated_time=120,
        risk_level=2,
        instances_affected=0,
        health_check_required=False
    )
    steps.append(smoke_test_step)

    return services, steps


if __name__ == "__main__":
    print("="*80)
    print("COMPLEX SCENARIO 3: Distributed System Rolling Deployment")
    print("="*80)

    # Create deployment
    services, steps = create_microservices_deployment()

    total_instances = sum(s.instances for s in services)
    print(f"\nDeployment Overview:")
    print(f"Services: {len(services)}")
    print(f"Total instances: {total_instances}")
    print(f"Deployment steps: {len(steps)}")
    print(f"Critical steps (risk 4-5): {sum(1 for s in steps if s.risk_level >= 4)}")
    print(f"Canary deployments: {sum(1 for s in services if s.rollout_strategy == 'canary')}")
    print(f"Estimated time: {sum(s.estimated_time for s in steps)}s ({sum(s.estimated_time for s in steps)//60}m)")

    print(f"\nServices:")
    for service in services:
        print(f"  - {service.name}: {service.version_old} -> {service.version_new} "
              f"({service.instances} instances, {service.rollout_strategy})")

    # Create task
    task = DistributedDeploymentTask(
        services=services,
        deployment_steps=steps,
        max_parallel_deployments=2
    )

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=3,
        task_type="distributed_deployment",
        verbose=False,
        max_response_length=50
    )

    print("\n" + "="*80)
    print("Executing deployment with MAKER...")
    print("="*80)

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    if success:
        print("\n✓ Deployment completed successfully!")

        state = task.get_current_state()
        print(f"\nResults:")
        print(f"  Steps executed: {state['executed']}/{len(steps)}")
        print(f"  Total time: {state['total_time']}s ({state['total_time']//60}m)")
        print(f"  Instances deployed: {state['instances_deployed']}")
        print(f"  Services updated: {state['services_updated']}/{len(services)}")
        print(f"  Health checks failed: {state['health_checks_failed']}")
        print(f"  All services healthy: {'✓' if state['all_services_healthy'] else '✗'}")

        print(f"\nDeployment sequence (first 15 steps):")
        for i, step_id in enumerate(task.execution_order[:15], 1):
            step = task.steps[step_id]
            health_str = ""
            if step.id in task.health_checks_passed:
                health_str = " ✓" if task.health_checks_passed[step.id] else " ✗"
            risk_str = "🔴" * step.risk_level
            print(f"  {i:2d}. {step.id:40s} {risk_str}{health_str}")

        # Verify correctness
        is_valid, message = task.validate_solution()
        print(f"\nValidation:")
        print(f"  {message}")
    else:
        print("\n✗ Deployment failed or required rollback")
        print(f"  Rollback required: {task.rollback_required}")
        print(f"  Health checks failed: {task.failed_health_checks}")

    print(f"\nMAKER Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "="*80)
    print("Key Insights:")
    print("- MAKER coordinates complex multi-service deployments")
    print("- Database migrations executed before dependent services")
    print("- Canary deployments reduce risk for critical services")
    print("- Health checks validate each step")
    print("- Automatic rollback on critical failures")
    print("- Zero downtime achieved through careful orchestration")
    print("="*80)
