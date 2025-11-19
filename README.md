# MAKER: Solving Million-Step LLM Tasks

Implementation of concepts from the paper ["Solving a Million-Step LLM Task with Zero Errors"](https://arxiv.org/html/2511.09030v1) using Python and LiteLLM.

## Overview

This project implements the **MAKER** system, which enables LLMs to complete tasks requiring over one million steps without errors through:

1. **Maximal Agentic Decomposition (MAD)**: Breaking tasks into single-step subtasks
2. **First-to-Ahead-by-k Voting**: Error correction through multi-agent consensus
3. **Red-Flagging**: Anomaly detection to discard unreliable responses

## Key Concepts

### Massively Decomposed Agentic Processes (MDAPs)
Instead of using a single sophisticated model, MAKER uses many focused microagents that each handle one simple decision. This reduces cumulative error propagation.

### First-to-Ahead-by-k Voting
Multiple agents vote on each step. The system continues sampling until one candidate achieves **k** more votes than competitors. The voting margin **k** grows logarithmically with task length: **Θ(ln s)**.

### Red-Flagging
Responses are checked for anomalies:
- Overly long or short outputs
- Malformed responses
- Failure patterns ("I cannot", "I don't know", etc.)
- Missing expected format

## Files

### Core Implementation
- `MAKER_CONCEPTS.md` - Comprehensive knowledge extraction from the paper
- `towers_of_hanoi.py` - Towers of Hanoi game implementation (benchmark task)
- `maker.py` - MAKER system implementation for Towers of Hanoi
- `test_maker.py` - Comprehensive test suite
- `demo.py` - Simple demonstration script
- `requirements.txt` - Python dependencies

### Generalized Framework (NEW!)
- `MAKER_GENERALIZATION.md` - How to apply MAKER to ANY sequential task
- `maker_base.py` - Generalized MAKER implementation for any task
- `.claude/skills/maker-methodology/` - Claude Skill for using MAKER
  - `SKILL.md` - Main skill instructions
  - `TASK_TEMPLATE.py` - Template for creating new MAKER tasks
  - `EXAMPLES.md` - Concrete examples for different task types

### Working Examples

**Basic Examples:**
- `example_sudoku.py` - Sudoku solver using generalized MAKER

**Real-World Scenarios:**
- `scenario1_dependency_resolution.py` - Build order/dependency resolution
- `scenario2_infrastructure_provisioning.py` - Cloud infrastructure provisioning
- `scenario3_interview_scheduling.py` - Interview scheduling with constraints
- `REAL_WORLD_SCENARIOS.md` - Complete breakdown of scenarios 1-3

**Complex Scenarios (Advanced):**
- `scenario4_api_test_execution.py` - API integration test suite with dependencies
- `scenario5_database_migration.py` - Production database migration with data preservation
- `scenario6_distributed_deployment.py` - Distributed system rolling deployment
- `COMPLEX_SCENARIOS.md` - Complete breakdown of scenarios 4-6

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API Key

The implementation uses LiteLLM, which supports multiple LLM providers. For OpenAI:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

For other providers, see [LiteLLM documentation](https://docs.litellm.ai/docs/).

### 3. Verify Installation

```bash
python towers_of_hanoi.py
```

This should run the basic Towers of Hanoi implementation without requiring an API key.

## Usage

### Quick Demo

```bash
python demo.py
```

### Run Tests

```bash
python test_maker.py
```

Tests include:
- Basic functionality (3 disks)
- Scaling tests (3, 4, 5 disks)
- Voting margin impact (k=1, 2, 3)
- Red-flagging effectiveness
- Solution verification

### Custom Usage

```python
from maker import MAKER, MAKERConfig

# Configure MAKER
config = MAKERConfig(
    model="gpt-4o-mini",  # Model to use
    k=3,                   # Voting margin
    temperature=0.7,       # Sampling temperature
    verbose=True           # Print progress
)

# Create MAKER instance
maker = MAKER(config)

# Solve Towers of Hanoi
num_disks = 4
success, moves, stats = maker.solve_towers_of_hanoi(num_disks)

print(f"Success: {success}")
print(f"Moves: {len(moves)}")
print(f"Expected: {2**num_disks - 1}")
```

## Generalizing MAKER to Any Task

The MAKER approach can be applied to **any sequential task**! The framework has been generalized to work with:

- Constraint satisfaction problems (Sudoku, N-Queens, scheduling)
- Sequential planning (route planning, workflow orchestration)
- Code generation (multi-file refactoring, test generation)
- Mathematical reasoning (proof construction, equation solving)
- Data pipelines (ETL workflows, data cleaning)

### Quick Start: Using the Generalized Framework

```python
from maker_base import GeneralizedMAKER, MAKERConfig, DecomposableTask

# 1. Define your task by implementing DecomposableTask
class YourTask(DecomposableTask):
    def get_possible_actions(self):
        # Return list of valid actions from current state
        pass

    def apply_action(self, action):
        # Apply action and update state
        pass

    def is_complete(self):
        # Check if task is done
        pass

    def format_for_agent(self, step_num):
        # Format state as prompt for voting agents
        pass

    # ... implement other required methods

# 2. Create task instance
task = YourTask(problem_instance)

# 3. Configure and solve with MAKER
config = MAKERConfig(model="gpt-4o-mini", task_type="your_task")
maker = GeneralizedMAKER(config, task)
success, actions, stats = maker.solve()
```

### Resources for Adaptation

- **`MAKER_GENERALIZATION.md`** - Complete guide to generalizing MAKER
- **`TASK_TEMPLATE.py`** - Copy-paste template for new tasks
- **`EXAMPLES.md`** - Concrete examples for different domains
- **`example_sudoku.py`** - Working Sudoku solver example
- **`.claude/skills/maker-methodology/`** - Claude Skill that teaches MAKER methodology

### Claude Skill: MAKER Methodology

A Claude Code skill is included that teaches Claude how to apply MAKER to any task:

```bash
# The skill is in .claude/skills/maker-methodology/
# Claude will automatically use it when you ask about:
# - Solving multi-step problems
# - Sequential planning tasks
# - Tasks requiring many decisions
# - Constraint satisfaction problems
```

When activated, Claude will:
1. Identify if your task is MAKER-compatible
2. Help you define the task interface
3. Set up voting and red-flagging
4. Generate the implementation
5. Guide you through testing

### Example: Sudoku Solver

```python
from maker_base import GeneralizedMAKER, MAKERConfig
from example_sudoku import SudokuTask, create_easy_sudoku

# Create puzzle
puzzle = create_easy_sudoku()
task = SudokuTask(puzzle)

# Solve with MAKER
config = MAKERConfig(model="gpt-4o-mini", verbose=True)
maker = GeneralizedMAKER(config, task)
success, actions, stats = maker.solve()

# Sudoku solved with zero errors!
```

### More Real-World Scenarios

Three additional complete implementations demonstrate MAKER's versatility:

#### 1. Dependency Resolution & Build Order (`scenario1_dependency_resolution.py`)
**Problem**: Determine build order for software project with module dependencies

**Use Cases**: npm/pip dependencies, Make/Gradle builds, Terraform resources, Kubernetes deployments

**Complexity**: 12-module project has ~1,000 valid build orders

```bash
python scenario1_dependency_resolution.py
```

#### 2. Infrastructure Provisioning (`scenario2_infrastructure_provisioning.py`)
**Problem**: Provision cloud resources in correct order with parallel limits

**Use Cases**: Terraform/CloudFormation, Kubernetes setup, multi-region deployments, CI/CD environments

**Complexity**: 20-resource infrastructure has ~10^6 valid provisioning orders

Features:
- Parallel provisioning (max 3 simultaneous)
- Cost optimization ($654/hour total)
- Resource dependencies (VPC → Subnet → Database → App)

```bash
python scenario2_infrastructure_provisioning.py
```

#### 3. Interview Scheduling (`scenario3_interview_scheduling.py`)
**Problem**: Schedule interviews satisfying interviewer availability, room capacity, and candidate preferences

**Use Cases**: Technical interviews, medical appointments, meeting rooms, university courses, court hearings

**Complexity**: 5 interviews with 8 time slots each = ~32,000 possible schedules

Features:
- Hard constraints (availability, capacity)
- Soft constraints (candidate preferences)
- Multi-person panel requirements
- Optimization (maximize preference satisfaction)

```bash
python scenario3_interview_scheduling.py
```

**See `REAL_WORLD_SCENARIOS.md` for complete breakdowns** of all three scenarios with:
- Detailed problem analysis
- Step-by-step MAKER decomposition
- Agent prompt examples
- Complexity analysis
- Cost comparisons
- Implementation guides

### Complex Real-World Scenarios (ADVANCED)

Three highly complex scenarios demonstrating MAKER at production scale:

#### 4. API Integration Test Execution (`scenario4_api_test_execution.py`)
**Problem**: Execute comprehensive API test suite with dependencies, data sharing, and parallel execution

**Complexity**: 13 tests, 23 dependencies, parallel execution (max 3), retry logic, shared state

Features:
- Test dependencies (test B needs test A's output)
- Data sharing between tests (user ID from create used in update)
- Parallel execution constraints
- Flaky test retry logic
- Critical test failure handling
- Setup/teardown management

```bash
python scenario4_api_test_execution.py
```

#### 5. Database Schema Migration (`scenario5_database_migration.py`)
**Problem**: Migrate production database while preserving all data and maintaining zero downtime

**Complexity**: 16 steps, 1.5M rows affected, backup points, rollback capability, risk levels 1-5

Features:
- Zero data loss requirement
- Multi-stage data transformation
- Foreign key dependency management
- Backup before risky operations
- Rollback capability at any point
- Continuous data validation
- 10-minute downtime limit

```bash
python scenario5_database_migration.py
```

#### 6. Distributed System Deployment (`scenario6_distributed_deployment.py`)
**Problem**: Deploy 5 microservices with rolling updates, health checks, and automatic rollback

**Complexity**: 25+ steps, 5 services, 19 instances, canary deployments, multi-stage health checks

Features:
- Multi-service dependencies
- Rolling updates (gradual instance replacement)
- Canary deployments for critical services
- Health checks after each stage
- Database migration coordination
- Load balancer reconfiguration
- Automatic rollback on failure
- Zero downtime requirement

```bash
python scenario6_distributed_deployment.py
```

**See `COMPLEX_SCENARIOS.md` for complete analysis** of these advanced scenarios with:
- Detailed complexity breakdown
- Multi-dimensional dependency graphs
- Rollback orchestration strategies
- Health check coordination
- Real-world impact metrics
- Comparison tables
- Implementation guide for similar complex tasks

### Task Suitability Checklist

MAKER works best for tasks that are:
- ✅ Sequential (steps must happen in order)
- ✅ Decomposable (can break into single-step decisions)
- ✅ Verifiable (can check if each step is valid)
- ✅ Long (>10 steps where errors accumulate)

MAKER is NOT ideal for:
- ❌ Creative/open-ended generation
- ❌ Tasks requiring holistic understanding
- ❌ Very short tasks (<10 steps)
- ❌ Continuous optimization problems

## Configuration

### MAKERConfig Parameters

- `model` (str): LLM model to use (default: "gpt-4o-mini")
  - Paper finding: Smaller, cheaper models work better with voting
- `k` (int): Voting margin (default: 3)
  - Grows logarithmically with task steps
  - Use `MAKERConfig.compute_k_for_steps(n)` for automatic calculation
- `max_response_length` (int): Maximum response length for red-flagging (default: 200)
- `min_response_length` (int): Minimum response length for red-flagging (default: 1)
- `temperature` (float): Sampling temperature (default: 0.7)
- `max_resamples` (int): Maximum resamples if red-flagged (default: 5)
- `verbose` (bool): Print progress information (default: True)

### Choosing k (Voting Margin)

The paper shows that k should grow logarithmically with the number of steps:

- **≤10 steps**: k=2
- **≤100 steps**: k=3
- **≤1000 steps**: k=4
- **>1000 steps**: k = max(3, ln(steps) + 1)

Use `MAKERConfig.compute_k_for_steps(num_steps)` for automatic calculation.

## Benchmark: Towers of Hanoi

The Towers of Hanoi puzzle is an ideal benchmark because:
- **Scalable**: 2^D - 1 steps for D disks
- **Verifiable**: Easy to check correctness
- **Single-step operations**: Each move is atomic

### Complexity by Disk Count

| Disks | Steps Required | Time Estimate (k=3) |
|-------|----------------|---------------------|
| 3     | 7              | ~30 seconds         |
| 4     | 15             | ~1 minute           |
| 5     | 31             | ~2 minutes          |
| 10    | 1,023          | ~20 minutes         |
| 20    | 1,048,575      | ~200 hours*         |

*Based on paper results. Actual time depends on model, API rate limits, and voting margin.

## Key Findings from Paper

1. **Decomposition > Sophistication**: Many simple agents outperform single sophisticated agents
2. **Voting is Critical**: Multi-agent consensus prevents error propagation
3. **Red-flagging is Essential**: Anomaly detection reduces correlated errors
4. **Cost-Effective Scaling**: Cheaper models with voting beat expensive reasoning models
5. **Stable Performance**: Error rates don't increase with task length

## Cost Considerations

Expected cost scales as **Θ(s ln s)** where s is the number of steps:

- Each step requires multiple agent calls (voting)
- The voting margin k grows logarithmically
- Total API calls ≈ s × (average agents per vote)

For cost optimization:
- Use cheaper models (gpt-4o-mini performs well)
- Tune k based on task length
- Implement caching for repeated states (not in this demo)

## Extending to Other Tasks

The MAKER approach can be applied to any task that:
1. Can be decomposed into steps
2. Has verifiable or votable intermediate states
3. Allows context extraction for each step

Examples:
- Multi-step reasoning problems
- Code generation with dependencies
- Mathematical proofs
- Sequential planning tasks

To adapt MAKER:
1. Implement your task's state representation
2. Define single-step operations
3. Create prompts for microagents
4. Implement validation logic
5. Adjust red-flagging criteria

## Limitations

- **API Costs**: Large tasks require many API calls
- **Time**: Voting adds latency
- **Task Suitability**: Only works for decomposable tasks
- **Model Dependence**: Requires models that can handle single-step decisions

## Future Improvements

- [ ] Implement caching to avoid redundant votes
- [ ] Add parallel agent calls for faster voting
- [ ] Support for other benchmark tasks
- [ ] Adaptive k selection based on confidence
- [ ] Cost tracking and optimization
- [ ] Support for more LLM providers

## References

**Paper**: "Solving a Million-Step LLM Task with Zero Errors"
- arXiv: https://arxiv.org/html/2511.09030v1
- Key result: Successfully solved 20-disk Towers of Hanoi (1,048,575 steps) with zero errors

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Areas for improvement:
- Additional benchmark tasks
- Performance optimizations
- Better red-flagging heuristics
- Cost optimization strategies
- Documentation and examples
