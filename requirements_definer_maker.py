"""
MAKER for Project Requirements Definition

Problem: LLM coding agents produce too much unnecessary code because
requirements are vague, incomplete, or misaligned.

Solution: Use MAKER to decompose and refine requirements step-by-step
with voting to ensure clarity, completeness, and alignment.

This is a META-MAKER application:
- Use MAKER to generate requirements
- Those requirements then guide other LLMs
- Prevents "LLM wants to spill out" syndrome
"""

from typing import List, Tuple, Optional, Any, Dict, Set
from dataclasses import dataclass
from enum import Enum
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


class RequirementType(Enum):
    """Types of requirements to define."""
    CORE_PURPOSE = "core_purpose"
    USER_STORY = "user_story"
    FEATURE = "feature"
    CONSTRAINT = "constraint"
    NON_GOAL = "non_goal"  # What NOT to build (critical!)
    TECH_STACK = "tech_stack"
    DATA_MODEL = "data_model"
    API_ENDPOINT = "api_endpoint"
    UI_COMPONENT = "ui_component"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"


class RequirementStatus(Enum):
    """Status of requirement definition."""
    NEEDED = "needed"
    DRAFT = "draft"
    VALIDATED = "validated"
    COMPLETE = "complete"


@dataclass
class Requirement:
    """A single project requirement."""
    id: str
    type: RequirementType
    description: str
    status: RequirementStatus
    priority: int  # 1-5, higher = more important
    depends_on: List[str]  # Other requirement IDs

    # Quality checks
    is_clear: bool = False  # No ambiguity
    is_testable: bool = False  # Can be verified
    is_minimal: bool = False  # Not over-specified

    # Validation notes
    validation_notes: List[str] = None

    def __post_init__(self):
        if self.validation_notes is None:
            self.validation_notes = []

    def __hash__(self):
        return hash(self.id)


@dataclass
class RequirementAction:
    """Represents defining/refining a requirement."""
    requirement: Requirement
    action: str  # "define", "refine", "validate", "mark_complete"

    def __str__(self):
        return f"{self.action}({self.requirement.id}: {self.requirement.type.value})"

    def __eq__(self, other):
        return (isinstance(other, RequirementAction) and
                self.requirement.id == other.requirement.id)

    def __hash__(self):
        return hash(self.requirement.id)


