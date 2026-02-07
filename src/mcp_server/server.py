"""
MCP (Model Context Protocol) Server

This FastAPI server exposes cloud infrastructure tools to the AI agent
while enforcing SERVICE-SPECIFIC security policies through the Policy Engine.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.guardrails.policy_engine import PolicyEngine, PolicyViolationError
from src.guardrails.impact_simulator import ImpactSimulator
from src.mcp_server.tools import (
    cloud_infra,
    get_service_status,
    list_services,
    read_logs,
    restart_service,
    scale_fleet,
    delete_database
)


# Initialize FastAPI app
app = FastAPI(
    title="Proxi MCP Server",
    description="Service-Specific Cloud Guardian - Policy-Enforced Tool Server",
    version="2.0.0"
)


# Initialize Policy Engine
policy_path = Path(__file__).parent.parent.parent / "policies" / "ops_policy.json"
policy_engine = PolicyEngine(str(policy_path))
impact_simulator = ImpactSimulator()



# Request/Response Models
class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    execution_mode: str = Field(
        default="REAL",
        description="REAL or SHADOW"
    )




    execution_mode: str = Field(
        default="REAL",
        description="REAL or SHADOW"
    )


class ToolResponse(BaseModel):
    """Response model for tool execution."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    policy_violation: bool = False
    blocked_reason: Optional[str] = None


class ModeChangeRequest(BaseModel):
    """Request model for changing operational mode."""
    mode: str = Field(..., description="Mode to switch to (NORMAL or EMERGENCY)")


class IncidentSimulation(BaseModel):
    """Request model for simulating service incidents."""
    service: str = Field(..., description="Service name")
    status: str = Field(default="critical", description="Health status (healthy, degraded, critical)")


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Proxi MCP Server v2.0",
        "status": "operational",
        "current_mode": policy_engine.get_current_mode(),
        "policy_engine": "active",
        "policy_type": "service-specific",
        "unhealthy_services": list(policy_engine.unhealthy_services)
    }


@app.get("/policy/status")
async def get_policy_status():
    """Get current policy configuration and status."""
    return {
        "current_mode": policy_engine.get_current_mode(),
        "allowed_tools": policy_engine.get_allowed_tools(),
        "blocked_tools": policy_engine.get_blocked_tools(),
        "unhealthy_services": list(policy_engine.unhealthy_services),
        "summary": policy_engine.get_policy_summary()
    }


