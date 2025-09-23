#!/usr/bin/env python3
"""
Ping monitoring tool with RTT, Jitter, and Packet Loss statistics
Usage: python ping_monitor.py [--verbose]
Environment variables:
- TARGET_HOST: Target IP address or hostname (required)
- PING_INTERVAL: Ping interval in milliseconds (default: 100)
"""

import os
import socket
import subprocess
import time
import statistics
from collections import deque
from dataclasses import dataclass
from typing import Optional, List
import signal
import sys
import argparse


@dataclass
class PingResult:
    timestamp: float
    rtt: Optional[float]  # RTT in milliseconds, None if packet lost
    success: bool


class PingStatistics:
    def __init__(self):
        self.results = deque()
        self.running = True

    def add_result(self, result: PingResult):
        self.results.append(result)

        # Keep only last 5 minutes of data
        cutoff_time = time.time() - 300
        while self.results and self.results[0].timestamp < cutoff_time:
            self.results.popleft()

    def get_stats_for_window(self, window_seconds: int) -> dict:
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        window_results = [r for r in self.results if r.timestamp >= cutoff_time]

        if not window_results:
            return {
                'rtt_avg': None,
                'rtt_min': None,
                'rtt_max': None,
                'jitter': None,
                'packet_loss': None,
                'total_packets': 0
            }

        successful_results = [r for r in window_results if r.success and r.rtt is not None]
        total_packets = len(window_results)
        lost_packets = total_packets - len(successful_results)

        if not successful_results:
            return {
                'rtt_avg': None,
                'rtt_min': None,
                'rtt_max': None,
                'jitter': None,
                'packet_loss': 100.0,
                'total_packets': total_packets
            }

        rtts = [r.rtt for r in successful_results]
        rtt_avg = statistics.mean(rtts)
        rtt_min = min(rtts)
        rtt_max = max(rtts)

        # Calculate jitter (standard deviation of RTT)
        jitter = statistics.stdev(rtts) if len(rtts) > 1 else 0.0

        packet_loss = (lost_packets / total_packets) * 100.0

        return {
            'rtt_avg': rtt_avg,
            'rtt_min': rtt_min,
            'rtt_max': rtt_max,
            'jitter': jitter,
            'packet_loss': packet_loss,
            'total_packets': total_packets
        }


