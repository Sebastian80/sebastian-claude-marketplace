#!/usr/bin/env python3
"""
Benchmark: CLI scripts vs HTTP daemon performance.

Compares latency of Jira operations between:
1. Traditional CLI (spawns new Python process per command)
2. HTTP daemon (persistent connection via skills-daemon)

Usage:
    python benchmark.py [--issue ISSUE_KEY] [--iterations N]
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request
import urllib.error

# Configuration
DAEMON_URL = "http://127.0.0.1:9100"
DEFAULT_ISSUE = "OPSDHL-2851"  # Test issue
DEFAULT_ITERATIONS = 10


def check_daemon_running() -> bool:
    """Check if skills-daemon is running."""
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def check_jira_plugin_loaded() -> bool:
    """Check if Jira plugin is loaded in daemon."""
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/plugins")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            plugins = data.get("plugins", [])
            return any(p.get("name") == "jira" for p in plugins)
    except Exception:
        return False


def benchmark_cli_issue_get(issue_key: str, iterations: int) -> list[float]:
    """Benchmark CLI: jira issue get."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(
            ["jira", "issue", "--json", "get", issue_key],
            capture_output=True,
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        if result.returncode != 0:
            print(f"  CLI error: {result.stderr.decode()[:100]}", file=sys.stderr)
    return times


def benchmark_http_issue_get(issue_key: str, iterations: int) -> list[float]:
    """Benchmark HTTP daemon: GET /jira/issue/{key}."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            req = urllib.request.Request(f"{DAEMON_URL}/jira/issue/{issue_key}")
            with urllib.request.urlopen(req, timeout=30) as resp:
                _ = resp.read()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        except Exception as e:
            print(f"  HTTP error: {e}", file=sys.stderr)
            times.append(float('inf'))
    return times


def benchmark_cli_search(iterations: int) -> list[float]:
    """Benchmark CLI: jira search query."""
    times = []
    jql = "project = OPSDHL ORDER BY created DESC"
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(
            ["jira", "search", "--json", "query", jql, "-n", "5"],
            capture_output=True,
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        if result.returncode != 0:
            print(f"  CLI error: {result.stderr.decode()[:100]}", file=sys.stderr)
    return times


def benchmark_http_search(iterations: int) -> list[float]:
    """Benchmark HTTP daemon: GET /jira/search."""
    times = []
    jql = "project = OPSDHL ORDER BY created DESC"
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            url = f"{DAEMON_URL}/jira/search?jql={urllib.parse.quote(jql)}&maxResults=5"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                _ = resp.read()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        except Exception as e:
            print(f"  HTTP error: {e}", file=sys.stderr)
            times.append(float('inf'))
    return times


def benchmark_cli_transitions(issue_key: str, iterations: int) -> list[float]:
    """Benchmark CLI: jira transition list."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(
            ["jira", "transition", "--json", "list", issue_key],
            capture_output=True,
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        if result.returncode != 0:
            print(f"  CLI error: {result.stderr.decode()[:100]}", file=sys.stderr)
    return times


