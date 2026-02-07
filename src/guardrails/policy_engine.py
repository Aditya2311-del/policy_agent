"""
Policy Engine for Proxi: Service-Specific Cloud Guardian

Enforces granular policies - agents can only fix broken services, not healthy ones.
"""

import json
from typing import Dict, Any, List, Set
from pathlib import Path
from datetime import datetime


class PolicyViolationError(Exception):
    """Raised when an action violates the current security policy."""
    
    def __init__(self, message: str, tool_name: str, mode: str, reason: str):
        self.tool_name = tool_name
        self.mode = mode
        self.reason = reason
        super().__init__(message)


class PolicyEngine:
    """
    Enforces service-specific security policies.
    
    Key Feature: In EMERGENCY mode, agents can only modify services that are unhealthy.
    Healthy services are protected from unnecessary changes.
    """
    
    def __init__(self, policy_path: str):
        self.policy_path = Path(policy_path)
        self.policy = self._load_policy()
        self.current_mode = "NORMAL"
        self.unhealthy_services: Set[str] = set()  # Track which services are broken
        
    def _load_policy(self) -> Dict[str, Any]:
        """Load policy configuration."""
        if not self.policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {self.policy_path}")
        
        with open(self.policy_path, 'r') as f:
            policy = json.load(f)
        
        print(f"✓ Loaded policy: {policy.get('policy_name', 'Unknown')} v{policy.get('version', '?')}")
        return policy
    
    def set_mode(self, mode: str) -> None:
        """Change operational mode."""
        if mode not in self.policy['modes']:
            raise ValueError(f"Invalid mode: {mode}")
        
        self.current_mode = mode
        print(f"\n🔄 Mode: {mode}")
        print(f"   {self.policy['modes'][mode]['description']}")
    
    def register_unhealthy_service(self, service_name: str) -> None:
        """
        Mark a service as unhealthy.
        Only unhealthy services can be modified in EMERGENCY mode.
        """
        self.unhealthy_services.add(service_name)
        print(f"⚠️  Registered unhealthy service: {service_name}")
    
    def mark_service_healthy(self, service_name: str) -> None:
        """Remove a service from the unhealthy list after it's fixed."""
        self.unhealthy_services.discard(service_name)
        print(f"✓ Service marked healthy: {service_name}")
    
    def validate(self, tool_name: str, args: Dict[str, Any] = None, context: Dict[str, Any] = None) -> bool:
        """
        Validate if a tool execution is allowed.
        
        Key Logic:
        - Read operations: Always allowed
        - Write operations in NORMAL mode: Blocked
        - Write operations in EMERGENCY mode: Only allowed on unhealthy services
        """
        args = args or {}
        context = context or {}
        
        # Always blocked tools (destructive operations)
        if tool_name in self.policy['global_rules']['always_blocked']:
            raise PolicyViolationError(
                f"'{tool_name}' is permanently blocked - destructive operation",
                tool_name=tool_name,
                mode=self.current_mode,
                reason="Globally blocked"
            )
        
        mode_policy = self.policy['modes'][self.current_mode]
        
        # Check if tool is blocked in current mode
        if tool_name in mode_policy['blocked_tools']:
            raise PolicyViolationError(
                f"'{tool_name}' blocked in {self.current_mode} mode",
                tool_name=tool_name,
                mode=self.current_mode,
                reason=mode_policy['rationale']
            )
        
        # Check if tool is allowed
        if tool_name not in mode_policy['allowed_tools']:
            raise PolicyViolationError(
                f"'{tool_name}' not whitelisted for {self.current_mode} mode",
                tool_name=tool_name,
                mode=self.current_mode,
                reason="Not in allowed tools list"
            )
        
        # SERVICE-SPECIFIC CHECK (the key feature!)
        # For modification tools, verify they target only unhealthy services
        if self._is_modification_tool(tool_name):
            service_name = args.get('service_name')
            
            if not service_name:
                raise PolicyViolationError(
                    f"'{tool_name}' requires a service_name parameter",
                    tool_name=tool_name,
                    mode=self.current_mode,
                    reason="Missing service target"
                )
            
            # In EMERGENCY mode, check if service is actually unhealthy
            if self.current_mode == "EMERGENCY":
                restrictions = mode_policy.get('service_restrictions', {})
                if restrictions.get('enabled', False):
                    if service_name not in self.unhealthy_services:
                        raise PolicyViolationError(
                            f"Cannot modify '{service_name}' - service is healthy. "
                            f"Only broken services can be modified: {list(self.unhealthy_services)}",
                            tool_name=tool_name,
                            mode=self.current_mode,
                            reason="Target service is not unhealthy"
                        )
        
        print(f"  ✓ Policy OK: {tool_name} allowed for {args.get('service_name', 'all services')}")
        return True
    
    def _is_modification_tool(self, tool_name: str) -> bool:
        """Check if a tool modifies system state (vs just reading)."""
        modification_tools = ['restart_service', 'scale_fleet', 'delete_database']
        return tool_name in modification_tools
    
    def get_current_mode(self) -> str:
        return self.current_mode
    
    def get_allowed_tools(self) -> List[str]:
        return self.policy['modes'][self.current_mode]['allowed_tools']
    
    def get_blocked_tools(self) -> List[str]:
        """Get the list of tools blocked in the current mode."""
        return self.policy['modes'][self.current_mode]['blocked_tools']
    
    def get_policy_summary(self) -> str:
        """Show current policy state."""
        mode_info = self.policy['modes'][self.current_mode]
        
        summary = f"""
╔═══════════════════════════════════════════════════════════╗
║  POLICY STATUS                                            ║
╠═══════════════════════════════════════════════════════════╣
║  Mode: {self.current_mode:<50} ║
║  {mode_info['description']:<58}║
╠═══════════════════════════════════════════════════════════╣
║  Unhealthy Services (can modify):                         ║
"""
        if self.unhealthy_services:
            for svc in self.unhealthy_services:
                summary += f"║    🔴 {svc:<52} ║\n"
        else:
            summary += f"║    (none - all services healthy)                      ║\n"
        
        summary += "╠═══════════════════════════════════════════════════════════╣\n"
        summary += f"║  Allowed: {', '.join(mode_info['allowed_tools'][:2]):<46}║\n"
        summary += f"║  Blocked: {', '.join(mode_info['blocked_tools'][:2]):<46}║\n"
        summary += "╚═══════════════════════════════════════════════════════════╝"
        
        return summary
    
    def _format_tool_list(self, tools: List[str]) -> str:
        """Format a list of tools for the summary display."""
        if not tools:
            return "║    (none)                                                      ║"
        
        lines = []
        for tool in tools:
            lines.append(f"║    • {tool:<56} ║")
        return "\n".join(lines)
