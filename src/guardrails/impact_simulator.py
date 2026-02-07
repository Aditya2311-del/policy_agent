from typing import Dict, Any
from datetime import datetime

class ImpactSimulator:
    """
    Simulates tool execution WITHOUT performing real actions.
    """

    def simulate(self, tool_name: str, args: Dict[str, Any], infra) -> Dict[str, Any]:

        if tool_name == "restart_service":
            service = args.get("service_name")
            health = infra.services.get(service, "unknown")

            return {
                "action": "restart_service",
                "service": service,
                "current_health": health,
                "predicted_effect": "Temporary service downtime during restart",
                "estimated_downtime_seconds": 10,
                "affected_users_estimate": 200,
                "risk_level": "medium",
                "reversible": True,
                "timestamp": datetime.now().isoformat()
            }

        if tool_name == "scale_fleet":
            current = infra.fleet_size
            target = args.get("count")

            return {
                "action": "scale_fleet",
                "current_size": current,
                "target_size": target,
                "estimated_cost_delta": (target - current) * 4000,
                "risk_level": "medium",
                "reversible": True,
                "timestamp": datetime.now().isoformat()
            }

        if tool_name == "delete_database":
            return {
                "action": "delete_database",
                "risk_level": "CRITICAL",
                "reversible": False,
                "warning": "Permanent data loss"
            }

        return {
            "summary": "No significant impact predicted",
            "risk_level": "low",
            "reversible": True
        }
