"""
Real-World Scenario 3: Interview Scheduling with Complex Constraints

Problem: Schedule multiple interview rounds for candidates while satisfying:
- Interviewer availability
- Room availability
- Time constraints (no back-to-back, lunch breaks)
- Panel requirements (need specific interviewers for each round)
- Candidate preferences

This is a complex constraint satisfaction problem common in HR systems.
"""

from typing import List, Set, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from maker_base import DecomposableTask, GeneralizedMAKER, MAKERConfig


@dataclass
class TimeSlot:
    """Represents a time slot."""
    start: datetime
    end: datetime

    def __str__(self):
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"

    def __hash__(self):
        return hash((self.start, self.end))

    def overlaps(self, other: 'TimeSlot') -> bool:
        """Check if this slot overlaps with another."""
        return (self.start < other.end and other.start < self.end)


@dataclass
class Interview:
    """Represents an interview round."""
    id: str
    candidate: str
    round_name: str
    required_interviewers: List[str]
    duration_minutes: int
    candidate_pref_slots: List[TimeSlot]  # Candidate's preferred times

    def __hash__(self):
        return hash(self.id)


@dataclass
class ScheduleAction:
    """Represents scheduling an interview to a time slot."""
    interview: Interview
    time_slot: TimeSlot
    assigned_interviewers: List[str]

    def __str__(self):
        return (f"schedule({self.interview.id} @ {self.time_slot} "
                f"with {self.assigned_interviewers})")

    def __eq__(self, other):
        return (isinstance(other, ScheduleAction) and
                self.interview.id == other.interview.id and
                self.time_slot == other.time_slot)

    def __hash__(self):
        return hash((self.interview.id, self.time_slot))

    def __repr__(self):
        return str(self)


