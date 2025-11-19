## MAKER Adaptation Examples

This document shows concrete examples of adapting MAKER to different task types.

### Example 1: Sudoku Solver

**Task**: Fill a 9x9 Sudoku grid following constraints.

**State**: Current grid + empty cells
**Actions**: Assign number to a cell
**Verification**: Check row/column/box constraints

```python
class SudokuTask(DecomposableTask):
    def _initialize_state(self, grid):
        return TaskState(
            grid=grid,
            empty_cells=self._find_empty_cells(grid)
        )

    def get_possible_actions(self):
        if not self.state.empty_cells:
            return []

        # Get next empty cell
        row, col = self.state.empty_cells[0]

        # Return valid numbers for this cell
        valid = []
        for num in range(1, 10):
            if self._is_valid_placement(row, col, num):
                valid.append(Action("place", row, col, num))

        return valid

    def apply_action(self, action):
        row, col, num = action.row, action.col, action.num

        # Validate
        if not self._is_valid_placement(row, col, num):
            return False

        # Apply
        self.state.grid[row][col] = num
        self.state.empty_cells.pop(0)
        self.history.append(action)
        return True

    def is_complete(self):
        return len(self.state.empty_cells) == 0

    def format_for_llm(self):
        row, col = self.state.empty_cells[0]
        valid_nums = [a.num for a in self.get_possible_actions()]

        return f"""
Current Sudoku grid:
{self._format_grid()}

Next cell to fill: Row {row+1}, Column {col+1}
Valid numbers: {valid_nums}

Row constraint: {self._get_row(row)}
Column constraint: {self._get_col(col)}
Box constraint: {self._get_box(row, col)}

Which number should go in this cell?
"""

    def estimate_steps(self):
        return len(self.state.empty_cells)
```

**Agent Prompt Pattern**:
```
You are solving Sudoku. This is cell {current}/{total_empty}.

{formatted_grid}

Which number (1-9) should go in Row {row}, Column {col}?
Valid options: {valid_numbers}

Constraints:
- Row must have 1-9 exactly once
- Column must have 1-9 exactly once
- 3x3 box must have 1-9 exactly once

Respond ONLY with the number. No explanation.
```

**Red-Flagging**:
- Response must be single digit 1-9
- Must be in valid_numbers list
- Length must be 1-2 characters
- No text, only number

---

### Example 2: Multi-File Code Refactoring

**Task**: Refactor codebase by renaming functions across multiple files.

**State**: Current code + test status + remaining refactorings
**Actions**: Rename, extract, move, update imports
**Verification**: Tests must pass after each change

```python
class CodeRefactoringTask(DecomposableTask):
    def _initialize_state(self, codebase):
        return TaskState(
            files=codebase.files,
            test_status="passing",
            refactorings_needed=self._find_refactorings(codebase),
            refactorings_done=[]
        )

    def get_possible_actions(self):
        actions = []

        # Find next refactoring opportunity
        for refactoring in self.state.refactorings_needed:
            if refactoring.type == "rename_function":
                actions.append(Action(
                    "rename",
                    old_name=refactoring.old_name,
                    new_name=refactoring.suggested_name,
                    files=refactoring.affected_files
                ))
            elif refactoring.type == "extract_method":
                actions.append(Action(
                    "extract",
                    lines=refactoring.code_lines,
                    new_name=refactoring.suggested_name
                ))

        return actions[:5]  # Limit to top 5 candidates

    def apply_action(self, action):
        # Apply refactoring
        if action.type == "rename":
            success = self._rename_function(
                action.old_name,
                action.new_name,
                action.files
            )
        elif action.type == "extract":
            success = self._extract_method(
                action.lines,
                action.new_name
            )

        if not success:
            return False

        # Run tests
        test_result = self._run_tests()
        if test_result != "passing":
            # Rollback
            self._undo_last_change()
            return False

        # Update state
        self.state.refactorings_done.append(action)
        self.state.refactorings_needed = self._find_refactorings(
            self.state.files
        )
        self.history.append(action)
        return True

    def is_complete(self):
        return (len(self.state.refactorings_needed) == 0 and
                self.state.test_status == "passing")

    def format_for_llm(self):
        return f"""
Refactoring Progress: {len(self.state.refactorings_done)}/{self.estimate_steps()}
Test Status: {self.state.test_status}

Current refactoring opportunities:
{self._format_refactorings()}

Next action options:
{self._format_actions()}

Which refactoring should be applied next?
"""

    def estimate_steps(self):
        return len(self.state.refactorings_needed)
```

