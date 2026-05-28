"""Shared builders for status response payloads."""
from typing import Dict, Any

DEFAULT_ISSUE_LINK = "Refer to status page as no specific link is available"


def build_status_payload(
    name: str,
    status: str,
    status_url: str,
    issue_link: str = DEFAULT_ISSUE_LINK,
) -> Dict[str, Any]:
    """Build a normalized status payload dictionary."""
    return {
        "name": name,
        "status": status,
        "status_url": status_url,
        "issue_link": issue_link,
    }


def build_operational_payload(
    name: str,
    is_operational: bool,
    status_url: str,
    issue_link: str = DEFAULT_ISSUE_LINK,
) -> Dict[str, Any]:
    """Build payload from an operational/disrupted boolean outcome."""
    return build_status_payload(
        name=name,
        status="Operational" if is_operational else "Disrupted",
        status_url=status_url,
        issue_link=issue_link,
    )


def build_unknown_payload(name: str, status_url: str) -> Dict[str, Any]:
    """Build payload for unknown status results."""
    return build_status_payload(name=name, status="Unknown", status_url=status_url)