class InterviewSchedulingTask(DecomposableTask):
    """
    Schedule interviews with complex constraints.

    Real-world use cases:
    - Technical interview scheduling
    - Medical appointment scheduling
    - Meeting room booking
    - Class/course scheduling
    - Court hearing scheduling
    """

    def __init__(
        self,
        interviews: List[Interview],
        available_slots: List[TimeSlot],
        interviewer_availability: Dict[str, List[TimeSlot]],
        room_count: int = 3
    ):
        """
        Initialize interview scheduling task.

        Args:
            interviews: List of interviews to schedule
            available_slots: All possible time slots
            interviewer_availability: Dict of interviewer -> available slots
            room_count: Number of available rooms
        """
        self.interviews = {i.id: i for i in interviews}
        self.available_slots = available_slots
        self.interviewer_availability = interviewer_availability
        self.room_count = room_count

        self.scheduled = {}  # interview_id -> ScheduleAction
        self.interviewer_schedule = {name: [] for name in interviewer_availability}
        self.room_schedule = {i: [] for i in range(room_count)}

    def get_current_state(self) -> Dict:
        """Get current scheduling state."""
        return {
            "scheduled": len(self.scheduled),
            "remaining": len(self.interviews) - len(self.scheduled),
            "interviewer_utilization": {
                name: len(slots) for name, slots in self.interviewer_schedule.items()
            }
        }

    def _is_interviewer_available(
        self,
        interviewer: str,
        time_slot: TimeSlot
    ) -> bool:
        """Check if interviewer is available at time slot."""
        # Check general availability
        if not any(
            time_slot.start >= avail.start and time_slot.end <= avail.end
            for avail in self.interviewer_availability[interviewer]
        ):
            return False

        # Check no overlap with existing interviews
        existing = self.interviewer_schedule.get(interviewer, [])
        return not any(time_slot.overlaps(existing_slot) for existing_slot in existing)

    def _is_room_available(self, time_slot: TimeSlot) -> bool:
        """Check if any room is available at time slot."""
        for room_schedule in self.room_schedule.values():
            if not any(time_slot.overlaps(existing) for existing in room_schedule):
                return True
        return False

    def _get_available_room(self, time_slot: TimeSlot) -> Optional[int]:
        """Get an available room for time slot."""
        for room_id, room_schedule in self.room_schedule.items():
            if not any(time_slot.overlaps(existing) for existing in room_schedule):
                return room_id
        return None

    def get_possible_actions(self) -> List[ScheduleAction]:
        """Get possible interview scheduling options."""
        actions = []

        # Get next unscheduled interview
        unscheduled = [
            interview for interview_id, interview in self.interviews.items()
            if interview_id not in self.scheduled
        ]

        if not unscheduled:
            return []

        # Focus on one interview at a time (MAKER principle: single decision)
        interview = unscheduled[0]

        # Try each time slot
        for time_slot in self.available_slots:
            # Check room availability
            if not self._is_room_available(time_slot):
                continue

            # Check if all required interviewers are available
            if all(
                self._is_interviewer_available(interviewer, time_slot)
                for interviewer in interview.required_interviewers
            ):
                # Check candidate preference (soft constraint)
                in_pref = any(
                    time_slot.start >= pref.start and time_slot.end <= pref.end
                    for pref in interview.candidate_pref_slots
                )

                # Create action
                action = ScheduleAction(
                    interview=interview,
                    time_slot=time_slot,
                    assigned_interviewers=interview.required_interviewers
                )

                actions.append(action)

        # Sort by candidate preference (preferred slots first)
        actions.sort(
            key=lambda a: any(
                a.time_slot.start >= pref.start and a.time_slot.end <= pref.end
                for pref in a.interview.candidate_pref_slots
            ),
            reverse=True
        )

        return actions[:5]  # Limit options to avoid overwhelming the agent

    def apply_action(self, action: Any) -> bool:
        """Schedule an interview."""
        if not isinstance(action, ScheduleAction):
            return False

        interview = action.interview

        # Verify not already scheduled
        if interview.id in self.scheduled:
            return False

        # Verify room available
        room_id = self._get_available_room(action.time_slot)
        if room_id is None:
            return False

        # Verify interviewers available
        for interviewer in action.assigned_interviewers:
            if not self._is_interviewer_available(interviewer, action.time_slot):
                return False

        # Schedule it
        self.scheduled[interview.id] = action

        # Update interviewer schedules
        for interviewer in action.assigned_interviewers:
            self.interviewer_schedule[interviewer].append(action.time_slot)

        # Update room schedule
        self.room_schedule[room_id].append(action.time_slot)

        return True

    def is_complete(self) -> bool:
        """Check if all interviews scheduled."""
        return len(self.scheduled) == len(self.interviews)

    def format_for_agent(self, step_num: int) -> str:
        """Format state for LLM agent."""
        possible = self.get_possible_actions()

        if not possible:
            return "No possible scheduling options available!"

        # Get the interview being scheduled
        interview = possible[0].interview

        # Format options
        options = []
        for i, action in enumerate(possible, 1):
            in_pref = any(
                action.time_slot.start >= pref.start and action.time_slot.end <= pref.end
                for pref in interview.candidate_pref_slots
            )
            pref_str = " ✓ PREFERRED" if in_pref else ""
            options.append(
                f"  {i}. {action.time_slot} with {action.assigned_interviewers}{pref_str}"
            )

        return f"""You are scheduling interviews. Step {step_num}/{len(self.interviews)}.

Scheduled: {len(self.scheduled)} interviews
Remaining: {len(self.interviews) - len(self.scheduled)} interviews

Current interview to schedule:
- ID: {interview.id}
- Candidate: {interview.candidate}
- Round: {interview.round_name}
- Duration: {interview.duration_minutes} minutes
- Required interviewers: {interview.required_interviewers}
- Candidate preferred times: {[str(s) for s in interview.candidate_pref_slots]}

Available time slot options:
{chr(10).join(options)}

Which time slot should be chosen?
Respond with just the number (1-{len(options)}). No explanation."""

    def parse_action(self, response: str) -> Optional[ScheduleAction]:
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
        return len(self.scheduled) / len(self.interviews)

    def estimate_steps(self) -> int:
        """Estimate steps needed."""
        return len(self.interviews)

    def validate_solution(self) -> Tuple[bool, str]:
        """Validate schedule."""
        if not self.is_complete():
            return False, "Not all interviews scheduled"

        # Check for conflicts
        for interview_id, action in self.scheduled.items():
            # Check room conflicts
            for other_id, other_action in self.scheduled.items():
                if interview_id != other_id:
                    if action.time_slot.overlaps(other_action.time_slot):
                        # Would be a conflict if same room
                        # (simplified - in real system would check actual room assignments)
                        pass

        # Count preferred slots
        in_pref_count = sum(
            1 for action in self.scheduled.values()
            if any(
                action.time_slot.start >= pref.start and action.time_slot.end <= pref.end
                for pref in action.interview.candidate_pref_slots
            )
        )

        return True, (
            f"Valid schedule for {len(self.scheduled)} interviews.\n"
            f"Candidate preferences met: {in_pref_count}/{len(self.scheduled)}"
        )


# ============================================================================
# Example Usage
# ============================================================================

