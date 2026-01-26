"""
Windows Service Manager for EmberOS.

Handles LLM server management and daemon control on Windows.
Uses subprocess management instead of systemd.
"""

from __future__ import annotations

import os
import sys
import subprocess
import time
import logging
import asyncio
import atexit
from pathlib import Path
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


class WindowsServiceManager:
    """
    Manages EmberOS services on Windows.

    Services:
    - ember-llm-bitnet: BitNet text model server
    - ember-llm-vision: Qwen2.5-VL vision model server
    - emberd: EmberOS daemon
    """

    # Configuration
    EMBER_DIR = Path(os.environ.get('LOCALAPPDATA', '')) / 'EmberOS'
    MODEL_DIR = EMBER_DIR / 'models'
    LOG_DIR = EMBER_DIR / 'logs'
    PID_DIR = EMBER_DIR / 'run'

    # Default ports (using less common ports)
    BITNET_PORT = 38080
    VISION_PORT = 11434

    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}
        self._ensure_dirs()

        # Register cleanup on exit
        atexit.register(self.stop_all)

    def _ensure_dirs(self):
        """Ensure required directories exist."""
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.PID_DIR.mkdir(parents=True, exist_ok=True)

    def _find_llama_server(self) -> Optional[Path]:
        """Find llama-server executable."""
        # Check PATH
        import shutil
        llama_path = shutil.which('llama-server')
        if llama_path:
            return Path(llama_path)

        # Check common locations
        common_paths = [
            Path(os.environ.get('PROGRAMFILES', '')) / 'llama.cpp' / 'llama-server.exe',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'llama.cpp' / 'llama-server.exe',
            Path.home() / 'llama.cpp' / 'llama-server.exe',
            Path.home() / 'llama.cpp' / 'build' / 'bin' / 'Release' / 'llama-server.exe',
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def _read_pid_file(self, service: str) -> Optional[int]:
        """Read PID from file."""
        pid_file = self.PID_DIR / f"{service}.pid"
        if pid_file.exists():
            try:
                return int(pid_file.read_text().strip())
            except (ValueError, IOError):
                pass
        return None

    def _write_pid_file(self, service: str, pid: int):
        """Write PID to file."""
        pid_file = self.PID_DIR / f"{service}.pid"
        pid_file.write_text(str(pid))

    def _remove_pid_file(self, service: str):
        """Remove PID file."""
        pid_file = self.PID_DIR / f"{service}.pid"
        if pid_file.exists():
            pid_file.unlink()

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running."""
        try:
            process = psutil.Process(pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def get_service_status(self, service: str) -> ServiceInfo:
        """Get status of a service."""
        pid = self._read_pid_file(service)

        if pid and self._is_process_running(pid):
            try:
                process = psutil.Process(pid)
                port = None

                # Determine port based on service
                if 'bitnet' in service:
                    port = self.BITNET_PORT
                elif 'vision' in service:
                    port = self.VISION_PORT

                return ServiceInfo(
                    name=service,
                    pid=pid,
                    state=ProcessState.RUNNING,
                    port=port,
                    started_at=process.create_time(),
                    cpu_percent=process.cpu_percent(),
                    memory_mb=process.memory_info().rss / (1024 * 1024)
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return ServiceInfo(
            name=service,
            pid=None,
            state=ProcessState.STOPPED,
            port=None,
            started_at=None
        )

    def start_bitnet_server(self) -> bool:
        """Start BitNet text model server."""
        service = 'ember-llm-bitnet'

        # Check if already running
        status = self.get_service_status(service)
        if status.state == ProcessState.RUNNING:
            logger.info(f"{service} already running (PID: {status.pid})")
            return True

        # Find llama-server
        llama_server = self._find_llama_server()
        if not llama_server:
            logger.error("llama-server not found")
            return False

        # Find model
        model_path = self.MODEL_DIR / 'bitnet' / 'ggml-model-i2_s.gguf'
        if not model_path.exists():
            logger.error(f"BitNet model not found: {model_path}")
            return False

        # Check port
        if self._is_port_in_use(self.BITNET_PORT):
            logger.warning(f"Port {self.BITNET_PORT} already in use")
            return False

        # Start server
        log_file = self.LOG_DIR / f"{service}.log"

        cmd = [
            str(llama_server),
            '--model', str(model_path),
            '--host', '127.0.0.1',
            '--port', str(self.BITNET_PORT),
            '--ctx-size', '4096',
            '--threads', '4',
            '--n-gpu-layers', '0',
            '--temp', '0.1',
        ]

        logger.info(f"Starting {service} on port {self.BITNET_PORT}...")

        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

        self._processes[service] = process
        self._write_pid_file(service, process.pid)

        # Wait a bit and check if it started
        time.sleep(2)
        if process.poll() is not None:
            logger.error(f"{service} failed to start")
            self._remove_pid_file(service)
            return False

        logger.info(f"{service} started (PID: {process.pid})")
        return True

    def start_vision_server(self) -> bool:
        """Start Qwen2.5-VL vision model server."""
        service = 'ember-llm-vision'

        # Check if already running
        status = self.get_service_status(service)
        if status.state == ProcessState.RUNNING:
            logger.info(f"{service} already running (PID: {status.pid})")
            return True

        # Find llama-server
        llama_server = self._find_llama_server()
        if not llama_server:
            logger.error("llama-server not found")
            return False

        # Find model
        model_path = self.MODEL_DIR / 'qwen2.5-vl-7b-instruct-q4_k_m.gguf'
        if not model_path.exists():
            logger.error(f"Vision model not found: {model_path}")
            return False

        # Check port
        if self._is_port_in_use(self.VISION_PORT):
            logger.warning(f"Port {self.VISION_PORT} already in use")
            return False

        # Start server
        log_file = self.LOG_DIR / f"{service}.log"

        cmd = [
            str(llama_server),
            '--model', str(model_path),
            '--host', '127.0.0.1',
            '--port', str(self.VISION_PORT),
            '--ctx-size', '8192',
            '--threads', '4',
            '--n-gpu-layers', '0',
        ]

        logger.info(f"Starting {service} on port {self.VISION_PORT}...")

        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

        self._processes[service] = process
        self._write_pid_file(service, process.pid)

        # Wait a bit and check if it started
        time.sleep(2)
        if process.poll() is not None:
            logger.error(f"{service} failed to start")
            self._remove_pid_file(service)
            return False

        logger.info(f"{service} started (PID: {process.pid})")
        return True

    def start_all_llm_servers(self) -> Dict[str, bool]:
        """Start all LLM servers."""
        results = {}
        results['bitnet'] = self.start_bitnet_server()
        results['vision'] = self.start_vision_server()
        return results

    def stop_service(self, service: str, timeout: int = 10) -> bool:
        """Stop a service."""
        pid = self._read_pid_file(service)

        if not pid:
            logger.info(f"{service} not running (no PID file)")
            return True

        if not self._is_process_running(pid):
            logger.info(f"{service} not running (process gone)")
            self._remove_pid_file(service)
            return True

        logger.info(f"Stopping {service} (PID: {pid})...")

        try:
            process = psutil.Process(pid)

            # Try graceful termination first
            process.terminate()

            try:
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                logger.warning(f"{service} did not stop gracefully, killing...")
                process.kill()
                process.wait(timeout=5)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        # Clean up
        self._remove_pid_file(service)
        if service in self._processes:
            del self._processes[service]

        logger.info(f"{service} stopped")
        return True

    def stop_all(self):
        """Stop all managed services."""
        services = ['ember-llm-bitnet', 'ember-llm-vision']
        for service in services:
            try:
                self.stop_service(service)
            except Exception as e:
                logger.error(f"Error stopping {service}: {e}")

    def restart_service(self, service: str) -> bool:
        """Restart a service."""
        self.stop_service(service)
        time.sleep(1)

        if 'bitnet' in service:
            return self.start_bitnet_server()
        elif 'vision' in service:
            return self.start_vision_server()

        return False

    def get_all_status(self) -> Dict[str, ServiceInfo]:
        """Get status of all services."""
        services = ['ember-llm-bitnet', 'ember-llm-vision']
        return {s: self.get_service_status(s) for s in services}

    async def wait_for_health(self, port: int, timeout: int = 30) -> bool:
        """Wait for a server to become healthy."""
        import aiohttp

        url = f"http://127.0.0.1:{port}/health"
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < timeout:
                try:
                    async with session.get(url, timeout=2) as resp:
                        if resp.status == 200:
                            return True
                except:
                    pass
                await asyncio.sleep(1)

        return False


# Singleton instance
_service_manager: Optional[WindowsServiceManager] = None


def get_service_manager() -> WindowsServiceManager:
    """Get the service manager singleton."""
    global _service_manager
    if _service_manager is None:
        _service_manager = WindowsServiceManager()
    return _service_manager


def main():
    """CLI for service management."""
    import argparse

    parser = argparse.ArgumentParser(description='EmberOS Windows Service Manager')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'],
                       help='Action to perform')
    parser.add_argument('--service', '-s',
                       choices=['bitnet', 'vision', 'all'],
                       default='all',
                       help='Service to manage')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    manager = get_service_manager()

    if args.action == 'status':
        statuses = manager.get_all_status()
        for name, info in statuses.items():
            state_icon = "●" if info.state == ProcessState.RUNNING else "○"
            port_str = f" (port {info.port})" if info.port else ""
            pid_str = f" PID: {info.pid}" if info.pid else ""
            print(f"{state_icon} {name}: {info.state.value}{port_str}{pid_str}")
            if info.state == ProcessState.RUNNING:
                print(f"    Memory: {info.memory_mb:.1f} MB, CPU: {info.cpu_percent:.1f}%")

    elif args.action == 'start':
        if args.service == 'all':
            results = manager.start_all_llm_servers()
            for svc, ok in results.items():
                print(f"{'✓' if ok else '✗'} {svc}")
        elif args.service == 'bitnet':
            ok = manager.start_bitnet_server()
            print(f"{'✓' if ok else '✗'} BitNet server")
        elif args.service == 'vision':
            ok = manager.start_vision_server()
            print(f"{'✓' if ok else '✗'} Vision server")

    elif args.action == 'stop':
        if args.service == 'all':
            manager.stop_all()
            print("All services stopped")
        else:
            svc_name = f'ember-llm-{args.service}'
            manager.stop_service(svc_name)
            print(f"{svc_name} stopped")

    elif args.action == 'restart':
        if args.service == 'all':
            manager.stop_all()
            time.sleep(2)
            results = manager.start_all_llm_servers()
            for svc, ok in results.items():
                print(f"{'✓' if ok else '✗'} {svc}")
        else:
            svc_name = f'ember-llm-{args.service}'
            manager.restart_service(svc_name)
            print(f"{svc_name} restarted")


if __name__ == '__main__':
    main()