def benchmark_http_transitions(issue_key: str, iterations: int) -> list[float]:
    """Benchmark HTTP daemon: GET /jira/transitions/{key}."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            req = urllib.request.Request(f"{DAEMON_URL}/jira/transitions/{issue_key}")
            with urllib.request.urlopen(req, timeout=30) as resp:
                _ = resp.read()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        except Exception as e:
            print(f"  HTTP error: {e}", file=sys.stderr)
            times.append(float('inf'))
    return times


def format_stats(times: list[float]) -> str:
    """Format timing statistics."""
    valid = [t for t in times if t != float('inf')]
    if not valid:
        return "ERROR (all failed)"
    mean = statistics.mean(valid)
    stdev = statistics.stdev(valid) if len(valid) > 1 else 0
    return f"{mean:7.1f}ms (±{stdev:5.1f}ms)"


def print_comparison(name: str, cli_times: list[float], http_times: list[float]):
    """Print comparison between CLI and HTTP times."""
    cli_mean = statistics.mean([t for t in cli_times if t != float('inf')] or [0])
    http_mean = statistics.mean([t for t in http_times if t != float('inf')] or [0])

    speedup = cli_mean / http_mean if http_mean > 0 else 0

    print(f"\n{name}:")
    print(f"  CLI:  {format_stats(cli_times)}")
    print(f"  HTTP: {format_stats(http_times)}")
    print(f"  Speedup: {speedup:.1f}x")


def main():
    import urllib.parse

    parser = argparse.ArgumentParser(description="Benchmark CLI vs HTTP daemon")
    parser.add_argument("--issue", default=DEFAULT_ISSUE, help=f"Issue key (default: {DEFAULT_ISSUE})")
    parser.add_argument("--iterations", "-n", type=int, default=DEFAULT_ITERATIONS, help=f"Iterations (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--skip-cli", action="store_true", help="Skip CLI benchmarks")
    parser.add_argument("--skip-http", action="store_true", help="Skip HTTP benchmarks")
    args = parser.parse_args()

    print("=" * 60)
    print("JIRA BENCHMARK: CLI vs HTTP Daemon")
    print("=" * 60)
    print(f"Issue: {args.issue}")
    print(f"Iterations: {args.iterations}")

    # Check prerequisites
    print("\nChecking prerequisites...")

    if not args.skip_http:
        if not check_daemon_running():
            print("  ERROR: skills-daemon not running")
            print("  Run: skills-daemon start")
            sys.exit(1)
        print("  ✓ skills-daemon running")

        if not check_jira_plugin_loaded():
            print("  ERROR: Jira plugin not loaded")
            print("  Run: skills-daemon restart")
            sys.exit(1)
        print("  ✓ Jira plugin loaded")

    if not args.skip_cli:
        result = subprocess.run(["which", "jira"], capture_output=True)
        if result.returncode != 0:
            print("  ERROR: 'jira' CLI not found in PATH")
            sys.exit(1)
        print("  ✓ jira CLI available")

    # Warmup
    print("\nWarming up...")
    if not args.skip_cli:
        benchmark_cli_issue_get(args.issue, 1)
    if not args.skip_http:
        benchmark_http_issue_get(args.issue, 1)
    print("  Done")

    # Run benchmarks
    print(f"\nRunning {args.iterations} iterations each...")

    results = {}

    # Issue GET
    print("\n[1/3] Issue GET")
    cli_issue = benchmark_cli_issue_get(args.issue, args.iterations) if not args.skip_cli else []
    http_issue = benchmark_http_issue_get(args.issue, args.iterations) if not args.skip_http else []
    results['issue_get'] = {'cli': cli_issue, 'http': http_issue}

    # Search
    print("[2/3] Search (JQL)")
    cli_search = benchmark_cli_search(args.iterations) if not args.skip_cli else []
    http_search = benchmark_http_search(args.iterations) if not args.skip_http else []
    results['search'] = {'cli': cli_search, 'http': http_search}

    # Transitions
    print("[3/3] Transition List")
    cli_trans = benchmark_cli_transitions(args.issue, args.iterations) if not args.skip_cli else []
    http_trans = benchmark_http_transitions(args.issue, args.iterations) if not args.skip_http else []
    results['transitions'] = {'cli': cli_trans, 'http': http_trans}

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if not args.skip_cli and not args.skip_http:
        print_comparison("Issue GET", cli_issue, http_issue)
        print_comparison("Search (JQL)", cli_search, http_search)
        print_comparison("Transitions", cli_trans, http_trans)

        # Overall
        all_cli = cli_issue + cli_search + cli_trans
        all_http = http_issue + http_search + http_trans
        print_comparison("OVERALL", all_cli, all_http)
    else:
        if not args.skip_cli:
            print("\nCLI Results:")
            print(f"  Issue GET:   {format_stats(cli_issue)}")
            print(f"  Search:      {format_stats(cli_search)}")
            print(f"  Transitions: {format_stats(cli_trans)}")
        if not args.skip_http:
            print("\nHTTP Results:")
            print(f"  Issue GET:   {format_stats(http_issue)}")
            print(f"  Search:      {format_stats(http_search)}")
            print(f"  Transitions: {format_stats(http_trans)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
