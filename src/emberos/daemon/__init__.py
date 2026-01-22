"""
EmberOS Daemon - The Brain of EmberOS.

The daemon (emberd) is a systemd user service that coordinates all EmberOS
functionality including D-Bus IPC, LLM orchestration, tool execution, and
memory management.
"""

from emberos.daemon.service import EmberDaemon, main
from emberos.daemon.dbus_server import EmberDBusServer
from emberos.daemon.llm_orchestrator import LLMOrchestrator
from emberos.daemon.planner import AgentPlanner
from emberos.daemon.context_monitor import ContextMonitor

__all__ = [
    "EmberDaemon",
    "EmberDBusServer",
    "LLMOrchestrator",
    "AgentPlanner",
    "ContextMonitor",
    "main",
]

