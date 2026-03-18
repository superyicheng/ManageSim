"""Security scanner — classify skills as clean, suspicious, or malicious.

Three tiers:
- clean: No security concerns, auto-installable
- suspicious: Potential issues, requires admin approval
- malicious: Blocked automatically
"""

import re
import json
from typing import Optional


# Patterns that indicate potential security issues
SUSPICIOUS_PATTERNS = [
    re.compile(r'eval\s*\(', re.IGNORECASE),
    re.compile(r'exec\s*\(', re.IGNORECASE),
    re.compile(r'subprocess', re.IGNORECASE),
    re.compile(r'os\.system', re.IGNORECASE),
    re.compile(r'requests\.post.*token', re.IGNORECASE),
    re.compile(r'base64\.decode', re.IGNORECASE),
    re.compile(r'__import__', re.IGNORECASE),
]

MALICIOUS_PATTERNS = [
    re.compile(r'rm\s+-rf\s+/', re.IGNORECASE),
    re.compile(r'curl.*\|\s*sh', re.IGNORECASE),
    re.compile(r'wget.*\|\s*bash', re.IGNORECASE),
    re.compile(r'chmod\s+777', re.IGNORECASE),
    re.compile(r'reverse.shell', re.IGNORECASE),
    re.compile(r'keylog', re.IGNORECASE),
    re.compile(r'crypto.?min', re.IGNORECASE),
]


class SecurityScanner:
    def __init__(self):
        self.scan_history = []

    def scan(self, skill_data: dict) -> dict:
        """Scan a skill for security issues.

        Returns:
            dict with tier (clean/suspicious/malicious), issues list, and details
        """
        content = json.dumps(skill_data) if isinstance(skill_data, dict) else str(skill_data)
        description = skill_data.get("description", "") if isinstance(skill_data, dict) else ""

        issues = []

        # Check for malicious patterns
        for pattern in MALICIOUS_PATTERNS:
            if pattern.search(content):
                issues.append({
                    "severity": "malicious",
                    "pattern": pattern.pattern,
                    "message": f"Malicious pattern detected: {pattern.pattern}",
                })

        if any(i["severity"] == "malicious" for i in issues):
            result = {"tier": "malicious", "issues": issues}
            self.scan_history.append(result)
            return result

        # Check for suspicious patterns
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(content):
                issues.append({
                    "severity": "suspicious",
                    "pattern": pattern.pattern,
                    "message": f"Suspicious pattern: {pattern.pattern}",
                })

        if issues:
            result = {"tier": "suspicious", "issues": issues}
            self.scan_history.append(result)
            return result

        result = {"tier": "clean", "issues": []}
        self.scan_history.append(result)
        return result

    def get_scan_history(self) -> list:
        return list(self.scan_history)
