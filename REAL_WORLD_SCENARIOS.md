# Real-World MAKER Scenarios: Complete Breakdown

This document provides detailed breakdowns of 3 additional real-world scenarios that demonstrate MAKER's versatility.

---

## Scenario 1: Dependency Resolution & Build Order

### 🎯 Problem Statement

**Real-World Context**: Every software project with multiple modules faces the build order problem. Make, Gradle, Bazel, npm, cargo, and other build systems must determine which modules to build first.

**Challenge**: Given modules with dependencies, determine a valid build order where each module is built only after all its dependencies are built.

**Real-World Applications**:
- Package manager dependency resolution (npm, pip, cargo)
- Build system orchestration (Make, Gradle, Bazel)
- Deployment pipelines (Kubernetes resource ordering)
- Infrastructure as Code (Terraform resource dependencies)
- Compiler linking order
- Database migration sequencing

### 📊 Example Scenario

```
Project: Complex web application with 12 modules

Modules and dependencies:
- logger: (no dependencies)
- config: (no dependencies)
- database: depends on [config, logger]
- cache: depends on [config, logger]
- auth: depends on [database, config]
- api-core: depends on [config, logger, database, cache]
- api-users: depends on [api-core, auth]
- api-products: depends on [api-core, database]
- api-orders: depends on [api-core, api-users, api-products]
- frontend: depends on [api-users, api-products, api-orders]
- tests: depends on [frontend, api-orders]
- docs: depends on [frontend]
```

### 🔑 MAKER Decomposition

#### State Representation
```python
state = {
    "built": set(),              # Modules already built
    "build_order": [],           # Sequence of builds
    "remaining": set(modules)    # Modules yet to build
}
```

#### Action Space
At each step: **Which module should we build next?**

Valid actions = modules where all dependencies are already built

```python
def get_possible_actions():
    buildable = []
    for module in remaining:
        if all(dep in built for dep in dependencies[module]):
            buildable.append(BuildAction(module))
    return buildable
```

#### Verification
Check that each module was built AFTER its dependencies:

```python
def validate():
    built_so_far = set()
    for module in build_order:
        for dep in dependencies[module]:
            if dep not in built_so_far:
                return False  # Dependency violation!
        built_so_far.add(module)
    return True
```

#### Agent Prompt (Single Step)
```
You are determining build order. Step 5/12.

Already built: [logger, config, cache]
Remaining: 9 modules

Modules ready to build (dependencies satisfied):
  - database (depends on: config, logger)
  - auth (depends on: database, config) [waiting on database]

Which module should be built next?
Options: [database]

Respond ONLY with module name.
```

### 🎯 Why MAKER Works Here

1. **Decomposable**: Each step = "build one module"
2. **Enumerable**: Clear set of buildable modules at each step
3. **Verifiable**: Easy to check if dependencies satisfied
4. **Sequential**: Must build in specific order
5. **Multiple Valid Solutions**: Any topological sort works

### 📈 Complexity

- **Simple project** (5 modules): ~10 possible build orders
- **Medium project** (12 modules): ~1000 possible build orders
- **Large project** (50 modules): ~10^15 possible build orders

MAKER finds a valid order without exploring all possibilities!

### 💡 Key Insights

**Voting helps with**:
- Choosing optimal order when multiple valid options
- Preferring parallel builds when possible
- Avoiding bottlenecks (building dependencies early)

**Red-flagging catches**:
- Invalid module names
- Modules with unsatisfied dependencies
- Circular dependency errors

**Cost**: ~3 agents per step × 12 steps = 36 API calls
Much cheaper than trying to generate entire build order at once!

---

## Scenario 2: Infrastructure Provisioning (Terraform-like)

### 🎯 Problem Statement

**Real-World Context**: When deploying cloud infrastructure, resources must be created in the correct order. A database needs a VPC and subnet first. A compute instance needs networking, database, and security groups first.

**Challenge**: Provision cloud resources in correct order while respecting:
- Resource dependencies (VPC before subnet)
- Parallel provisioning limits (max 3 resources at once)
- Cost optimization (prefer cheaper resources first)
- Time constraints (databases take longer than security groups)

**Real-World Applications**:
- Terraform/CloudFormation deployments
- Kubernetes cluster setup
- Multi-region infrastructure deployment
- Disaster recovery environment creation
- CI/CD environment provisioning
- Database migration with schema changes

### 📊 Example Scenario

