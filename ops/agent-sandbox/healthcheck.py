#!/usr/bin/env python3
"""WP-057: Junie Agent Sandbox Healthcheck.

This script verifies that the agent sandbox container is running
in an isolated environment without access to host resources.
"""

import os
import sys
import socket


def check_no_docker_socket() -> bool:
    """Verify Docker socket is not accessible."""
    return not os.path.exists("/var/run/docker.sock")


def check_no_lxd_socket() -> bool:
    """Verify LXD socket is not accessible."""
    lxd_paths = ["/var/lib/lxd/unix.socket", "/var/lib/lxd/socket"]
    return not any(os.path.exists(p) for p in lxd_paths)


def check_no_user_home() -> bool:
    """Verify user's real home directory is not mounted."""
    return not os.path.exists("/home/fenatodev/.ssh")


def check_no_n8n_data() -> bool:
    """Verify n8n data directory is not mounted."""
    return not os.path.exists("/var/lib/n8n")


def check_no_ssh_agent() -> bool:
    """Verify SSH agent is not accessible."""
    ssh_sock = os.environ.get("SSH_AUTH_SOCK", "")
    if not ssh_sock:
        return True
    return not os.path.exists(ssh_sock)


def check_no_internal_network() -> bool:
    """Verify internal network access is blocked.

    This check is informational — it doesn't block access,
    it only reports whether the container can reach internal hosts.
    """
    # Try to reach localhost — should fail in --network none mode
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", 22))
        sock.close()
        # If we can connect to localhost, network is not fully isolated
        return result != 0
    except Exception:
        # Connection failed — good for isolation
        return True


def check_non_root_user() -> bool:
    """Verify the container is running as non-root."""
    return os.getuid() != 0


def check_read_only_filesystem() -> bool:
    """Verify the filesystem is mostly read-only.

    This check verifies that /etc is not writable, which is a
    good indicator of read-only filesystem.
    """
    try:
        test_file = "/etc/junie-healthcheck-test"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return False  # Writable — not read-only
    except (PermissionError, OSError):
        return True  # Not writable — read-only


def main() -> int:
    """Run all health checks."""
    checks = [
        ("Docker socket blocked", check_no_docker_socket),
        ("LXD socket blocked", check_no_lxd_socket),
        ("User home not mounted", check_no_user_home),
        ("n8n data not mounted", check_no_n8n_data),
        ("SSH agent not accessible", check_no_ssh_agent),
        ("Non-root user", check_non_root_user),
        ("Read-only filesystem", check_read_only_filesystem),
    ]

    failed = []
    for name, check in checks:
        try:
            if check():
                print(f"✓ {name}")
            else:
                print(f"✗ {name}")
                failed.append(name)
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed.append(name)

    # Network check is informational
    if check_no_internal_network():
        print("✓ Internal network blocked (informational)")
    else:
        print("⚠ Internal network accessible (informational)")

    if failed:
        print(f"\nFailed checks: {', '.join(failed)}")
        return 1

    print("\nAll health checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
