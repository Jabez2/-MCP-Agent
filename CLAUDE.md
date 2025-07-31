# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Multi-Agent Code Generation System** based on MCP (Model Context Protocol). It implements a collaborative development workflow with 8 specialized AI agents that work together to analyze requirements, write code, generate tests, execute tests, refactor, scan code quality, and create project structures.

## Key Architecture

### Core Components

**GraphFlowOrchestrator** (`src/core/orchestrator.py`): The central coordinator that combines GraphFlow structural execution with MagenticOne intelligent scheduling. Features dual-loop architecture:
- **Outer Loop**: Task decomposition and planning using LLM analysis
- **Inner Loop**: Intelligent execution with progress ledger-based node selection

**Data Structures** (`src/core/data_structures.py`):
- `TaskLedger`: Global task state, plans, and dynamic file path configuration
- `ProgressLedger`: Execution tracking, node states, and retry management
- `NodeState`: Execution state enumeration for agents

**Agent System** (`src/agents/`): 7 specialized agents (excludes ReflectionAgent):
1. CodePlanningAgent - Requirements analysis and implementation planning
2. FunctionWritingAgent - Python function implementation
3. TestGenerationAgent - Test case creation
4. UnitTestAgent - Test execution with MCP code runner
5. RefactoringAgent - Code optimization and fixes
6. CodeScanningAgent - Static code analysis
7. ProjectStructureAgent - Directory structure creation

### MCP Integration

**File System MCP** (`mcp_services/filesystem-mcp-server/`): Provides file operations with intelligent path resolution
**Code Runner MCP**: Remote npm package for test execution
**Custom MCP Servers**: fetch-mcp for web requests, code_scanner_mcp for quality analysis

### Intelligent Path Resolution

Dynamic file naming system that generates project-specific paths based on task analysis. Files are output to `/Users/jabez/output/` with structured naming conventions.

## Common Commands

### Running the System
```bash
# Run with default task
python src/main.py

# Run with custom task
python src/main.py "Create a math library with advanced functions"

# Run single agent workflow
python eight_agent.py
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest tests/

# Lint and format
black src/
flake8 src/
mypy src/

# Build MCP servers
cd mcp_services/filesystem-mcp-server && npm install && npm run build
cd mcp_services/fetch-mcp && npm install && npm run build
```

### Configuration
**LLM Model**: Configured in `src/config/model_config.py` - currently uses Qwen/Qwen3-Coder-480B-A35B-Instruct via ModelScope API
**MCP Servers**: Configured in `src/config/mcp_config.py` - filesystem server with `/Users` directory access

## Important Development Patterns

### Agent Creation
All agents follow the same pattern:
- Created via factory functions in `src/agents/[agent_type]_agent.py`
- Receive model_client, workbench, and optional configuration
- Return AutoGen ChatAgent instances with specific system prompts

### Workflow Execution
1. **Task Analysis**: LLM parses requirements and generates file configuration
2. **Sequential Execution**: Agents execute in predefined order with intelligent fallbacks
3. **Error Recovery**: Failed unit tests trigger refactoring agent with error context
4. **Path Management**: All file operations use intelligent path resolver

### Completion Markers
Each agent signals completion with specific markers:
- `PLANNING_COMPLETE`, `CODING_COMPLETE`, `TESTING_COMPLETE`
- `UNIT_TESTING_COMPLETE`, `REFACTORING_COMPLETE`
- `SCANNING_COMPLETE`, `PROJECT_STRUCTURE_COMPLETE`

### Logging and Monitoring
Comprehensive workflow logging saves to `/Users/jabez/output/logs/` with:
- Agent execution timing and status
- File operation results
- Error context and recovery actions
- Final workflow summary

## Key Files to Understand

- `src/main.py`: Entry point with MCP workbench setup and agent orchestration
- `src/core/orchestrator.py`: Core execution logic with intelligent node selection
- `src/core/orchestrator_helpers.py`: Prompt building and execution analysis utilities
- `src/utils/file_naming.py`: Dynamic file path generation from task analysis
- `src/utils/workflow_logger.py`: Structured logging with JSON output

## Error Handling

The system implements sophisticated error recovery:
- **Unit Test Failures**: Automatically trigger refactoring with error context
- **Agent Retries**: Configurable retry limits with exponential backoff
- **Alternative Paths**: Intelligent fallback to different agents when failures persist
- **Stall Detection**: Monitors for infinite loops and triggers replanning