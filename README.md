# Proxi: The Context-Aware Cloud Guardian

**ArmorIQ Hackathon Project**

An AI Agent system demonstrating **Policy Enforcement** and **Context-Aware Security** for cloud infrastructure management.

## 🎯 Overview

Proxi is a demonstration of how AI agents can be safely constrained using policy engines. The system shows a realistic scenario where an AI Site Reliability Engineer (SRE) manages cloud infrastructure but is strictly limited by context-aware security policies.

### Key Features

- **Policy Engine**: Validates every agent action against operational policies
- **Context-Aware Security**: Different permissions based on operational mode (NORMAL vs EMERGENCY)
- **Defense in Depth**: Certain destructive operations are always blocked, regardless of mode
- **MCP Server**: FastAPI-based tool server with built-in policy enforcement
- **AI Agent**: LangChain-powered agent that respects constraints and explains policy violations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI AGENT                                 │
│                    (LangChain-based SRE)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Tool Calls
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP SERVER                                  │
│                     (FastAPI)                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              POLICY ENGINE                               │   │
│  │  • Validates all actions against policy                  │   │
│  │  • Enforces mode-based constraints                       │   │
│  │  • Blocks destructive operations                         │   │
│  └────────────────┬─────────────────────────────────────────┘   │
│                   │                                              │
│                   ▼                                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         CLOUD INFRASTRUCTURE TOOLS                       │   │
│  │  • get_service_status (read-only)                        │   │
│  │  • read_logs (read-only)                                 │   │
│  │  • restart_service (emergency only)                      │   │
│  │  • scale_fleet (emergency only)                          │   │
│  │  • delete_database (always blocked)                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Policy Rules

### NORMAL Mode (Read-Only)
✅ **Allowed:**
- `get_service_status` - Check service health
- `read_logs` - View system logs

❌ **Blocked:**
- `restart_service` - Cannot modify services
- `scale_fleet` - Cannot change infrastructure
- `delete_database` - Always blocked

### EMERGENCY Mode (Corrective Actions)
✅ **Allowed:**
- `get_service_status` - Check service health
- `read_logs` - View system logs
- `restart_service` - Fix critical services
- `scale_fleet` - Handle load issues

❌ **Blocked:**
- `delete_database` - Always blocked (data protection)

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip

### Installation

1. **Clone or download the project:**
   ```bash
   cd proxi-armoriq
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Demo

The demo runs with a **mock LLM** by default, so no API keys are required!

```bash
python main.py
```

This will:
1. Start the MCP server on http://localhost:8000
2. Initialize the AI agent
3. Run three demonstration scenarios
4. Show the complete thought → action → policy enforcement flow

### Expected Output

```
================================================================================
                    PROXI: THE CONTEXT-AWARE CLOUD GUARDIAN
                         ArmorIQ Hackathon Demo
================================================================================

┌──────────────────────────────────────────────────────────────────────────────┐
│ SCENARIO 1: NORMAL MODE - Corrective Action Blocked                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Agent attempts to restart a service but is blocked by policy                │
└──────────────────────────────────────────────────────────────────────────────┘

🤖 Agent reasoning process:
   → Thought: The task requires restarting a service
   → Action: Attempting to use restart_service tool
   → Observation: ❌ POLICY BLOCKED: Tool 'restart_service' is blocked in NORMAL mode

💬 Agent response:
I attempted to restart the web-server, but the operation was blocked by policy.
This is because we are in NORMAL mode that only allows read-only operations...
```

## 🧪 Testing Individual Components

### Test the Policy Engine
```bash
python -c "
from src.guardrails.policy_engine import PolicyEngine

engine = PolicyEngine('policies/ops_policy.json')
print(engine.get_policy_summary())

# Test validation
try:
    engine.validate('restart_service')
except Exception as e:
    print(f'Blocked: {e}')

engine.set_mode('EMERGENCY')
engine.validate('restart_service')  # Should pass
print('✓ Restart allowed in EMERGENCY mode')
"
```

### Test the MCP Server
```bash
# In one terminal, start the server:
python -m uvicorn src.mcp_server.server:app --reload