**Agent Prompt Pattern**:
```
You are refactoring {project_name}. Step {current}/{total}.

Current situation:
File: {current_file}
Function: {function_name}
Issue: {code_smell}

Available refactorings:
1. Rename function "{old_name}" to "{suggested_name}" (affects {n} files)
2. Extract method from lines {start}-{end} as "{new_name}"
3. Move function "{name}" to module "{target_module}"

Which refactoring should be applied? Respond with just the number (1-3).
```

**Red-Flagging**:
- Must be a number corresponding to an option
- Length < 50 characters
- No code snippets in response
- No explanation text

---

### Example 3: Database Schema Migration

**Task**: Migrate database schema while preserving data integrity.

**State**: Current schema + data + migration steps
**Actions**: Add column, rename, migrate data, drop column
**Verification**: Data integrity checks + query tests

```python
class SchemaMigrationTask(DecomposableTask):
    def _initialize_state(self, migration_plan):
        return TaskState(
            current_schema=self._get_current_schema(),
            target_schema=migration_plan.target_schema,
            migrations_pending=migration_plan.steps,
            data_integrity_ok=True
        )

    def get_possible_actions(self):
        actions = []

        for migration in self.state.migrations_pending:
            # Check prerequisites
            if self._prerequisites_met(migration):
                actions.append(Action(
                    type=migration.type,
                    table=migration.table,
                    params=migration.params
                ))

        return actions

    def apply_action(self, action):
        # Execute migration
        if action.type == "add_column":
            success = self._add_column(
                action.table,
                action.params['name'],
                action.params['type']
            )
        elif action.type == "rename_column":
            success = self._rename_column(
                action.table,
                action.params['old_name'],
                action.params['new_name']
            )
        elif action.type == "migrate_data":
            success = self._migrate_data(
                action.table,
                action.params['from_col'],
                action.params['to_col'],
                action.params['transform']
            )

        if not success:
            return False

        # Verify data integrity
        if not self._check_data_integrity():
            self._rollback_last_migration()
            return False

        # Update state
        self.state.migrations_pending.remove(action.migration)
        self.history.append(action)
        return True

    def is_complete(self):
        return (len(self.state.migrations_pending) == 0 and
                self.state.data_integrity_ok)

    def format_for_llm(self):
        return f"""
Database Migration Progress: {len(self.history)}/{self.estimate_steps()}

Current schema:
{self._format_schema(self.state.current_schema)}

Target schema:
{self._format_schema(self.state.target_schema)}

Pending migrations:
{self._format_pending_migrations()}

Data integrity: {self.state.data_integrity_ok}

Which migration should be executed next?
"""
```

**Agent Prompt Pattern**:
```
You are migrating database schema for {database_name}. Step {current}/{total}.

Current table: {table_name}
Current columns: {columns}

Target state: {target_columns}

Available migrations:
1. Add column "{name}" ({type}) - SAFE, reversible
2. Rename column "{old}" to "{new}" - SAFE, reversible
3. Migrate data from "{old_col}" to "{new_col}" - CAUTION, test first

Which migration should run next? Respond with just the number (1-3).
```

**Red-Flagging**:
- Must be valid migration number
- No SQL code in response
- Length < 30 characters
- Check migration is safe (no DROP without backup)

---

### Example 4: Test Suite Generation

**Task**: Generate comprehensive tests for untested code.

**State**: Code coverage + untested functions + generated tests
**Actions**: Generate test for specific function
**Verification**: Tests compile and pass

```python
class TestGenerationTask(DecomposableTask):
    def _initialize_state(self, codebase):
        coverage = self._analyze_coverage(codebase)
        return TaskState(
            codebase=codebase,
            coverage=coverage,
            untested_functions=coverage.untested,
            generated_tests=[]
        )

    def get_possible_actions(self):
        actions = []

        # Prioritize untested functions
        for func in self.state.untested_functions[:10]:
            actions.append(Action(
                "generate_test",
                function=func,
                test_name=f"test_{func.name}",
                priority=self._calculate_priority(func)
            ))

        return sorted(actions, key=lambda a: a.priority, reverse=True)

    def apply_action(self, action):
        # Generate test using LLM
        test_code = self._generate_test_code(action.function)

        # Validate test compiles
        if not self._validate_syntax(test_code):
            return False

        # Run test
        result = self._run_test(test_code)
        if result.status != "passing":
            return False

        # Update coverage
        self.state.generated_tests.append(test_code)
        self.state.untested_functions.remove(action.function)
        self.state.coverage = self._analyze_coverage(self.state.codebase)
        self.history.append(action)
        return True

    def is_complete(self):
        return self.state.coverage.percentage >= 0.90  # 90% target

    def format_for_llm(self):
        return f"""
Test Coverage: {self.state.coverage.percentage:.1%}
Untested functions: {len(self.state.untested_functions)}
Tests generated: {len(self.state.generated_tests)}

Next function to test:
{self._format_function(self.state.untested_functions[0])}

Function signature: {func.signature}
Function body preview:
{func.body_preview}

What test cases should be generated?
"""
```

