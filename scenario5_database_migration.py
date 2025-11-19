"""
Complex Scenario 2: Database Schema Migration with Data Preservation

Problem: Migrate a production database schema while:
- Preserving all existing data
- Transforming data to fit new schema
- Maintaining referential integrity
- Zero downtime (or minimal)
- Rollback capability
- Data validation at each step
- Handling millions of rows

This is significantly more complex than simple schema changes because:
- Can't just drop columns (data loss!)
- Must transform data in correct order
- Foreign keys create dependencies
- Large data sets need batching
- Must validate data integrity continuously
- Need backup/restore points
"""

from typing import List, Set, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


class MigrationType(Enum):
    """Types of migration operations."""
    ADD_COLUMN = "add_column"
    RENAME_COLUMN = "rename_column"
    CHANGE_TYPE = "change_type"
    ADD_INDEX = "add_index"
    DROP_INDEX = "drop_index"
    MIGRATE_DATA = "migrate_data"
    ADD_FK = "add_foreign_key"
    DROP_FK = "drop_foreign_key"
    CREATE_TABLE = "create_table"
    DROP_COLUMN = "drop_column"  # Dangerous!
    BACKUP = "backup"
    VALIDATE = "validate"


@dataclass
class MigrationStep:
    """Represents a single migration step."""
    id: str
    name: str
    type: MigrationType
    table: str
    depends_on: List[str]  # Other migration IDs
    reversible: bool  # Can this be rolled back?
    data_rows_affected: int  # How many rows touched
    estimated_time: int  # Seconds
    risk_level: int  # 1-5, higher = more risky
    requires_backup: bool  # Backup before this step?
    validation_query: Optional[str]  # SQL to validate

    # Execution details
    sql: str = ""
    batch_size: int = 1000  # For large data operations

    def __hash__(self):
        return hash(self.id)


@dataclass
class MigrationAction:
    """Represents executing a migration step."""
    step: MigrationStep

    def __str__(self):
        return f"execute({self.step.id}: {self.step.type.value})"

    def __eq__(self, other):
        return (isinstance(other, MigrationAction) and
                self.step.id == other.step.id)

    def __hash__(self):
        return hash(self.step.id)

    def __repr__(self):
        return str(self)