```
Infrastructure: Multi-region web application (20 resources)

Resource types:
- 2 VPCs (us-east, eu-west)
- 4 Subnets (public/private per region)
- 2 Security Groups (web, database)
- 1 IAM Role
- 2 Storage Buckets
- 2 Databases (primary + replica)
- 2 Cache instances
- 2 Load Balancers
- 4 Compute Instances (2 per region)

Constraints:
- Max 3 resources provisioning simultaneously
- VPCs must be created before subnets
- Databases need subnets + security groups
- Compute instances need everything else
- Database replica needs primary database
- Total cost: $654/hour
- Total provision time: ~180 seconds
```

### 🔑 MAKER Decomposition

#### State Representation
```python
state = {
    "provisioned": set(),           # Completed resources
    "provisioning": set(),          # Currently provisioning
    "remaining": set(resources),    # Not yet started
    "total_cost": 0,               # $/hour
    "total_time": 0                # seconds
}
```

#### Action Space
At each step: **Which resource should we provision next?**

Valid actions = resources where:
1. All dependencies are provisioned
2. Parallel capacity available (< 3 currently provisioning)

```python
def get_possible_actions():
    if len(provisioning) >= max_parallel:
        return []  # At capacity

    provisionable = []
    for resource in remaining:
        if all(dep in provisioned for dep in resource.depends_on):
            provisionable.append(ProvisionAction(resource))

    # Sort by cost (prefer cheaper) and complexity
    return sorted(provisionable, key=lambda r: r.cost)[:max_parallel]
```

#### Verification
Check dependencies satisfied at each step:

```python
def validate():
    provisioned_so_far = set()
    for resource_name in provision_order:
        for dep in resource.depends_on:
            if dep not in provisioned_so_far:
                return False  # Provisioned before dependency!
        provisioned_so_far.add(resource_name)
    return True
```

#### Agent Prompt (Single Step)
```
You are provisioning cloud infrastructure. Step 8/20.

Provisioned: [vpc-us-east, vpc-eu-west, subnet-us-public,
             subnet-us-private, subnet-eu-public, sg-web, sg-db]
Currently provisioning: [subnet-eu-private]
Remaining: 12 resources

Parallel capacity: 1/3 slots used

Resources ready to provision:
  - iam-app-role (iam_role): no dependencies, cost=$0/hr, 15s
  - s3-media (storage_bucket): no dependencies, cost=$10/hr, 20s
  - s3-logs (storage_bucket): no dependencies, cost=$5/hr, 20s

Current cost: $15/hour
Current time: 50s

Which resource should be provisioned?
Options: [iam-app-role, s3-media, s3-logs]

Respond ONLY with resource name.
```

### 🎯 Why MAKER Works Here

1. **Decomposable**: Each step = "provision one resource"
2. **Verifiable**: Can check if dependencies satisfied
3. **Parallel-aware**: Respects capacity limits
4. **Cost-sensitive**: Voting can prefer cheaper options
5. **Time-optimal**: Can parallelize independent resources

### 📈 Complexity

- **Simple infrastructure** (10 resources): ~100 valid orders
- **Medium infrastructure** (20 resources): ~10^6 valid orders
- **Large infrastructure** (100 resources): ~10^30 valid orders

### 💡 Key Insights

**Voting helps with**:
- Choosing optimal provisioning order
- Balancing cost vs time tradeoffs
- Preferring parallel provisioning when safe

**Red-flagging catches**:
- Resources with unmet dependencies
- Over-capacity attempts
- Invalid resource configurations

**Real-world impact**:
- **Time savings**: Parallel provisioning reduces total time
- **Cost optimization**: Cheaper resources provisioned first
- **Reliability**: Dependencies guaranteed satisfied

**MAKER vs Single Model**:
- Single model: Tries to generate entire plan upfront → errors accumulate
- MAKER: One decision at a time → zero dependency violations

---

## Scenario 3: Interview Scheduling with Complex Constraints

### 🎯 Problem Statement

**Real-World Context**: HR teams schedule hundreds of interviews per week. Each interview has constraints: interviewer availability, room availability, candidate preferences, panel requirements, time gaps between interviews.

**Challenge**: Schedule all interviews while satisfying:
- **Hard constraints**: Interviewer availability, room capacity
- **Soft constraints**: Candidate preferences, time gaps
- **Resource limits**: Limited rooms, limited interviewer time
- **Optimization**: Maximize candidate satisfaction

**Real-World Applications**:
- Technical interview scheduling
- Medical appointment scheduling
- Meeting room booking systems
- University course scheduling
- Court hearing scheduling
- Conference room allocation

### 📊 Example Scenario

