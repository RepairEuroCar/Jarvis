import asyncio
import logging
import re
import shlex
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ScanResult:
    target: str
    output: str
    success: bool
    timestamp: float
    command: str
    duration: float = 0.0

class KaliTools:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.scan_history: List[ScanResult] = []
        self.profiles: Dict[str, Dict] = {}
        self.load_profiles()
        self.active_scans: Dict[str, asyncio.Task] = {}

    async def _execute_command(self, command: List[str]) -> ScanResult:
        """Execute command with timing and enhanced output"""
        start_time = asyncio.get_event_loop().time()
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            duration = asyncio.get_event_loop().time() - start_time
            
            output = stdout.decode().strip()
            if stderr:
                output += f"\nERRORS:\n{stderr.decode().strip()}"
            
            result = ScanResult(
                target=command[-1],
                output=output,
                success=process.returncode == 0,
                timestamp=start_time,
                command=" ".join(command),
                duration=duration
            )
            
            self.scan_history.append(result)
            self.save_history()
            return result
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            return ScanResult(
                target=command[-1],
                output=str(e),
                success=False,
                timestamp=start_time,
                command=" ".join(command),
                duration=asyncio.get_event_loop().time() - start_time
            )

    # Nmap enhanced functionality
    async def run_nmap(self, target: str, options: str = "", profile: str = None) -> ScanResult:
        """Run nmap with profile support"""
        if profile and profile in self.profiles.get('nmap', {}):
            options = self.profiles['nmap'][profile]
        
        cmd = ["nmap"] + shlex.split(options) + [target]
        return await self._execute_command(cmd)

    async def nmap_os_detection(self, target: str) -> ScanResult:
        """Enhanced OS detection scan"""
        return await self.run_nmap(target, "-O -sV --fuzzy --osscan-limit")

    async def nmap_full_scan(self, target: str) -> ScanResult:
        """Comprehensive scan with all checks"""
        return await self.run_nmap(target, "-sS -sU -T4 -A -v -PE -PP -PS80,443 -PA3389 -PU40125 -PY -g 53")

    # Hydra enhanced functionality
    async def run_hydra(
        self,
        service: str,
        target: str,
        userlist: str = None,
        passlist: str = None,
        options: str = "",
        profile: str = None
    ) -> ScanResult:
        """Run hydra with various authentication methods"""
        if profile and profile in self.profiles.get('hydra', {}):
            options = self.profiles['hydra'][profile]
        
        cmd = ["hydra"]
        if userlist:
            cmd.extend(["-L", userlist])
        if passlist:
            cmd.extend(["-P", passlist])
        cmd.extend(shlex.split(options))
        cmd.append(f"{service}://{target}")
        
        return await self._execute_command(cmd)

    # Metasploit integration
    async def run_msf(self, resource_file: str) -> ScanResult:
        """Execute Metasploit resource script"""
        cmd = ["msfconsole", "-q", "-r", resource_file]
        return await self._execute_command(cmd)

    # Network scanning tools
    async def scan_network(self, network: str, concurrent: int = 10) -> List[ScanResult]:
        """Parallel network scanning"""
        hosts = [str(host) for host in ip_network(network).hosts()]
        semaphore = asyncio.Semaphore(concurrent)
        
        async def scan_host(host: str):
            async with semaphore:
                return await self.run_nmap(host, "-sS -Pn")
        
        return await asyncio.gather(*[scan_host(host) for host in hosts])

    # Vulnerability scanning
    async def run_nikto(self, target: str, options: str = "") -> ScanResult:
        """Run Nikto web scanner"""
        cmd = ["nikto", "-h", target] + shlex.split(options)
        return await self._execute_command(cmd)

    async def run_sqlmap(self, url: str, options: str = "") -> ScanResult:
        """Run SQLMap for SQL injection testing"""
        cmd = ["sqlmap", "-u", url] + shlex.split(options)
        return await self._execute_command(cmd)

    # Wireless tools
    async def run_aircrack(self, pcap_file: str, wordlist: str) -> ScanResult:
        """Run aircrack-ng for WPA cracking"""
        cmd = ["aircrack-ng", pcap_file, "-w", wordlist]
        return await self._execute_command(cmd)

    # Password cracking
    async def run_john(self, hash_file: str, options: str = "") -> ScanResult:
        """Run John the Ripper password cracker"""
        cmd = ["john", hash_file] + shlex.split(options)
        return await self._execute_command(cmd)

    # Utility methods
    def get_scan_history(self, limit: int = 10, filter_success: bool = None) -> List[ScanResult]:
        """Get scan history with filtering"""
        results = self.scan_history.copy()
        if filter_success is not None:
            results = [r for r in results if r.success == filter_success]
        return sorted(results, key=lambda x: x.timestamp, reverse=True)[:limit]

    def save_history(self, file_path: str = "scan_history.json"):
        """Save scan history to JSON file"""
        with open(file_path, 'w') as f:
            json.dump([r.__dict__ for r in self.scan_history], f)

    def load_history(self, file_path: str = "scan_history.json"):
        """Load scan history from JSON file"""
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.scan_history = [ScanResult(**r) for r in data]

    def load_profiles(self, file_path: str = "profiles.json"):
        """Load tool profiles from JSON file"""
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                self.profiles = json.load(f)

    def save_profiles(self, file_path: str = "profiles.json"):
        """Save tool profiles to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.profiles, f)

    def create_profile(self, tool: str, name: str, options: str):
        """Create new tool profile"""
        if tool not in self.profiles:
            self.profiles[tool] = {}
        self.profiles[tool][name] = options
        self.save_profiles()

    async def cancel_scan(self, scan_id: str):
        """Cancel running scan"""
        if scan_id in self.active_scans:
            self.active_scans[scan_id].cancel()
            del self.active_scans[scan_id]

    # Reporting
    def generate_report(self, format: str = "text") -> Union[str, Dict]:
        """Generate scan report in specified format"""
        if format == "json":
            return [r.__dict__ for r in self.scan_history]
        else:
            report = []
            for result in self.scan_history:
                report.append(
                    f"[{datetime.fromtimestamp(result.timestamp)}] "
                    f"{'SUCCESS' if result.success else 'FAILURE'} "
                    f"Target: {result.target}\n"
                    f"Command: {result.command}\n"
                    f"Duration: {result.duration:.2f}s\n"
                    f"Output:\n{result.output}\n"
                    f"{'-'*50}"
                )
            return "\n".join(report)

    # Background scanning
    async def start_background_scan(self, scan_type: str, *args, **kwargs):
        """Start scan in background"""
        scan_id = f"{scan_type}_{datetime.now().timestamp()}"
        task = asyncio.create_task(self._run_scan(scan_type, *args, **kwargs))
        self.active_scans[scan_id] = task
        return scan_id

    async def _run_scan(self, scan_type: str, *args, **kwargs):
        """Internal method for background scans"""
        scan_method = getattr(self, f"run_{scan_type}", None)
        if scan_method:
            return await scan_method(*args, **kwargs)
        raise ValueError(f"Unknown scan type: {scan_type}")