class PingMonitor:
    def __init__(self, target_host: str, interval_ms: int = 100, verbose: bool = False):
        self.target_host = target_host
        self.interval_seconds = interval_ms / 1000.0
        self.resolved_ip = self.resolve_hostname(target_host)
        self.stats = PingStatistics()
        self.verbose = verbose

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def resolve_hostname(self, hostname: str) -> str:
        """Resolve hostname to IP address"""
        try:
            ip = socket.gethostbyname(hostname)
            print(f"Resolved {hostname} to {ip}")
            return ip
        except socket.gaierror:
            # If resolution fails, assume it's already an IP address
            print(f"Using {hostname} as IP address")
            return hostname

    def signal_handler(self, _signum, _frame):
        """Handle shutdown signals gracefully"""
        print("\nShutting down ping monitor...")
        self.stats.running = False
        sys.exit(0)

    def ping_once(self) -> PingResult:
        """Execute a single ping and return the result"""
        timestamp = time.time()

        try:
            # Use subprocess to execute ping command
            # -c 1: send only 1 packet
            # -W 1000: timeout of 1 second (1000ms)
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1000', self.resolved_ip],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                # Parse RTT from ping output
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'time=' in line:
                        # Extract RTT value
                        time_part = line.split('time=')[1].split()[0]
                        rtt = float(time_part)
                        ping_result = PingResult(timestamp=timestamp, rtt=rtt, success=True)

                        # Display individual packet response in verbose mode
                        if self.verbose:
                            self.display_packet_response(ping_result, line.strip())

                        return ping_result

                # If we can't parse RTT but ping succeeded
                ping_result = PingResult(timestamp=timestamp, rtt=None, success=True)
                if self.verbose:
                    self.display_packet_response(ping_result, "Ping succeeded but RTT could not be parsed")
                return ping_result
            else:
                # Ping failed
                ping_result = PingResult(timestamp=timestamp, rtt=None, success=False)
                if self.verbose:
                    self.display_packet_response(ping_result, f"Ping failed (exit code: {result.returncode})")
                return ping_result

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
            ping_result = PingResult(timestamp=timestamp, rtt=None, success=False)
            if self.verbose:
                self.display_packet_response(ping_result, f"Ping error: {str(e)}")
            return ping_result

    def display_packet_response(self, result: PingResult, detail: str):
        """Display individual packet response in verbose mode"""
        timestamp_str = time.strftime('%H:%M:%S', time.localtime(result.timestamp))
        status = "✓" if result.success else "✗"

        if result.success and result.rtt is not None:
            print(f"[{timestamp_str}] {status} {self.resolved_ip}: {result.rtt:6.2f}ms - {detail}")
        else:
            print(f"[{timestamp_str}] {status} {self.resolved_ip}: FAILED - {detail}")

    def format_stats(self, stats: dict, window_name: str) -> str:
        """Format statistics for display"""
        if stats['total_packets'] == 0:
            return f"{window_name:>8}: No data"

        if stats['rtt_avg'] is None:
            return f"{window_name:>8}: {stats['packet_loss']:5.1f}% loss ({stats['total_packets']} packets)"

        return (f"{window_name:>8}: "
                f"RTT avg={stats['rtt_avg']:6.2f}ms "
                f"min={stats['rtt_min']:6.2f}ms "
                f"max={stats['rtt_max']:6.2f}ms "
                f"jitter={stats['jitter']:6.2f}ms "
                f"loss={stats['packet_loss']:5.1f}% "
                f"({stats['total_packets']} packets)")

    def display_status(self):
        """Display current statistics"""
        if not self.verbose:
            # Clear screen and move cursor to top only in non-verbose mode
            print("\033[2J\033[H", end="")

        print(f"Ping Monitor - Target: {self.target_host} ({self.resolved_ip})")
        print(f"Interval: {self.interval_seconds*1000:.0f}ms")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.verbose:
            print("Verbose mode: ON")
        print("-" * 80)

        # Get statistics for different time windows
        stats_10s = self.stats.get_stats_for_window(10)
        stats_1m = self.stats.get_stats_for_window(60)
        stats_5m = self.stats.get_stats_for_window(300)

        print(self.format_stats(stats_10s, "10 sec"))
        print(self.format_stats(stats_1m, "1 min"))
        print(self.format_stats(stats_5m, "5 min"))

        print("-" * 80)
        if not self.verbose:
            print("Press Ctrl+C to stop")
        else:
            print("Press Ctrl+C to stop | Packet responses shown below:")
            print()

    def run(self):
        """Main monitoring loop"""
        print(f"Starting ping monitor for {self.target_host} ({self.resolved_ip})")
        print(f"Ping interval: {self.interval_seconds*1000:.0f}ms")
        print("Collecting initial data...")

        last_display_time = 0
        display_interval = 1.0  # Update display every second

        while self.stats.running:
            # Execute ping
            result = self.ping_once()
            self.stats.add_result(result)

            # Update display if enough time has passed
            current_time = time.time()
            if current_time - last_display_time >= display_interval:
                self.display_status()
                last_display_time = current_time

            # Wait for next ping
            time.sleep(self.interval_seconds)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ping monitoring tool with RTT, Jitter, and Packet Loss statistics')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose mode to show individual packet responses')
    args = parser.parse_args()

    # Get configuration from environment variables
    target_host = os.environ.get('TARGET_HOST')
    if not target_host:
        print("Error: TARGET_HOST environment variable is required")
        print("Usage: TARGET_HOST=example.com python ping_monitor.py [--verbose]")
        sys.exit(1)

    interval_ms = int(os.environ.get('PING_INTERVAL', 100))

    # Create and run monitor
    monitor = PingMonitor(target_host, interval_ms, verbose=args.verbose)
    monitor.run()


if __name__ == "__main__":
    main()
