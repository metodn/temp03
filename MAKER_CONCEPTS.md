# MAKER: Solving Million-Step LLM Tasks with Zero Errors

**Paper**: https://arxiv.org/html/2511.09030v1

## Overview
MAKER is a system that enables LLMs to complete tasks requiring over one million steps without errors through massive task decomposition, error correction voting, and anomaly detection.

## Core Concepts

### 1. Massively Decomposed Agentic Processes (MDAPs)
- **Principle**: Break complex tasks into minimal subtasks
- **Approach**: Use many focused microagents instead of single sophisticated models
- **Benefit**: Reduces cumulative error propagation

### 2. Maximal Agentic Decomposition (MAD)
- **Goal**: Divide tasks into single-step subtasks
- **Implementation**: Each agent receives minimal context to solve one move
- **Advantage**: Simplifies individual decisions, improving reliability

### 3. First-to-Ahead-by-k Voting
- **Method**: Error correction through multi-agent consensus
- **Algorithm**: Continue sampling until one candidate achieves k more votes than competitors
- **Scaling**: Required voting margin grows logarithmically: Θ(ln s) where s = steps
- **Cost**: Expected cost scales log-linearly: Θ(s ln s)

### 4. Red-Flagging (Anomaly Detection)
- **Purpose**: Discard unreliable responses
- **Criteria**:
  - Overly long outputs
  - Malformed outputs
  - Responses that don't match expected format
- **Impact**: Substantially reduces correlated errors

## Mathematical Properties

### Scaling Laws
- **Voting margin growth**: Θ(ln s) - logarithmic with task steps
- **Expected cost**: Θ(s ln s) - log-linear scaling
- **Per-step success**: Remains stable across task scales

### Error Rates
- Consistent error rates regardless of task progression
- No degradation over million+ steps

## Benchmark: Towers of Hanoi

### Why Towers of Hanoi?
- Natural scalability: 2^D - 1 steps for D disks
- Verifiable correctness
- Well-defined single-step operations

### Results
- ✅ Successfully solved 20-disk problem (1,048,575 steps)
- ✅ Zero errors achieved
- ✅ Smaller models (gpt-4o-mini) outperformed reasoning-specialized LLMs on cost-effectiveness

## Key Findings

1. **Decomposition > Sophistication**: Many simple agents outperform single sophisticated agents
2. **Voting is Critical**: Multi-agent consensus prevents error propagation
3. **Red-flagging is Essential**: Anomaly detection reduces correlated errors
4. **Cost-Effective Scaling**: Cheaper models with voting beat expensive reasoning models
5. **Stable Performance**: Error rates don't increase with task length

## Implementation Components

### Algorithm 1: Complete Solution Generation
- Iterative voting rounds
- Builds solution step by step
- Validates each step before proceeding

### Algorithm 2: First-to-Ahead-by-k Voting
- Samples multiple responses
- Counts votes for each candidate
- Returns when one achieves k-vote lead

### Algorithm 3: Individual Voting Agent
- Generates response for single step
- Applies red-flagging criteria
- Resamples if flagged as unreliable

## Practical Applications

### Suitable For:
- Long-form reasoning tasks
- Multi-step planning
- Code generation with many dependencies
- Mathematical proofs
- Sequential decision making

### Requirements:
- Task must be decomposable into steps
- Each step must be verifiable or votable
- Context for each step must be extractable

## Testing Strategy with LiteLLM

### 1. Simple Towers of Hanoi (3-5 disks)
- Test basic decomposition
- Validate voting mechanism
- Measure error rates

### 2. Medium Tasks (10 disks)
- Test scaling properties
- Measure cost vs accuracy tradeoffs
- Compare different models

### 3. Red-Flagging Validation
- Test anomaly detection
- Measure impact on error correlation
- Tune flagging thresholds

### 4. Model Comparison
- Test gpt-4o-mini vs other models
- Measure cost-effectiveness
- Validate paper's findings
