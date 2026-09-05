"""Diagnostic helpers for read-only cluster observations."""


def classify_ansible_failure(result):
    """
    Convert Ansible/SSH failure text into a stable machine-readable reason.
    """
    if result.get("timed_out") is True:
        return "timeout"

    text = (
        f"{result.get('stdout', '')}\n"
        f"{result.get('stderr', '')}"
    ).lower()

    if (
        "no inventory was parsed" in text
        or "could not match supplied host pattern" in text
    ):
        return "inventory_error"

    if any(
        marker in text
        for marker in (
            "permission denied",
            "publickey",
            "authentication failed",
            "failed to authenticate",
            "invalid/incorrect password",
        )
    ):
        return "ssh_auth_failed"

    if any(
        marker in text
        for marker in (
            "connection timed out",
            "timed out",
            "no route to host",
            "network is unreachable",
            "connection refused",
            "host unreachable",
        )
    ):
        return "host_unreachable"

    if result.get("rc", 0) != 0:
        return "ansible_error"

    return "unknown"


def short_error_detail(result, limit=240):
    """
    Keep a short diagnostic without dumping huge command output.
    """
    text = (
        result.get("stderr", "").strip()
        or result.get("stdout", "").strip()
    )

    text = " ".join(text.split())

    if len(text) > limit:
        return text[:limit] + "..."

    return text or None
