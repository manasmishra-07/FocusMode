import re
from pathlib import PureWindowsPath

PROTECTED = frozenset(
    [
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "brave.exe",
        "opera.exe",
        "vivaldi.exe",
        "arc.exe",
        "browser.exe",
        "python.exe",
        "pythonw.exe",
        "focusmode.exe",
        "explorer.exe",
        "dwm.exe",
        "winlogon.exe",
        "csrss.exe",
        "services.exe",
        "lsass.exe",
        "svchost.exe",
        "sihost.exe",
        "taskmgr.exe",
        "applicationframehost.exe",
        "shellexperiencehost.exe",
        "startmenuexperiencehost.exe",
        "searchhost.exe",
        "securityhealthsystray.exe",
        "msmpeng.exe",
        "codex.exe",
    ]
)


def validate_apps(apps):
    if (
        not isinstance(apps, list)
        or len(apps) > 50
        or any(
            not isinstance(a, str)
            or not re.fullmatch(r"[\w .-]{1,80}\.exe", a, re.ASCII)
            for a in apps
        )
    ):
        raise ValueError("Allow-list must contain executable names such as Code.exe")
    return sorted(set(a.lower() for a in apps))


def protected(path, apps):
    name = PureWindowsPath(path).name.lower()
    # Conservatively preserve all executables under the Windows directory.
    import os

    windows = os.environ.get("WINDIR", "C:\\Windows").lower().rstrip("\\") + "\\"
    return name in PROTECTED or name in apps or path.lower().startswith(windows)