class ProjectRequirementsTask(DecomposableTask):
    """
    Define project requirements using MAKER approach.

    Key innovation: Use VOTING to ensure requirements are:
    - Clear (no ambiguity)
    - Complete (nothing missing)
    - Minimal (no unnecessary features)
    - Testable (verifiable)
    - Aligned (consistent with project goals)

    This prevents "LLM spill" where coding agents add unnecessary features.
    """

    def __init__(self, project_description: str):
        """
        Initialize project requirements definition.

        Args:
            project_description: High-level project description
        """
        self.project_description = project_description

        # Requirements tracking
        self.requirements = {}  # requirement_id -> Requirement
        self.completed_requirements = set()
        self.requirement_order = []

        # Quality metrics
        self.clarity_checks_passed = 0
        self.ambiguities_found = 0
        self.unnecessary_features_removed = 0

        # Project context
        self.core_purpose = None
        self.explicit_non_goals = []  # Critical: what NOT to build

    def get_current_state(self) -> Dict:
        """Get current requirements state."""
        return {
            "total_requirements": len(self.requirements),
            "completed": len(self.completed_requirements),
            "remaining": len(self.requirements) - len(self.completed_requirements),
            "by_type": self._count_by_type(),
            "quality_score": self._calculate_quality_score(),
            "has_core_purpose": self.core_purpose is not None,
            "has_non_goals": len(self.explicit_non_goals) > 0
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count requirements by type."""
        counts = {}
        for req in self.requirements.values():
            type_name = req.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def _calculate_quality_score(self) -> float:
        """Calculate overall requirements quality (0-1)."""
        if not self.requirements:
            return 0.0

        total_score = 0
        for req in self.requirements.values():
            if req.status == RequirementStatus.COMPLETE:
                score = 0
                if req.is_clear:
                    score += 0.33
                if req.is_testable:
                    score += 0.33
                if req.is_minimal:
                    score += 0.34
                total_score += score

        return total_score / len(self.requirements) if self.requirements else 0.0

    def get_possible_actions(self) -> List[RequirementAction]:
        """Get next requirements to define/refine."""
        actions = []

        # Phase 1: Must define core purpose first
        if self.core_purpose is None:
            req = Requirement(
                id="core_purpose",
                type=RequirementType.CORE_PURPOSE,
                description="",
                status=RequirementStatus.NEEDED,
                priority=5,
                depends_on=[]
            )
            return [RequirementAction(req, "define")]

        # Phase 2: Define explicit non-goals (what NOT to build)
        if len(self.explicit_non_goals) == 0:
            req = Requirement(
                id="non_goals",
                type=RequirementType.NON_GOAL,
                description="",
                status=RequirementStatus.NEEDED,
                priority=5,
                depends_on=["core_purpose"]
            )
            return [RequirementAction(req, "define")]

        # Phase 3: Define other requirements
        # Look for requirements that need definition
        for req_id, req in self.requirements.items():
            if req_id in self.completed_requirements:
                continue

            # Check dependencies
            if all(dep in self.completed_requirements for dep in req.depends_on):
                if req.status == RequirementStatus.NEEDED:
                    actions.append(RequirementAction(req, "define"))
                elif req.status == RequirementStatus.DRAFT:
                    actions.append(RequirementAction(req, "validate"))
                elif req.status == RequirementStatus.VALIDATED:
                    actions.append(RequirementAction(req, "mark_complete"))

        # If no existing requirements, suggest next types to define
        if not actions:
            actions = self._suggest_next_requirements()

        # Sort by priority
        actions.sort(key=lambda a: a.requirement.priority, reverse=True)

        return actions[:3]  # Top 3 for voting

    def _suggest_next_requirements(self) -> List[RequirementAction]:
        """Suggest next requirement types to define."""
        suggestions = []

        # Suggested order for requirement definition
        type_order = [
            RequirementType.USER_STORY,
            RequirementType.FEATURE,
            RequirementType.CONSTRAINT,
            RequirementType.DATA_MODEL,
            RequirementType.API_ENDPOINT,
            RequirementType.UI_COMPONENT,
            RequirementType.ACCEPTANCE_CRITERIA
        ]

        for req_type in type_order:
            # Check if we have this type
            has_type = any(
                req.type == req_type
                for req in self.requirements.values()
            )

            if not has_type:
                req = Requirement(
                    id=f"{req_type.value}_001",
                    type=req_type,
                    description="",
                    status=RequirementStatus.NEEDED,
                    priority=4,
                    depends_on=["core_purpose", "non_goals"]
                )
                suggestions.append(RequirementAction(req, "define"))
                break  # One at a time

        return suggestions

    def apply_action(self, action: Any) -> bool:
        """Define or refine a requirement."""
        if not isinstance(action, RequirementAction):
            return False

        req = action.requirement

        if action.action == "define":
            # Define the requirement (simulated - in real use, LLM provides definition)
            req.status = RequirementStatus.DRAFT
            req.description = self._simulate_requirement_definition(req)
            self.requirements[req.id] = req

            # Special handling
            if req.type == RequirementType.CORE_PURPOSE:
                self.core_purpose = req.description
            elif req.type == RequirementType.NON_GOAL:
                self.explicit_non_goals = req.description.split("\n")

        elif action.action == "validate":
            # Validate the requirement (check quality)
            req.is_clear = self._check_clarity(req)
            req.is_testable = self._check_testability(req)
            req.is_minimal = self._check_minimality(req)

            if req.is_clear and req.is_testable and req.is_minimal:
                req.status = RequirementStatus.VALIDATED
                self.clarity_checks_passed += 1
            else:
                # Needs refinement
                ambiguities = []
                if not req.is_clear:
                    ambiguities.append("Not clear enough")
                if not req.is_testable:
                    ambiguities.append("Not testable")
                if not req.is_minimal:
                    ambiguities.append("Over-specified")
                req.validation_notes.extend(ambiguities)
                self.ambiguities_found += len(ambiguities)
                return False  # Needs more work

        elif action.action == "mark_complete":
            req.status = RequirementStatus.COMPLETE
            self.completed_requirements.add(req.id)
            self.requirement_order.append(req.id)

        return True

    def _simulate_requirement_definition(self, req: Requirement) -> str:
        """Simulate defining a requirement (in real use, LLM provides this)."""
        if req.type == RequirementType.CORE_PURPOSE:
            return f"Build a {self.project_description} that solves X problem for Y users"
        elif req.type == RequirementType.NON_GOAL:
            return "Do NOT build:\n- Feature X\n- Integration Y\n- Complex feature Z"
        else:
            return f"Sample requirement for {req.type.value}"

    def _check_clarity(self, req: Requirement) -> bool:
        """Check if requirement is clear (no ambiguity)."""
        # Check for ambiguous words
        ambiguous_words = ["maybe", "might", "could", "possibly", "etc", "and so on"]
        return not any(word in req.description.lower() for word in ambiguous_words)

    def _check_testability(self, req: Requirement) -> bool:
        """Check if requirement is testable."""
        # Should have measurable outcomes
        testable_indicators = ["must", "shall", "will", "can", "should"]
        return any(word in req.description.lower() for word in testable_indicators)

    def _check_minimality(self, req: Requirement) -> bool:
        """Check if requirement is minimal (not over-specified)."""
        # Check for over-specification indicators
        over_spec_indicators = ["advanced", "sophisticated", "cutting-edge", "all possible"]
        return not any(phrase in req.description.lower() for phrase in over_spec_indicators)

    def is_complete(self) -> bool:
        """Check if requirements are complete."""
        # Need at least:
        # - Core purpose
        # - Non-goals
        # - 3+ user stories or features
        # - Acceptance criteria

        has_core = self.core_purpose is not None
        has_non_goals = len(self.explicit_non_goals) > 0

        feature_count = sum(
            1 for req in self.requirements.values()
            if req.type in [RequirementType.USER_STORY, RequirementType.FEATURE]
            and req.status == RequirementStatus.COMPLETE
        )

        has_acceptance = any(
            req.type == RequirementType.ACCEPTANCE_CRITERIA
            and req.status == RequirementStatus.COMPLETE
            for req in self.requirements.values()
        )

        return (has_core and has_non_goals and
                feature_count >= 3 and has_acceptance)

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()

        if not possible:
            return "No requirements ready to define"

        state = self.get_current_state()

        # Format action options
        action_info = []
        for i, action in enumerate(possible, 1):
            req = action.requirement
            action_info.append(
                f"  {i}. {action.action.upper()}: {req.type.value}\n"
                f"      Priority: {'🔴' * req.priority}\n"
                f"      Status: {req.status.value}"
            )

        return f"""You are defining project requirements. Step {step_num}.

Project: {self.project_description}

Current state:
  Total requirements: {state['total_requirements']}
  Completed: {state['completed']}
  Quality score: {state['quality_score']:.2f}
  Has core purpose: {'✓' if state['has_core_purpose'] else '✗'}
  Has non-goals: {'✓' if state['has_non_goals'] else '✗'}

Quality metrics:
  Clarity checks passed: {self.clarity_checks_passed}
  Ambiguities found: {self.ambiguities_found}

Next actions to take:
{chr(10).join(action_info)}

Which action should be taken next?
Respond with just the number (1-{len(possible)}). No explanation."""

    def parse_action(self, response: str) -> Optional[RequirementAction]:
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
        if not self.requirements:
            return 0.0
        return len(self.completed_requirements) / max(len(self.requirements), 10)

    def estimate_steps(self) -> int:
        """Estimate steps needed."""
        # Core purpose + non-goals + ~10 other requirements
        return 12

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate requirements are complete and high quality."""
        if not self.is_complete():
            return False, "Requirements not complete"

        quality_score = self._calculate_quality_score()
        if quality_score < 0.8:
            return False, f"Quality score too low: {quality_score:.2f}"

        return True, (
            f"Requirements complete and validated!\n"
            f"Total requirements: {len(self.requirements)}\n"
            f"Quality score: {quality_score:.2f}\n"
            f"Core purpose defined: ✓\n"
            f"Non-goals explicit: ✓ ({len(self.explicit_non_goals)} items)\n"
            f"Ready for implementation!"
        )

    def export_for_coding_agent(self) -> str:
        """Export requirements in format for coding agents."""
        output = []

        output.append("# PROJECT REQUIREMENTS")
        output.append(f"\n## Core Purpose\n{self.core_purpose}\n")

        output.append("\n## EXPLICIT NON-GOALS (Do NOT Build)")
        for non_goal in self.explicit_non_goals:
            output.append(f"- ✗ {non_goal}")

        output.append("\n## Requirements by Type\n")

        for req_type in RequirementType:
            reqs = [
                req for req in self.requirements.values()
                if req.type == req_type and req.status == RequirementStatus.COMPLETE
            ]

            if reqs:
                output.append(f"\n### {req_type.value.replace('_', ' ').title()}")
                for req in sorted(reqs, key=lambda r: r.priority, reverse=True):
                    priority_stars = "⭐" * req.priority
                    output.append(f"\n**{req.id}** {priority_stars}")
                    output.append(f"{req.description}")
                    output.append(f"- Clear: {'✓' if req.is_clear else '✗'}")
                    output.append(f"- Testable: {'✓' if req.is_testable else '✗'}")
                    output.append(f"- Minimal: {'✓' if req.is_minimal else '✗'}")

        output.append("\n## Implementation Constraints")
        output.append("- Build ONLY what is specified above")
        output.append("- Do NOT add features from the non-goals list")
        output.append("- Do NOT add 'nice-to-have' features without approval")
        output.append("- Keep implementation minimal and focused")

        return "\n".join(output)


if __name__ == "__main__":
    print("="*80)
    print("MAKER for Project Requirements Definition")
    print("="*80)

    # Example project
    project_desc = "a simple task management API with user authentication"

    print(f"\nProject: {project_desc}")
    print("\nDefining requirements using MAKER...")

    # Create task
    task = ProjectRequirementsTask(project_desc)

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=2,
        task_type="project_requirements",
        verbose=False
    )

    # Run MAKER
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    if success:
        print("\n✓ Requirements defined successfully!")

        # Show results
        state = task.get_current_state()
        print(f"\nRequirements summary:")
        print(f"  Total: {state['total_requirements']}")
        print(f"  Completed: {state['completed']}")
        print(f"  Quality score: {state['quality_score']:.2f}")

        print(f"\nBy type:")
        for type_name, count in state['by_type'].items():
            print(f"  {type_name}: {count}")

        # Export for coding agent
        print("\n" + "="*80)
        print("REQUIREMENTS FOR CODING AGENT")
        print("="*80)
        print(task.export_for_coding_agent())

        # Validation
        is_valid, message = task.validate_solution()
        print(f"\nValidation: {message}")
    else:
        print("\n✗ Requirements definition incomplete")

    print(f"\nMAKER Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
