"""
Linux Service Manager for EmberOS.

Provides a compatible interface with Windows service manager but uses systemd.
"""

from __future__ import annotations

import os
import subprocess
import logging
from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum

import psutil

logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """Process state."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class ServiceInfo:
    """Information about a managed service."""
    name: str
    pid: Optional[int]
    state: ProcessState
    port: Optional[int]
    started_at: Optional[float]
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


class LinuxServiceManager:
    """
    Manages EmberOS services on Linux using systemd.
    """

    BITNET_PORT = 38080
    VISION_PORT = 11434

    def __init__(self):
        pass

    def _run_systemctl(self, *args) -> tuple[int, str, str]:
        """Run a systemctl command."""
        cmd = ['systemctl', '--user'] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def _get_service_pid(self, service: str) -> Optional[int]:
        """Get PID of a systemd service."""
        code, stdout, _ = self._run_systemctl('show', service, '--property=MainPID')
        if code == 0 and stdout:
            try:
                pid = int(stdout.strip().split('=')[1])
                return pid if pid > 0 else None
            except (ValueError, IndexError):
                pass
        return None

    def _is_service_active(self, service: str) -> bool:
        """Check if a systemd service is active."""
        code, stdout, _ = self._run_systemctl('is-active', service)
        return code == 0 and stdout.strip() == 'active'

    def get_service_status(self, service: str) -> ServiceInfo:
        """Get status of a service."""
        systemd_name = f"{service}.service"

        if self._is_service_active(systemd_name):
            pid = self._get_service_pid(systemd_name)

            port = None
            if 'bitnet' in service:
                port = self.BITNET_PORT
            elif 'vision' in service or 'llm' in service:
                port = self.VISION_PORT

            cpu_percent = 0.0
            memory_mb = 0.0
            started_at = None

            if pid:
                try:
                    proc = psutil.Process(pid)
                    cpu_percent = proc.cpu_percent()
                    memory_mb = proc.memory_info().rss / (1024 * 1024)
                    started_at = proc.create_time()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return ServiceInfo(
                name=service,
                pid=pid,
                state=ProcessState.RUNNING,
                port=port,
                started_at=started_at,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb
            )

        return ServiceInfo(
            name=service,
            pid=None,
            state=ProcessState.STOPPED,
            port=None,
            started_at=None
        )

    def start_bitnet_server(self) -> bool:
        """Start BitNet server via systemd."""
        # On Linux, both models are managed by ember-llm service
        code, _, _ = self._run_systemctl('start', 'ember-llm')
        return code == 0

    def start_vision_server(self) -> bool:
        """Start vision server via systemd."""
        code, _, _ = self._run_systemctl('start', 'ember-llm')
        return code == 0

    def start_all_llm_servers(self) -> Dict[str, bool]:
        """Start all LLM servers."""
        code, _, _ = self._run_systemctl('start', 'ember-llm')
        success = code == 0
        return {
            'bitnet': success,
            'vision': success
        }

    def stop_service(self, service: str, timeout: int = 10) -> bool:
        """Stop a service."""
        systemd_name = f"{service}.service"
        code, _, _ = self._run_systemctl('stop', systemd_name)
        return code == 0

    def stop_all(self):
        """Stop all managed services."""
        self._run_systemctl('stop', 'ember-llm')

    def restart_service(self, service: str) -> bool:
        """Restart a service."""
        systemd_name = f"{service}.service"
        code, _, _ = self._run_systemctl('restart', systemd_name)
        return code == 0

    def get_all_status(self) -> Dict[str, ServiceInfo]:
        """Get status of all services."""
        return {
            'ember-llm-bitnet': self.get_service_status('ember-llm'),
            'ember-llm-vision': self.get_service_status('ember-llm'),
        }


# Singleton instance
_service_manager: Optional[LinuxServiceManager] = None


def get_service_manager() -> LinuxServiceManager:
    """Get the service manager singleton."""
    global _service_manager
    if _service_manager is None:
        _service_manager = LinuxServiceManager()
    return _service_manager