# In another terminal, test the API:
curl http://localhost:8000/policy/status
curl -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_service_status", "arguments": {}}'
```

### Explore the API
Visit http://localhost:8000/docs for interactive API documentation.

## 📁 Project Structure

```
proxi-armoriq/
├── main.py                          # Demo orchestration script
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── policies/
│   └── ops_policy.json             # Security policy definition
│
└── src/
    ├── guardrails/
    │   ├── __init__.py
    │   └── policy_engine.py        # Core policy enforcement
    │
    ├── mcp_server/
    │   ├── __init__.py
    │   ├── tools.py                # Mock cloud infrastructure
    │   └── server.py               # FastAPI MCP server
    │
    └── agent/
        ├── __init__.py
        └── bot.py                  # LangChain AI agent
```

## 🔧 Using Real LLMs

To use real LLMs instead of the mock:

1. **Create a `.env` file:**
   ```bash
   # For OpenAI
   OPENAI_API_KEY=your_key_here
   
   # OR for Anthropic
   ANTHROPIC_API_KEY=your_key_here
   ```

2. **Modify the agent initialization in `main.py`:**
   ```python
   agent = ProxiAgent(use_mock=False)  # Change True to False
   ```

## 🎓 Educational Value

This project demonstrates several important concepts:

1. **AI Safety**: How to build guardrails that enforce security policies
2. **Context-Aware Security**: Different permissions based on operational context
3. **Agent Architecture**: Separation of reasoning (agent) from execution (tools)
4. **Policy as Code**: Declarative policy definitions that are easy to audit
5. **Fail-Safe Design**: Critical operations blocked regardless of context

## 🔒 Security Highlights

- **Every** tool execution goes through policy validation
- Policy violations raise exceptions before execution
- Agent is informed of policy constraints and explains them to users
- Destructive operations have absolute blocks (defense in depth)
- All actions are logged for audit trails

## 🛠️ Extending the Project

### Add New Tools
1. Define the tool function in `src/mcp_server/tools.py`
2. Add it to the policy in `policies/ops_policy.json`
3. Register it in the MCP server's `_execute_tool_function`
4. Add it to the agent's tool list in `src/agent/bot.py`

### Add New Modes
1. Define the mode in `policies/ops_policy.json` with its allowed/blocked tools
2. The policy engine automatically supports new modes
3. Update the demo scenarios in `main.py` to showcase the new mode

### Advanced Policies
The policy engine's `validate()` method accepts `args` and `context` parameters for future enhancements like:
- Parameter-based validation (e.g., only allow scaling up to 10 instances)
- Time-based constraints (e.g., no destructive operations during business hours)
- User-based permissions (e.g., different rules for different operators)

## 📊 Demo Scenarios

### Scenario 1: Normal Mode Block
- **Setup**: System in NORMAL mode
- **Task**: "Restart the web server"
- **Result**: ❌ Blocked - read-only mode
- **Learning**: Agent explains why action is blocked and suggests alternatives

### Scenario 2: Emergency Mode Success
- **Setup**: Critical service failure, EMERGENCY mode
- **Task**: "Fix the critical web server issue"
- **Result**: ✅ Success - restart allowed
- **Learning**: Context-aware policies enable appropriate responses

### Scenario 3: Always Blocked
- **Setup**: EMERGENCY mode active
- **Task**: "Delete the database to clear space"
- **Result**: ❌ Blocked - destructive operation
- **Learning**: Some operations are never allowed, ensuring data safety

## 🤝 Contributing

This is a hackathon demo project. Feel free to:
- Fork and enhance the policy engine
- Add more realistic cloud tools
- Implement real monitoring integrations
- Add more sophisticated agent reasoning
- Create UI for policy management

## 📝 License

This project is created for the ArmorIQ Hackathon. Feel free to use and modify for educational purposes.

## 🙏 Acknowledgments

Built with:
- [LangChain](https://www.langchain.com/) - Agent framework
- [FastAPI](https://fastapi.tiangolo.com/) - MCP server
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation

---

**Proxi: Because even AI agents need guardrails.** 🛡️
# policy_agent