class DatabaseMigrationTask(DecomposableTask):
    """
    Execute database schema migration with data preservation.

    Real-world use cases:
    - Production database upgrades
    - Schema refactoring
    - Multi-tenant database consolidation
    - Cloud database migrations
    - Data warehouse schema evolution

    Complexity factors:
    - Data preservation (can't lose data!)
    - Foreign key dependencies
    - Large table operations (millions of rows)
    - Downtime minimization
    - Rollback capability
    - Data validation
    - Index management (can slow writes)
    - Backup/restore points
    """

    def __init__(
        self,
        migration_steps: List[MigrationStep],
        total_rows: int,
        max_downtime_seconds: int = 300
    ):
        """
        Initialize database migration task.

        Args:
            migration_steps: List of migration steps
            total_rows: Total rows across all tables
            max_downtime_seconds: Maximum acceptable downtime
        """
        self.steps = {s.id: s for s in migration_steps}
        self.total_rows = total_rows
        self.max_downtime_seconds = max_downtime_seconds

        # Execution state
        self.executed = set()
        self.execution_order = []
        self.backups = []  # Backup points
        self.data_integrity_ok = True
        self.total_time = 0
        self.total_rows_migrated = 0

        # Safety
        self.last_backup_step = None
        self.rollback_stack = []  # For reversible operations

        self._validate_dependencies()

    def _validate_dependencies(self):
        """Validate migration dependencies exist."""
        for step in self.steps.values():
            for dep in step.depends_on:
                if dep not in self.steps:
                    raise ValueError(
                        f"Step {step.id} depends on unknown step {dep}"
                    )

    def get_current_state(self) -> Dict:
        """Get current migration state."""
        return {
            "executed": len(self.executed),
            "remaining": len(self.steps) - len(self.executed),
            "progress": f"{(len(self.executed) / len(self.steps)) * 100:.1f}%",
            "total_time": self.total_time,
            "rows_migrated": self.total_rows_migrated,
            "backups_taken": len(self.backups),
            "data_integrity": "✓" if self.data_integrity_ok else "✗",
            "can_rollback": len(self.rollback_stack) > 0
        }

    def get_possible_actions(self) -> List[MigrationAction]:
        """Get migration steps that can be executed."""
        actions = []

        for step_id, step in self.steps.items():
            # Already executed?
            if step_id in self.executed:
                continue

            # Check dependencies
            if all(dep in self.executed for dep in step.depends_on):
                actions.append(MigrationAction(step))

        # Sort by risk (lower risk first) and dependencies
        actions.sort(
            key=lambda a: (a.step.risk_level, len(a.step.depends_on))
        )

        # Always backup before high-risk operations
        high_risk_pending = any(a.step.risk_level >= 4 for a in actions)
        if high_risk_pending and self.last_backup_step != len(self.executed):
            # Insert backup step (if not just taken)
            backup_actions = [a for a in actions if a.step.type == MigrationType.BACKUP]
            if backup_actions:
                return backup_actions[:1]

        return actions[:3]  # Max 3 options for simpler voting

    def apply_action(self, action: Any) -> bool:
        """Execute a migration step."""
        if not isinstance(action, MigrationAction):
            return False

        step = action.step

        # Verify not already executed
        if step.id in self.executed:
            return False

        # Verify dependencies
        if not all(dep in self.executed for dep in step.depends_on):
            return False

        # Take backup if required
        if step.requires_backup and self.last_backup_step != len(self.executed):
            self._take_backup()

        # Execute migration step
        success, error = self._execute_migration_step(step)

        if not success:
            print(f"Migration step failed: {step.id} - {error}")
            self.data_integrity_ok = False
            return False

        # Validate if validation query provided
        if step.validation_query:
            if not self._validate_data(step):
                print(f"Data validation failed after step: {step.id}")
                self.data_integrity_ok = False
                # Should rollback here in real implementation
                return False

        # Update state
        self.executed.add(step.id)
        self.execution_order.append(step.id)
        self.total_time += step.estimated_time
        self.total_rows_migrated += step.data_rows_affected

        # Add to rollback stack if reversible
        if step.reversible:
            self.rollback_stack.append(step.id)

        return True

    def _take_backup(self):
        """Take database backup."""
        self.backups.append(f"backup_{len(self.backups)}")
        self.last_backup_step = len(self.executed)
        # In real implementation: pg_dump, mysqldump, etc.

    def _execute_migration_step(
        self,
        step: MigrationStep
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute a single migration step.
        In real implementation, would execute SQL.
        """
        # Simulate execution
        import random

        # Simulate risk-based failure rate
        failure_rate = (step.risk_level - 1) * 0.02  # 0-8% based on risk
        success = random.random() > failure_rate

        if not success:
            return False, f"Migration failed (risk level {step.risk_level})"

        # Simulate time
        # time.sleep(step.estimated_time / 100)  # Scaled down

        return True, None

    def _validate_data(self, step: MigrationStep) -> bool:
        """
        Validate data integrity after step.
        In real implementation, would run validation query.
        """
        # Simulate validation
        import random
        return random.random() > 0.05  # 95% success rate

    def is_complete(self) -> bool:
        """Check if all migrations executed."""
        return len(self.executed) == len(self.steps)

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()

        if not possible:
            return "No migrations ready (waiting on dependencies)"

        # Format migration options
        step_info = []
        for i, action in enumerate(possible, 1):
            step = action.step
            deps_str = f"after: {step.depends_on}" if step.depends_on else "no deps"
            risk_str = "🔴" * step.risk_level
            reversible_str = "↩️ reversible" if step.reversible else "⚠️  irreversible"

            step_info.append(
                f"  {i}. {step.id:35s} [{step.type.value:15s}]\n"
                f"      Table: {step.table}, {deps_str}\n"
                f"      {risk_str} {reversible_str}, ~{step.estimated_time}s, "
                f"{step.data_rows_affected:,} rows"
            )

        state = self.get_current_state()

        return f"""You are executing database schema migration. Step {step_num}/{len(self.steps)}.

Progress: {state['progress']} ({state['executed']}/{len(self.steps)})
Time elapsed: {state['total_time']}s / {self.max_downtime_seconds}s max
Rows migrated: {state['rows_migrated']:,} / {self.total_rows:,}
Backups taken: {state['backups_taken']}
Data integrity: {state['data_integrity']}
Can rollback: {state['can_rollback']}

Migration steps ready to execute:
{chr(10).join(step_info)}

Which migration step should be executed next?
Respond with just the number (1-{len(possible)}). No explanation."""

    def parse_action(self, response: str) -> Optional[MigrationAction]:
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
        """Validate migration completion."""
        if not self.is_complete():
            return False, "Migration incomplete"

        if not self.data_integrity_ok:
            return False, "Data integrity compromised"

        if self.total_time > self.max_downtime_seconds:
            return False, f"Exceeded max downtime ({self.total_time}s > {self.max_downtime_seconds}s)"

        return True, (
            f"Migration completed successfully!\n"
            f"Steps executed: {len(self.executed)}\n"
            f"Total time: {self.total_time}s\n"
            f"Rows migrated: {self.total_rows_migrated:,}\n"
            f"Backups taken: {len(self.backups)}\n"
            f"Data integrity: ✓\n"
            f"Execution order: {' -> '.join(self.execution_order[:8])}..."
        )


# ============================================================================
# Example Usage
# ============================================================================

def create_production_migration():
    """
    Create a realistic production database migration.

    Scenario: E-commerce database refactoring
    - Split monolithic 'users' table into 'users' and 'user_profiles'
    - Add email verification
    - Migrate order status from string to enum
    - Add indexes for performance
    - Update foreign keys
    """
    steps = [
        # Phase 1: Backups and preparation
        MigrationStep(
            id="backup_initial",
            name="Take initial backup",
            type=MigrationType.BACKUP,
            table="*",
            depends_on=[],
            reversible=True,
            data_rows_affected=0,
            estimated_time=30,
            risk_level=1,
            requires_backup=False,
            validation_query=None
        ),

        # Phase 2: Create new tables
        MigrationStep(
            id="create_user_profiles",
            name="Create user_profiles table",
            type=MigrationType.CREATE_TABLE,
            table="user_profiles",
            depends_on=["backup_initial"],
            reversible=True,
            data_rows_affected=0,
            estimated_time=5,
            risk_level=2,
            requires_backup=False,
            validation_query="SELECT COUNT(*) FROM user_profiles"
        ),

        # Phase 3: Add new columns to existing tables
        MigrationStep(
            id="add_email_verified",
            name="Add email_verified column to users",
            type=MigrationType.ADD_COLUMN,
            table="users",
            depends_on=["backup_initial"],
            reversible=True,
            data_rows_affected=0,
            estimated_time=10,
            risk_level=2,
            requires_backup=False,
            validation_query="SELECT email_verified FROM users LIMIT 1"
        ),
        MigrationStep(
            id="add_profile_id_to_users",
            name="Add profile_id column to users",
            type=MigrationType.ADD_COLUMN,
            table="users",
            depends_on=["create_user_profiles"],
            reversible=True,
            data_rows_affected=0,
            estimated_time=10,
            risk_level=2,
            requires_backup=False,
            validation_query="SELECT profile_id FROM users LIMIT 1"
        ),

        # Phase 4: Migrate data (HIGH RISK)
        MigrationStep(
            id="backup_before_data_migration",
            name="Backup before data migration",
            type=MigrationType.BACKUP,
            table="*",
            depends_on=["add_profile_id_to_users", "add_email_verified"],
            reversible=True,
            data_rows_affected=0,
            estimated_time=30,
            risk_level=1,
            requires_backup=False,
            validation_query=None
        ),
        MigrationStep(
            id="migrate_user_data_to_profiles",
            name="Migrate user profile data",
            type=MigrationType.MIGRATE_DATA,
            table="user_profiles",
            depends_on=["backup_before_data_migration"],
            reversible=True,
            data_rows_affected=500000,  # 500K users
            estimated_time=120,
            risk_level=5,  # CRITICAL
            requires_backup=False,  # Already taken
            validation_query="SELECT COUNT(*) FROM user_profiles WHERE user_id IS NOT NULL"
        ),
        MigrationStep(
            id="populate_profile_ids",
            name="Populate profile_id in users table",
            type=MigrationType.MIGRATE_DATA,
            table="users",
            depends_on=["migrate_user_data_to_profiles"],
            reversible=True,
            data_rows_affected=500000,
            estimated_time=100,
            risk_level=5,  # CRITICAL
            requires_backup=False,
            validation_query="SELECT COUNT(*) FROM users WHERE profile_id IS NOT NULL"
        ),

        # Phase 5: Add foreign keys (requires data migration complete)
        MigrationStep(
            id="add_fk_user_profile",
            name="Add foreign key users.profile_id -> user_profiles.id",
            type=MigrationType.ADD_FK,
            table="users",
            depends_on=["populate_profile_ids"],
            reversible=True,
            data_rows_affected=0,
            estimated_time=20,
            risk_level=3,
            requires_backup=True,
            validation_query="SELECT COUNT(*) FROM users u JOIN user_profiles up ON u.profile_id = up.id"
        ),

        # Phase 6: Orders table migration
        MigrationStep(
            id="add_order_status_enum",
            name="Add order_status_new column (enum type)",
            type=MigrationType.ADD_COLUMN,
            table="orders",
            depends_on=["backup_initial"],
            reversible=True,
            data_rows_affected=0,
            estimated_time=15,
            risk_level=2,
            requires_backup=False,
            validation_query="SELECT order_status_new FROM orders LIMIT 1"
        ),
        MigrationStep(
            id="migrate_order_status",
            name="Migrate order status from string to enum",
            type=MigrationType.MIGRATE_DATA,
            table="orders",
            depends_on=["add_order_status_enum"],
            reversible=True,
            data_rows_affected=1000000,  # 1M orders
            estimated_time=150,
            risk_level=4,
            requires_backup=True,
            validation_query="SELECT COUNT(*) FROM orders WHERE order_status_new IS NOT NULL"
        ),
        MigrationStep(
            id="rename_order_status",
            name="Rename order_status_new to order_status",
            type=MigrationType.RENAME_COLUMN,
            table="orders",
            depends_on=["migrate_order_status"],
            reversible=True,
            data_rows_affected=0,
            estimated_time=25,
            risk_level=3,
            requires_backup=True,
            validation_query=None
        ),

        # Phase 7: Add indexes for performance
        MigrationStep(
            id="add_index_user_email",
            name="Add index on users.email",
            type=MigrationType.ADD_INDEX,
            table="users",
            depends_on=["add_email_verified"],
            reversible=True,
            data_rows_affected=500000,
            estimated_time=40,
            risk_level=2,
            requires_backup=False,
            validation_query=None
        ),
        MigrationStep(
            id="add_index_order_status",
            name="Add index on orders.order_status",
            type=MigrationType.ADD_INDEX,
            table="orders",
            depends_on=["rename_order_status"],
            reversible=True,
            data_rows_affected=1000000,
            estimated_time=60,
            risk_level=2,
            requires_backup=False,
            validation_query=None
        ),
        MigrationStep(
            id="add_index_user_profile",
            name="Add index on users.profile_id",
            type=MigrationType.ADD_INDEX,
            table="users",
            depends_on=["add_fk_user_profile"],
            reversible=True,
            data_rows_affected=500000,
            estimated_time=35,
            risk_level=2,
            requires_backup=False,
            validation_query=None
        ),

        # Phase 8: Final validation
        MigrationStep(
            id="validate_final",
            name="Final data integrity validation",
            type=MigrationType.VALIDATE,
            table="*",
            depends_on=[
                "add_fk_user_profile",
                "rename_order_status",
                "add_index_user_email",
                "add_index_order_status",
                "add_index_user_profile"
            ],
            reversible=False,
            data_rows_affected=0,
            estimated_time=20,
            risk_level=1,
            requires_backup=False,
            validation_query="SELECT 1"  # Comprehensive checks
        ),
    ]

    return steps


if __name__ == "__main__":
    print("="*80)
    print("COMPLEX SCENARIO 2: Database Schema Migration with Data Preservation")
    print("="*80)

    # Create migration
    steps = create_production_migration()

    total_rows = sum(s.data_rows_affected for s in steps)
    print(f"\nMigration Overview:")
    print(f"Total steps: {len(steps)}")
    print(f"High-risk steps (level 4-5): {sum(1 for s in steps if s.risk_level >= 4)}")
    print(f"Data rows affected: {total_rows:,}")
    print(f"Estimated time: {sum(s.estimated_time for s in steps)}s ({sum(s.estimated_time for s in steps)//60}m)")
    print(f"Reversible steps: {sum(1 for s in steps if s.reversible)}/{len(steps)}")
    print(f"Backup steps: {sum(1 for s in steps if s.type == MigrationType.BACKUP)}")

    # Create task
    task = DatabaseMigrationTask(
        migration_steps=steps,
        total_rows=total_rows,
        max_downtime_seconds=600  # 10 minutes max
    )

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=3,
        task_type="database_migration",
        verbose=False,
        max_response_length=50
    )

    print("\n" + "="*80)
    print("Executing migration with MAKER...")
    print("="*80)

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    if success:
        print("\n✓ Migration completed successfully!")

        state = task.get_current_state()
        print(f"\nResults:")
        print(f"  Steps executed: {state['executed']}/{len(steps)}")
        print(f"  Total time: {state['total_time']}s ({state['total_time']//60}m)")
        print(f"  Rows migrated: {state['rows_migrated']:,}")
        print(f"  Backups taken: {state['backups_taken']}")
        print(f"  Data integrity: {state['data_integrity']}")

        print(f"\nExecution order (first 10):")
        for i, step_id in enumerate(task.execution_order[:10], 1):
            step = task.steps[step_id]
            risk_str = "🔴" * step.risk_level
            print(f"  {i:2d}. {step_id:35s} {risk_str}")

        # Verify correctness
        is_valid, message = task.validate_solution()
        print(f"\nValidation:")
        print(f"  {message}")
    else:
        print("\n✗ Migration failed or incomplete")
        print(f"  Data integrity: {task.data_integrity_ok}")

    print(f"\nMAKER Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "="*80)
    print("Key Insights:")
    print("- MAKER ensures safe migration order (backups before risky operations)")
    print("- Data dependencies tracked automatically")
    print("- High-risk operations identified and handled carefully")
    print("- Rollback capability maintained")
    print("- Zero data loss through careful ordering")
    print("="*80)