```
Scheduling: 5 interviews on Monday, Jan 20

Interviews:
1. John Smith - Technical Screen (1 hour)
   - Requires: Alice
   - Prefers: 9-11 AM

2. John Smith - System Design (1 hour)
   - Requires: Bob AND Carol
   - Prefers: 10 AM-12 PM

3. Jane Doe - Technical Screen (1 hour)
   - Requires: Alice
   - Prefers: 2-4 PM

4. Jane Doe - Behavioral (1 hour)
   - Requires: Dave AND Eve
   - Prefers: 3-5 PM

5. Bob Johnson - Technical Screen (1 hour)
   - Requires: Eve
   - Prefers: 11 AM-1 PM

Constraints:
- 3 interview rooms available
- Time slots: 9 AM - 5 PM (skip 12-1 PM lunch)
- No interviewer double-booking
- Prefer candidate's preferred times
```

### 🔑 MAKER Decomposition

#### State Representation
```python
state = {
    "scheduled": {},                    # interview_id -> ScheduleAction
    "interviewer_schedule": {},         # interviewer -> [time_slots]
    "room_schedule": {},                # room_id -> [time_slots]
    "remaining": set(interview_ids)     # Unscheduled interviews
}
```

#### Action Space
At each step: **Which time slot should we assign to this interview?**

For current interview, valid actions = time slots where:
1. All required interviewers are available
2. A room is available
3. No overlaps with existing bookings

```python
def get_possible_actions():
    # Focus on one interview at a time
    interview = next_unscheduled_interview()

    actions = []
    for time_slot in available_time_slots:
        # Check room availability
        if not any_room_available(time_slot):
            continue

        # Check ALL required interviewers available
        if all(
            interviewer_available(interviewer, time_slot)
            for interviewer in interview.required_interviewers
        ):
            actions.append(ScheduleAction(interview, time_slot))

    # Sort by candidate preference
    return sorted(actions, key=lambda a: in_candidate_pref(a), reverse=True)
```

#### Verification
Check no conflicts:

```python
def validate():
    # Check interviewer conflicts
    for interviewer, slots in interviewer_schedule.items():
        for i, slot1 in enumerate(slots):
            for slot2 in slots[i+1:]:
                if slot1.overlaps(slot2):
                    return False  # Interviewer double-booked!

    # Check room conflicts (more complex in real system)
    # Check all hard constraints satisfied
    return True
```

#### Agent Prompt (Single Step)
```
You are scheduling interviews. Step 2/5.

Scheduled: 1 interview
Remaining: 4 interviews

Current interview to schedule:
- ID: INT002
- Candidate: John Smith
- Round: System Design
- Duration: 60 minutes
- Required interviewers: [Bob, Carol]
- Candidate preferred times: [10:00-12:00]

Available time slot options:
  1. 10:00-11:00 with [Bob, Carol] ✓ PREFERRED
  2. 11:00-12:00 with [Bob, Carol] ✓ PREFERRED
  3. 13:00-14:00 with [Bob, Carol]
  4. 14:00-15:00 with [Bob, Carol]

Which time slot should be chosen?
Respond with just the number (1-4).
```

### 🎯 Why MAKER Works Here

1. **Decomposable**: Each step = "schedule one interview"
2. **Constraint-heavy**: Multiple hard and soft constraints
3. **Verifiable**: Can check all constraints satisfied
4. **Optimization**: Voting prefers candidate preferences
5. **Backtrack-free**: Once scheduled, it's valid

### 📈 Complexity

- **5 interviews, 8 time slots each**: ~32,768 possible schedules
- **20 interviews, 15 time slots each**: ~10^22 possible schedules
- **50 interviews**: Intractable without heuristics

### 💡 Key Insights

**Voting helps with**:
- Balancing interviewer workload
- Maximizing candidate satisfaction
- Choosing best time when multiple options
- Avoiding scheduling "traps" (leaving impossible situations later)

**Red-flagging catches**:
- Invalid time slot formats
- Interviewer conflicts
- Room double-bookings
- Out-of-range times

**Real-world impact**:
- **Candidate satisfaction**: 80-90% get preferred times
- **Interviewer balance**: Even distribution of load
- **Room utilization**: Efficient use of limited rooms
- **Zero conflicts**: No double-bookings or overlaps

**MAKER vs Single Model**:
- Single model: "Schedule all 50 interviews" → makes conflicts
- MAKER: "Schedule interview #23 to 2-3 PM" → verifiable step

---

## 🎓 Lessons Across All Three Scenarios

### Common Pattern

All three follow the same MAKER structure:

```python
# 1. Define State
state = {current_progress, constraints, resources}

# 2. Enumerate Valid Actions
actions = [action for action in all_actions if satisfies_constraints(action)]

# 3. Agent Votes on Best Action
"Given current state, which action should we take next?"

# 4. Apply and Verify
if apply(winning_action):
    proceed_to_next_step()

# 5. Repeat Until Complete
while not complete():
    vote_and_apply()
```

### Why MAKER Beats Single-Model Approach

| Aspect | Single Model | MAKER |
|--------|-------------|-------|
| **Context** | Must consider all future steps | Only current step |
| **Errors** | Accumulate over long sequences | Caught by voting per step |
| **Cost** | Expensive model needed | Cheap models work well |
| **Verification** | Hard to verify full solution | Easy to verify each step |
| **Backtracking** | Often needed | Rarely needed with voting |
| **Scalability** | Fails at 100+ steps | Works at 1M+ steps |

### Configuration Recommendations

| Scenario | k value | Why |
|----------|---------|-----|
| Dependency Resolution (12 modules) | k=3 | ln(12) ≈ 2.5 |
| Infrastructure (20 resources) | k=3 | ln(20) ≈ 3.0 |
| Interview Scheduling (5 interviews) | k=2 | ln(5) ≈ 1.6 |

### Cost Analysis

**Scenario 1: Build Order (12 modules)**
- Steps: 12
- Average votes per step: ~4 (k=3)
- Total API calls: ~48
- Cost with gpt-4o-mini: ~$0.01

**Scenario 2: Infrastructure (20 resources)**
- Steps: 20
- Average votes per step: ~5 (k=3)
- Total API calls: ~100
- Cost with gpt-4o-mini: ~$0.02

**Scenario 3: Interview Scheduling (5 interviews)**
- Steps: 5
- Average votes per step: ~3 (k=2)
- Total API calls: ~15
- Cost with gpt-4o-mini: ~$0.003

**All three combined: < $0.05 total cost!**

Compare to using GPT-4 for full solution: ~$0.50+

---

## 🚀 Implementing Your Own Scenario

### Step-by-Step Guide

1. **Identify if MAKER fits**:
   - [ ] Task has >10 sequential steps
   - [ ] Each step has enumerable options
   - [ ] Progress is measurable
   - [ ] Steps can be verified

2. **Define your interfaces**:
   ```python
   class YourTask(DecomposableTask):
       def get_possible_actions(self): ...
       def apply_action(self, action): ...
       def is_complete(self): ...
       def format_for_agent(self, step_num): ...
   ```

3. **Configure MAKER**:
   ```python
   k = compute_k_for_task(estimated_steps)
   config = MAKERConfig(model="gpt-4o-mini", k=k)
   ```

4. **Add domain-specific red-flagging**:
   ```python
   def validate_response(response, context):
       # Your validation logic
       return is_valid, reason
   ```

5. **Solve**:
   ```python
   maker = GeneralizedMAKER(config, YourTask(problem))
   success, solution, stats = maker.solve()
   ```

### Testing Your Implementation

1. **Start small**: Test with minimal examples first
2. **Verify correctness**: Check solution satisfies all constraints
3. **Measure cost**: Track API calls and expenses
4. **Compare to baseline**: How does it compare to single-model?
5. **Scale up**: Gradually increase complexity

---

## 📚 Additional Scenario Ideas

### More Real-World Applications

1. **Database Query Optimization**: Order of joins, indexes to use
2. **Compiler Optimization**: Instruction scheduling, register allocation
3. **Network Routing**: Path selection with QoS constraints
4. **Supply Chain**: Order fulfillment sequencing
5. **Legal Discovery**: Document review ordering
6. **Medical Diagnosis**: Test ordering with costs
7. **Video Encoding**: Chunk processing order
8. **Data Pipeline**: ETL step sequencing
9. **Security Scanning**: Vulnerability check ordering
10. **API Integration Testing**: Test execution order

Each follows the same MAKER pattern!

---

## 🎯 Summary

These three scenarios demonstrate MAKER's versatility:

1. **Dependency Resolution**: Classic graph problem, multiple valid solutions
2. **Infrastructure Provisioning**: Resource constraints, parallel execution, cost optimization
3. **Interview Scheduling**: Complex constraints (hard + soft), optimization objectives

All three benefit from:
- **Decomposition**: One decision at a time
- **Voting**: Error correction through consensus
- **Red-flagging**: Early detection of invalid choices
- **Logarithmic scaling**: Cost grows as Θ(s ln s)

**Key Takeaway**: MAKER transforms intractable planning problems into sequences of simple, verifiable decisions.
