"""Dynamically pause and resume modules based on system load."""

import asyncio
import logging
import threading
import time
from typing import Set

REQUIRES = ["psutil"]

import psutil

from config.settings import (
    DYNAMIC_SCALER_CHECK_INTERVAL,
    DYNAMIC_SCALER_CPU_THRESHOLD,
    DYNAMIC_SCALER_MEMORY_THRESHOLD,
)
from jarvis.core.module_manager import ModuleManager, ModuleState

logger = logging.getLogger(__name__)


class DynamicScaler:
    """Dynamic scaling manager for modules."""
    
    def __init__(
        self,
        manager: ModuleManager,
        interval: int = DYNAMIC_SCALER_CHECK_INTERVAL,
        cpu_threshold: float = DYNAMIC_SCALER_CPU_THRESHOLD,
        memory_threshold: float = DYNAMIC_SCALER_MEMORY_THRESHOLD,
    ) -> None:
        self.manager = manager
        self.interval = interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.running = False
        self._thread: threading.Thread | None = None
        self._paused: Set[str] = set()

    def start(self) -> None:
        """Start the dynamic scaling thread."""
        if self.running:
            return
            
        self.running = True
        self._thread = threading.Thread(
            target=self._run, 
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the dynamic scaling thread."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=0)

    def _run(self) -> None:
        """Main monitoring loop."""
        while self.running:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            
            if cpu > self.cpu_threshold or mem > self.memory_threshold:
                self._pause_low_priority()
            else:
                self._resume_paused()
                
            time.sleep(self.interval)

    def _pause_low_priority(self) -> None:
        """Pause low priority modules."""
        modules = [
            name
            for name, cfg in self.manager.module_configs.items()
            if name in self.manager.modules and cfg.priority >= 50
        ]
        
        for name in modules:
            if name in self._paused:
                continue
                
            try:
                asyncio.run(self.manager.pause_module(name))
                self._paused.add(name)
            except Exception:
                logger.exception("Failed to pause %s", name)

    def _resume_paused(self) -> None:
        """Resume paused modules."""
        for name in list(self._paused):
            if self.manager.module_states.get(name) == ModuleState.PAUSED:
                try:
                    asyncio.run(self.manager.resume_module(name))
                    self._paused.discard(name)
                except Exception:
                    logger.exception("Failed to resume %s", name)