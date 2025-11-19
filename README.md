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

- `MAKER_CONCEPTS.md` - Comprehensive knowledge extraction from the paper
- `towers_of_hanoi.py` - Towers of Hanoi game implementation (benchmark task)
- `maker.py` - MAKER system implementation with voting and red-flagging
- `test_maker.py` - Comprehensive test suite
- `demo.py` - Simple demonstration script
- `requirements.txt` - Python dependencies

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