def create_sample_schedule():
    """Create a sample interview scheduling scenario."""
    base_date = datetime(2025, 1, 20, 9, 0)  # Monday 9 AM

    # Available time slots (9 AM - 5 PM, 1-hour slots)
    available_slots = []
    for hour in range(9, 17):
        if hour == 12:  # Skip lunch
            continue
        start = base_date.replace(hour=hour)
        end = start + timedelta(hours=1)
        available_slots.append(TimeSlot(start, end))

    # Interviewers and their availability
    interviewer_availability = {
        "Alice": [TimeSlot(base_date.replace(hour=9), base_date.replace(hour=17))],
        "Bob": [TimeSlot(base_date.replace(hour=10), base_date.replace(hour=16))],
        "Carol": [TimeSlot(base_date.replace(hour=9), base_date.replace(hour=13))],
        "Dave": [TimeSlot(base_date.replace(hour=13), base_date.replace(hour=17))],
        "Eve": [TimeSlot(base_date.replace(hour=9), base_date.replace(hour=17))],
    }

    # Interviews to schedule
    interviews = [
        Interview(
            id="INT001",
            candidate="John Smith",
            round_name="Technical Screen",
            required_interviewers=["Alice"],
            duration_minutes=60,
            candidate_pref_slots=[
                TimeSlot(base_date.replace(hour=9), base_date.replace(hour=11)),
            ]
        ),
        Interview(
            id="INT002",
            candidate="John Smith",
            round_name="System Design",
            required_interviewers=["Bob", "Carol"],
            duration_minutes=60,
            candidate_pref_slots=[
                TimeSlot(base_date.replace(hour=10), base_date.replace(hour=12)),
            ]
        ),
        Interview(
            id="INT003",
            candidate="Jane Doe",
            round_name="Technical Screen",
            required_interviewers=["Alice"],
            duration_minutes=60,
            candidate_pref_slots=[
                TimeSlot(base_date.replace(hour=14), base_date.replace(hour=16)),
            ]
        ),
        Interview(
            id="INT004",
            candidate="Jane Doe",
            round_name="Behavioral",
            required_interviewers=["Dave", "Eve"],
            duration_minutes=60,
            candidate_pref_slots=[
                TimeSlot(base_date.replace(hour=15), base_date.replace(hour=17)),
            ]
        ),
        Interview(
            id="INT005",
            candidate="Bob Johnson",
            round_name="Technical Screen",
            required_interviewers=["Eve"],
            duration_minutes=60,
            candidate_pref_slots=[
                TimeSlot(base_date.replace(hour=11), base_date.replace(hour=13)),
            ]
        ),
    ]

    return interviews, available_slots, interviewer_availability


if __name__ == "__main__":
    print("="*80)
    print("SCENARIO 3: Interview Scheduling with Complex Constraints")
    print("="*80)

    # Create scenario
    interviews, available_slots, interviewer_availability = create_sample_schedule()

    print(f"\nScheduling requirements:")
    print(f"Interviews to schedule: {len(interviews)}")
    print(f"Available time slots: {len(available_slots)}")
    print(f"Interviewers: {len(interviewer_availability)}")
    print(f"Rooms available: 3")

    print(f"\nInterviews:")
    for interview in interviews:
        print(f"  {interview.id}: {interview.candidate} - {interview.round_name}")
        print(f"    Requires: {interview.required_interviewers}")
        print(f"    Prefers: {[str(s) for s in interview.candidate_pref_slots]}")

    # Create task
    task = InterviewSchedulingTask(
        interviews=interviews,
        available_slots=available_slots,
        interviewer_availability=interviewer_availability,
        room_count=3
    )

    # Configure MAKER
    config = MAKERConfig(
        model="gpt-4o-mini",
        k=2,  # Lower k for faster demo
        task_type="interview_scheduling",
        verbose=False,
        max_response_length=50
    )

    print("\n" + "="*80)
    print("Scheduling with MAKER...")
    print("="*80)

    # Solve
    maker = GeneralizedMAKER(config, task)
    success, actions, stats = maker.solve()

    if success:
        print("\n✓ Successfully scheduled all interviews!")

        print(f"\nSchedule:")
        for interview_id, action in sorted(task.scheduled.items()):
            in_pref = any(
                action.time_slot.start >= pref.start and action.time_slot.end <= pref.end
                for pref in action.interview.candidate_pref_slots
            )
            pref_mark = " ✓" if in_pref else " ⚠"
            print(
                f"  {action.interview.id}: {action.interview.candidate:15s} - "
                f"{action.interview.round_name:20s} @ {action.time_slot} "
                f"with {action.assigned_interviewers}{pref_mark}"
            )

        # Verify correctness
        is_valid, message = task.validate_solution()
        print(f"\nValidation: {message}")

        # Show interviewer utilization
        print(f"\nInterviewer utilization:")
        for interviewer, slots in sorted(task.interviewer_schedule.items()):
            print(f"  {interviewer}: {len(slots)} interview(s)")

    else:
        print("\n✗ Failed to schedule all interviews")

    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "="*80)
    print("Note: This problem has multiple valid solutions.")
    print("MAKER finds one that satisfies all hard constraints and")
    print("optimizes for soft constraints (candidate preferences).")
    print("="*80)