@app.post("/policy/set-mode")
async def set_mode(request: ModeChangeRequest):
    """Change the operational mode (NORMAL or EMERGENCY)."""
    try:
        policy_engine.set_mode(request.mode)
        return {
            "success": True,
            "new_mode": request.mode,
            "allowed_tools": policy_engine.get_allowed_tools(),
            "unhealthy_services": list(policy_engine.unhealthy_services)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tools/execute", response_model=ToolResponse)
async def execute_tool(request: ToolRequest):
    """
    Execute a tool with SERVICE-SPECIFIC policy enforcement.
    
    Key Feature: In EMERGENCY mode, agents can only modify unhealthy services.
    Healthy services are protected.
    """
    tool_name = request.tool_name
    arguments = request.arguments
    context = request.context
    
    print(f"\n🔧 Tool execution request: {tool_name}")
    print(f"   Arguments: {arguments}")
    print(f"   Current mode: {policy_engine.get_current_mode()}")
    print(f"   Unhealthy services: {list(policy_engine.unhealthy_services)}")
    
    # STEP 1: Check current service health for status checks
    # This allows the policy engine to know which services are broken
    if tool_name == "get_service_status":
        result = _execute_tool_function(tool_name, arguments)
        _update_unhealthy_services(arguments.get('service_name'), result)
        print(f"   ✓ Status check completed")
        return ToolResponse(success=True, result=result)
    
    # STEP 2: Validate against SERVICE-SPECIFIC policy
    try:
        policy_engine.validate(tool_name, arguments, context)
    except PolicyViolationError as e:
        print(f"   ❌ BLOCKED by policy: {e.reason}")
        return ToolResponse(
            success=False,
            policy_violation=True,
            blocked_reason=str(e),
            error=f"Policy violation: {e.reason}"
        )
    # STEP 3A: SHADOW MODE — simulate only
    execution_mode = (request.execution_mode or "REAL").upper()

    if execution_mode not in {"REAL", "SHADOW"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid execution_mode. Use REAL or SHADOW."
        )

    if execution_mode == "SHADOW":
        impact = impact_simulator.simulate(
            tool_name,
            arguments,
            cloud_infra
        )

        return ToolResponse(
            success=True,
            result={
                "mode": "SHADOW",
                "impact_report": impact,
                "note": "No real action was executed"
            }
        )



    

    
    try:
        result = _execute_tool_function(tool_name, arguments)
        
        # If restart was successful, mark service as healthy again
        if tool_name == "restart_service" and "success" in str(result).lower():
            service_name = arguments.get('service_name')
            if service_name:
                policy_engine.mark_service_healthy(service_name)
                cloud_infra.set_service_health(service_name, "healthy")
        
        print(f"   ✓ Execution completed successfully")
        return ToolResponse(success=True, result=result)
        
    except Exception as e:
        print(f"   ❌ Execution error: {str(e)}")
        return ToolResponse(
            success=False,
            error=f"Execution error: {str(e)}"
        )


def _update_unhealthy_services(service_name: Optional[str], status_result: Any) -> None:
    """
    Update the policy engine's tracking of unhealthy services.
    
    This is called after status checks to keep the policy engine informed
    about which services are broken and can be modified.
    """
    try:
        # Parse the status result to identify unhealthy services
        result_str = str(status_result)
        
        # Check all services if no specific service requested
        if service_name is None:
            for svc_name, health in cloud_infra.services.items():
                if health in ["critical", "degraded"]:
                    policy_engine.register_unhealthy_service(svc_name)
                elif health == "healthy":
                    policy_engine.mark_service_healthy(svc_name)
        else:
            # Check specific service
            health = cloud_infra.services.get(service_name, "unknown")
            if health in ["critical", "degraded"]:
                policy_engine.register_unhealthy_service(service_name)
            elif health == "healthy":
                policy_engine.mark_service_healthy(service_name)
                
    except Exception as e:
        print(f"   ⚠️  Error updating unhealthy services: {e}")


def _execute_tool_function(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Route tool execution to the appropriate function.
    
    This internal function maps tool names to their implementations.
    """
    tool_map = {
        "get_service_status": get_service_status,
        "read_logs": read_logs,
        "restart_service": restart_service,
        "scale_fleet": scale_fleet,
        "delete_database": delete_database,
        "list_services": list_services
    }
    
    if tool_name not in tool_map:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool_function = tool_map[tool_name]
    
    # Execute the tool with its arguments
    try:
        result = tool_function(**arguments)
        return result
    except TypeError as e:
        raise ValueError(f"Invalid arguments for {tool_name}: {str(e)}")


@app.get("/infrastructure/status")
async def get_infrastructure_status():
    """Get current infrastructure status (diagnostic endpoint)."""
    return {
        "services": cloud_infra.services,
        "fleet_size": cloud_infra.fleet_size,
        "recent_actions": cloud_infra.execution_log[-10:],
        "policy_unhealthy_services": list(policy_engine.unhealthy_services)
    }


@app.post("/infrastructure/simulate-incident")
async def simulate_incident(request: IncidentSimulation):
    """
    Simulate a service incident for demo purposes.
    
    This marks a service as unhealthy both in the infrastructure
    and in the policy engine's tracking.
    """
    service = request.service
    status = request.status
    
    # Update infrastructure
    cloud_infra.set_service_health(service, status)
    
    # Update policy engine tracking
    if status in ["critical", "degraded"]:
        policy_engine.register_unhealthy_service(service)
    else:
        policy_engine.mark_service_healthy(service)
    
    return {
        "success": True,
        "message": f"Simulated incident: {service} set to {status}",
        "infrastructure_status": cloud_infra.services[service],
        "policy_tracking": service in policy_engine.unhealthy_services
    }


@app.post("/infrastructure/fix-service")
async def fix_service(service: str):
    """
    Manually fix a service (for demo purposes).
    
    This marks a service as healthy and removes it from unhealthy tracking.
    """
    cloud_infra.set_service_health(service, "healthy")
    policy_engine.mark_service_healthy(service)
    
    return {
        "success": True,
        "message": f"Service {service} marked as healthy",
        "unhealthy_services": list(policy_engine.unhealthy_services)
    }


# Tool catalog for agent discovery
@app.get("/tools/catalog")
async def get_tool_catalog():
    """Get catalog of available tools with descriptions."""
    return {
        "tools": [
            {
                "name": "list_services",
                "description": "List all available cloud services",
                "parameters": {},
                "category": "read-only"
            },
            {
                "name": "get_service_status",
                "description": "Get the current health status of cloud services",
                "parameters": {
                    "service_name": {
                        "type": "string",
                        "description": "Specific service to check (optional)",
                        "required": False
                    }
                },
                "category": "read-only"
            },
            {
                "name": "read_logs",
                "description": "Read recent system logs",
                "parameters": {
                    "lines": {
                        "type": "integer",
                        "description": "Number of log lines to retrieve",
                        "default": 10
                    }
                },
                "category": "read-only"
            },
            {
                "name": "restart_service",
                "description": "Restart a cloud service (EMERGENCY mode only, ONLY unhealthy services)",
                "parameters": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service to restart",
                        "required": True
                    }
                },
                "category": "active",
                "restrictions": "Can only restart services that are unhealthy"
            },
            {
                "name": "scale_fleet",
                "description": "Scale the number of service instances (EMERGENCY mode only)",
                "parameters": {
                    "count": {
                        "type": "integer",
                        "description": "Target number of instances",
                        "required": True
                    }
                },
                "category": "active"
            },
            {
                "name": "delete_database",
                "description": "Delete a database (ALWAYS BLOCKED)",
                "parameters": {
                    "db_name": {
                        "type": "string",
                        "description": "Name of the database",
                        "required": True
                    }
                },
                "category": "destructive"
            }
        ],
        "current_mode": policy_engine.get_current_mode(),
        "allowed_in_current_mode": policy_engine.get_allowed_tools(),
        "unhealthy_services": list(policy_engine.unhealthy_services)
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("  PROXI MCP SERVER v2.0 - Service-Specific Cloud Guardian")
    print("="*70)
    print(policy_engine.get_policy_summary())
    print("\nStarting server on http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)