---

### Example 5: Route Planning with Constraints

**Task**: Find optimal route through graph with time/cost constraints.

**State**: Current location + visited nodes + remaining budget
**Actions**: Move to adjacent node
**Verification**: Constraints satisfied, goal reached

```python
class RoutePlanningTask(DecomposableTask):
    def _initialize_state(self, graph):
        return TaskState(
            graph=graph,
            current_node=graph.start,
            goal_node=graph.goal,
            visited=[graph.start],
            cost_spent=0,
            time_spent=0
        )

    def get_possible_actions(self):
        current = self.state.current_node
        actions = []

        # Get adjacent nodes
        for neighbor in self.state.graph.neighbors(current):
            edge = self.state.graph.get_edge(current, neighbor)

            # Check constraints
            if (self.state.cost_spent + edge.cost <= self.max_cost and
                self.state.time_spent + edge.time <= self.max_time):

                actions.append(Action(
                    "move",
                    from_node=current,
                    to_node=neighbor,
                    cost=edge.cost,
                    time=edge.time
                ))

        return actions

    def apply_action(self, action):
        # Move to new node
        self.state.current_node = action.to_node
        self.state.visited.append(action.to_node)
        self.state.cost_spent += action.cost
        self.state.time_spent += action.time
        self.history.append(action)
        return True

    def is_complete(self):
        return self.state.current_node == self.state.goal_node

    def format_for_llm(self):
        return f"""
Route Planning Progress: Step {len(self.history)}

Current location: {self.state.current_node}
Goal: {self.state.goal_node}
Visited: {self.state.visited}

Resources:
- Cost: {self.state.cost_spent}/{self.max_cost}
- Time: {self.state.time_spent}/{self.max_time}

Available moves:
{self._format_moves()}

Which move should be taken?
"""
```

---

## Common Patterns Across Examples

### 1. State Representation
- Keep state **minimal** but **complete**
- Include only what's needed for decision-making
- Separate current state from history

### 2. Action Enumeration
- Return **concrete, executable** actions
- Limit to **feasible** options (check constraints)
- Order by priority if helpful

### 3. Validation
- **Validate before** applying action
- **Verify after** applying action
- **Rollback** on failure

### 4. LLM Formatting
- Show **current state clearly**
- List **available options**
- Include **relevant constraints**
- Keep it **concise** (< 500 tokens ideally)

### 5. Progress Tracking
- Measure **completion percentage**
- Track **actions taken**
- Monitor **resource usage**

## Choosing the Right Model

Based on paper findings:

| Task Complexity | Recommended Model | Why |
|----------------|------------------|-----|
| Simple (< 100 steps) | gpt-4o-mini | Cheap, fast, voting compensates |
| Medium (100-1000 steps) | gpt-4o-mini | Still cost-effective with voting |
| Complex (> 1000 steps) | gpt-4o-mini | Paper solved 1M steps with it! |
| Requires domain knowledge | gpt-4o or claude-3-5-sonnet | If single steps need expertise |

**Key insight**: Cheaper models with voting beat expensive models without voting!

## Debugging Your Adaptation

### Agents don't converge
- **Symptom**: Voting never reaches k-vote lead
- **Check**: Are actions well-defined? Is state ambiguous?
- **Fix**: Clarify state representation, reduce action space

### Agents converge to wrong answer
- **Symptom**: Consensus on invalid action
- **Check**: Is validation working? Is prompt misleading?
- **Fix**: Strengthen validation, improve prompt clarity

### Too expensive
- **Symptom**: Too many API calls per step
- **Check**: Is k too high? Using expensive model?
- **Fix**: Use gpt-4o-mini, reduce k, add caching

### Too slow
- **Symptom**: Takes too long to complete
- **Check**: Sequential vs parallel voting?
- **Fix**: Parallelize agent calls, cache results
