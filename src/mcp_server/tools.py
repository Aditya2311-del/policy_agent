"""
Mock Cloud Infrastructure Tools

This module simulates cloud infrastructure management tools that an AI agent
might use to manage services, databases, and fleet scaling.

Now includes health status tracking for service-specific policy enforcement.
"""

import random
from typing import Dict, Any, List
from datetime import datetime


class CloudInfrastructure:
    """
    Mock cloud infrastructure providing simulated services.
    
    This class simulates a cloud environment with services that can be
    in different states (healthy, degraded, critical).
    """
    
    def __init__(self):
        """Initialize the mock cloud infrastructure."""
        self.services = {
            "web-server": "healthy",
            "api-gateway": "healthy",
            "database": "healthy",
            "cache": "healthy",
            "load-balancer": "healthy"
        }
        self.fleet_size = 3
        self.execution_log = []
    
    def list_services(self) -> Dict[str, Any]:
        """List all available services."""
        self._log_action("list_services", {})
        return {
            "services": list(self.services.keys()),
            "count": len(self.services),
            "timestamp": datetime.now().isoformat()
        }

    def _log_action(self, action: str, details: Dict[str, Any]) -> None:
        """Log all infrastructure actions for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        self.execution_log.append(log_entry)
        # Keep only last 100 entries
        if len(self.execution_log) > 100:
            self.execution_log = self.execution_log[-100:]
    
    def set_service_health(self, service: str, status: str) -> None:
        """
        Manually set service health for demo scenarios.
        
        Args:
            service: Service name
            status: Health status (healthy, degraded, critical)
        """
        if service in self.services:
            old_status = self.services[service]
            self.services[service] = status
            self._log_action("health_change", {
                "service": service,
                "old_status": old_status,
                "new_status": status
            })
            print(f"    📊 Health updated: {service} {old_status} → {status}")
    
    def get_unhealthy_services(self) -> List[str]:
        """Get list of services that are not healthy."""
        return [
            name for name, health in self.services.items()
            if health in ["critical", "degraded"]
        ]
    
    def get_service_status(self, service_name: str = None) -> Dict[str, Any]:
        """
        Get the current status of cloud services.
        
        This is a READ-ONLY operation allowed in all modes.
        
        Args:
            service_name: Optional specific service to check. If None, returns all services.
        
        Returns:
            Dictionary containing service status information
        """
        self._log_action("get_service_status", {"service": service_name})
        
        if service_name:
            if service_name not in self.services:
                return {
                    "status": "error",
                    "message": f"Service '{service_name}' not found",
                    "available_services": list(self.services.keys())
                }
            
            health = self.services[service_name]
            health_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "critical": "🔴"
            }.get(health, "❓")
            
            return {
                "service": service_name,
                "health": health,
                "status_emoji": health_emoji,
                "is_healthy": health == "healthy",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Return status of all services
            unhealthy = self.get_unhealthy_services()
            
            return {
                "services": self.services,
                "fleet_size": self.fleet_size,
                "unhealthy_count": len(unhealthy),
                "unhealthy_services": unhealthy,
                "all_healthy": len(unhealthy) == 0,
                "timestamp": datetime.now().isoformat()
            }
    
    def read_logs(self, lines: int = 10) -> Dict[str, Any]:
        """
        Read system logs.
        
        This is a READ-ONLY operation allowed in all modes.
        
        Args:
            lines: Number of recent log lines to retrieve
        
        Returns:
            Dictionary containing recent log entries
        """
        self._log_action("read_logs", {"lines": lines})
        
        # Generate dynamic log entries based on current service states
        log_entries = []
        
        for service, health in self.services.items():
            if health == "healthy":
                log_entries.append(f"[INFO] {service}: Operating normally")
            elif health == "degraded":
                log_entries.append(f"[WARN] {service}: Performance degraded, response time elevated")
            elif health == "critical":
                log_entries.append(f"[ERROR] {service}: Service experiencing critical issues!")
        
        # Add some general logs
        log_entries.extend([
            f"[INFO] Fleet health check: {self.fleet_size} instances responding",
            f"[INFO] Total services monitored: {len(self.services)}",
            f"[INFO] Execution log entries: {len(self.execution_log)}"
        ])
        
        return {
            "log_lines": log_entries[:lines],
            "timestamp": datetime.now().isoformat(),
            "total_available": len(log_entries),
            "services_logged": len(self.services)
        }
    
    def restart_service(self, service_name: str) -> Dict[str, Any]:
        """
        Restart a cloud service.
        
        This is an ACTIVE operation only allowed in EMERGENCY mode
        and only for UNHEALTHY services.
        
        Args:
            service_name: Name of the service to restart
        
        Returns:
            Dictionary containing restart operation results
        """
        self._log_action("restart_service", {"service": service_name})
        
        if service_name not in self.services:
            return {
                "status": "error",
                "message": f"Service '{service_name}' not found",
                "available_services": list(self.services.keys())
            }
        
        old_health = self.services[service_name]
        
        print(f"    🔄 EXECUTING: Restarting service '{service_name}'...")
        print(f"       • Previous health: {old_health}")
        print(f"       • Stopping service...")
        print(f"       • Clearing cache...")
        print(f"       • Starting service...")
        
        # Simulate service restart improving health
        self.services[service_name] = "healthy"
        
        print(f"       • New health: healthy ✅")
        
        return {
            "status": "success",
            "service": service_name,
            "action": "restart",
            "old_health": old_health,
            "new_health": "healthy",
            "message": f"Service '{service_name}' successfully restarted and recovered",
            "timestamp": datetime.now().isoformat()
        }
    
    def scale_fleet(self, count: int) -> Dict[str, Any]:
        """
        Scale the number of service instances.
        
        This is an ACTIVE operation only allowed in EMERGENCY mode.
        
        Args:
            count: Target number of instances
        
        Returns:
            Dictionary containing scaling operation results
        """
        self._log_action("scale_fleet", {"target_count": count})
        
        if count < 1:
            return {
                "status": "error",
                "message": "Fleet size must be at least 1"
            }
        
        if count > 100:
            return {
                "status": "error",
                "message": "Fleet size cannot exceed 100 instances"
            }
        
        old_size = self.fleet_size
        self.fleet_size = count
        
        print(f"    📊 EXECUTING: Scaling fleet from {old_size} to {count} instances...")
        print(f"       • Provisioning new instances...")
        print(f"       • Updating load balancer...")
        print(f"       • Health checking new instances...")
        print(f"       • Fleet scaled successfully ✅")
        
        return {
            "status": "success",
            "action": "scale",
            "old_size": old_size,
            "new_size": count,
            "change": count - old_size,
            "message": f"Fleet scaled from {old_size} to {count} instances",
            "timestamp": datetime.now().isoformat()
        }
    
    def delete_database(self, db_name: str) -> Dict[str, Any]:
        """
        Delete a database.
        
        This is a DESTRUCTIVE operation that is ALWAYS BLOCKED by policy.
        
        Args:
            db_name: Name of the database to delete
        
        Returns:
            Dictionary containing deletion attempt results
        """
        self._log_action("delete_database_attempt", {"db_name": db_name})
        
        print(f"    ⚠️  CRITICAL: Attempting to delete database '{db_name}'...")
        print(f"       ❌ THIS OPERATION SHOULD BE BLOCKED BY POLICY ENGINE")
        
        return {
            "status": "error",
            "message": "This operation should never execute - policy violation!",
            "db_name": db_name,
            "timestamp": datetime.now().isoformat()
        }


# Global infrastructure instance
cloud_infra = CloudInfrastructure()


# Tool function wrappers for agent integration
def get_service_status(service_name: str = None) -> str:
    """Get cloud service status - READ ONLY."""
    result = cloud_infra.get_service_status(service_name)
    return str(result)


def list_services() -> str:
    """List all available services - READ ONLY."""
    result = cloud_infra.list_services()
    return str(result)


def read_logs(lines: int = 10) -> str:
    """Read system logs - READ ONLY."""
    result = cloud_infra.read_logs(lines)
    return str(result)


def restart_service(service_name: str) -> str:
    """Restart a service - ACTIVE OPERATION (unhealthy services only)."""
    result = cloud_infra.restart_service(service_name)
    return str(result)


def scale_fleet(count: int) -> str:
    """Scale fleet size - ACTIVE OPERATION."""
    result = cloud_infra.scale_fleet(count)
    return str(result)


def delete_database(db_name: str) -> str:
    """Delete a database - DESTRUCTIVE OPERATION (ALWAYS BLOCKED)."""
    result = cloud_infra.delete_database(db_name)
    return str(result)