# device_utils.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import sys
import re
import platform
import subprocess
import plistlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PurePath
from typing import Dict, List, Optional, Tuple

import hashlib
import magic

@dataclass
class DeviceMount:
    uuid: str                 # 规范化后的统一 UUID
    mount_path: str
    device: Optional[str]
    fs_type: Optional[str]
    label: Optional[str]
    is_external: Optional[bool]
    partition_uuid: Optional[str] = None # new uuid, more stable

# =========================
# 统一 UUID 规范化
# =========================
_UUID_HEX_RE = re.compile(r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}")

def normalize_uuid(value: Optional[str], fs_type: Optional[str] = None, os_name: Optional[str] = None) -> Optional[str]:
    """
    将各平台得到的“卷标识/文件系统UUID/唯一ID/SerialNumber”等规范为统一的 UUID 字符串（大写）。
    规则：
    - 去除花括号/前后缀（如 {GUID}, Volume{GUID}, \\?\Volume{GUID}\）
    - Windows 若给到 UniqueId 为路径形式，抽取中间的 GUID
    - 常见的 SerialNumber（纯十六进制/十进制）无法转GUID时，保留原值（大写）
    - ext/ntfs/exfat/hfs/apfs 的 Volume UUID 直接转大写
    """
    if not value:
        return None

    v = str(value).strip()

    # 去掉常见前后缀
    v = v.replace("UUID:", "").replace("Volume UUID:", "").strip()
    v = v.strip("\\")  # 去尾部反斜杠
    v = v.strip()      # 再次清理空格

    # Windows: \\?\Volume{GUID}\ 或 DeviceHarddiskVolumeX
    # 形如：\\?\Volume{12345678-1234-1234-1234-1234567890AB}\
    m = re.search(r"\{([0-9a-fA-F\-]{36})\}", v)
    if m:
        v = m.group(1)

    # 去掉 "Volume" 前缀，如 Volume{GUID} → GUID
    m = re.search(r"Volume\{([0-9a-fA-F\-]{36})\}", v, re.IGNORECASE)
    if m:
        v = m.group(1)

    # 去掉花括号
    v = v.strip("{}")

    # 若已经是 GUID 形态，统一格式化为大写 8-4-4-4-12
    m = _UUID_HEX_RE.fullmatch(v) or _UUID_HEX_RE.search(v)
    if m:
        g = m.group(0).replace("-", "")
        # 规范化带连字符并大写
        v = f"{g[0:8]}-{g[8:12]}-{g[12:16]}-{g[16:20]}-{g[20:32]}".upper()
        return v

    # 部分文件系统给的是短序列号（如 FAT/NTFS SerialNumber：XXXX-XXXX）
    # 统一大写存储；跨平台一致性不如 GUID，但至少稳定
    return v.upper()

# =========================
# 公共 API
# =========================

def get_mounted_devices() -> Dict[str, str]:
    """返回 {uuid: mount_path}（uuid 已规范化）"""
    return {d.uuid: d.mount_path for d in list_mounted_devices() if d.uuid and d.mount_path}

def list_mounted_devices() -> List[DeviceMount]:
    system = platform.system()
    try:
        if system == "Darwin":
            return _list_macos()
        elif system == "Linux":
            return _list_linux()
        elif system == "Windows":
            return _list_windows()
        else:
            return []
    except Exception as e:
        print(f"[device_utils] 列举设备失败: {e}", file=sys.stderr)
        return []

def resolve_full_path(device_uuid: str, relative_path: str, mounts: Optional[Dict[str, str]] = None) -> str:
    if mounts is None:
        mounts = get_mounted_devices()
    base = mounts.get(device_uuid) or mounts.get(normalize_uuid(device_uuid))
    if not base:
        raise FileNotFoundError(f"未找到设备 {device_uuid} 的挂载点，请确认设备已连接。")
    return str(Path(base) / Path(relative_path))

def match_path_to_device(abs_path: str, mounts: Optional[Dict[str, str]] = None) -> Optional[Tuple[str, str]]:
    abs_path = str(Path(abs_path).resolve())
    if mounts is None:
        mounts = get_mounted_devices()
    best = None
    best_len = -1
    for uuid, mnt in mounts.items():
        try:
            mnorm = str(Path(mnt).resolve())
        except Exception:
            mnorm = mnt
        if _is_prefix_of(mnorm, abs_path) and len(mnorm) > best_len:
            best = (uuid, mnorm)
            best_len = len(mnorm)
    if not best:
        return None
    uuid, mount_path = best
    rel = os.path.relpath(abs_path, mount_path)
    return uuid, normalize_relative_path(rel)

def normalize_relative_path(p: str) -> str:
    posix = PurePosixPath(*PurePath(p).parts)
    return posix.as_posix()

# =========================
# macOS
# =========================

def _list_macos() -> List[DeviceMount]:
    devices: List[DeviceMount] = []
    info_all = subprocess.run(
        ["diskutil", "info", "-all", "-plist"],
        capture_output=True, check=False
    )
    if info_all.returncode == 0 and info_all.stdout:
        try:
            pl = plistlib.loads(info_all.stdout)
        except Exception:
            pl = None
        if isinstance(pl, list):
            for e in pl:
                _append_macos_entry(devices, e)
            return _dedup_by_uuid_choose_mounted(devices)
    # 回退文本解析
    return _list_macos_text()

def _append_macos_entry(devices: List[DeviceMount], e: dict) -> None:
    def first(keys: List[str]) -> Optional[str]:
        for k in keys:
            v = e.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    uuid_raw = first(["VolumeUUID", "VolumeUUIDString"])
    part_uuid_raw = first(["PartitionUUID"])
    mount_point = first(["MountPoint"])
    device_node = first(["DeviceNode"])
    fs = first(["FilesystemName", "FileSystemType", "Type (Bundle)"])
    label = first(["VolumeName", "MediaName"])
    # 规范化 UUID
    uuid = normalize_uuid(uuid_raw, fs_type=fs, os_name="Darwin")
    part_uuid = normalize_uuid(part_uuid_raw, os_name="Darwin") if part_uuid_raw else None # new stable uuid

    if uuid and mount_point:
        devices.append(DeviceMount(
            uuid=uuid, mount_path=mount_point, device=device_node,
            fs_type=fs, label=label, is_external=None,
            partition_uuid=part_uuid  # new stable uuid
        ))

def _list_macos_text() -> List[DeviceMount]:
    out = subprocess.run(["diskutil", "info", "-all"], capture_output=True, text=True, check=False)
    if out.returncode != 0:
        return []
    devices: List[DeviceMount] = []
    uuid = mount = device = fs = label = None
    for line in out.stdout.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("Device Node:"):
            device = s.split(":", 1)[1].strip()
        elif s.startswith("Volume Name:"):
            label = s.split(":", 1)[1].strip() or None
        elif s.startswith("Mount Point:"):
            mount = s.split(":", 1)[1].strip() or None
        elif s.startswith("File System:"):
            fs = s.split(":", 1)[1].strip() or None
        elif s.startswith("Volume UUID:"):
            raw = s.split(":", 1)[1].strip() or None
            uuid = normalize_uuid(raw, fs_type=fs, os_name="Darwin")
        if uuid and mount:
            devices.append(DeviceMount(
                uuid=uuid, mount_path=mount, device=device, fs_type=fs, label=label, is_external=None
            ))
            uuid = mount = device = fs = label = None
    return _dedup_by_uuid_choose_mounted(devices)

# =========================
# Linux
# =========================

def _list_linux() -> List[DeviceMount]:
    uuid_to_dev = {}
    partuuid_map = {}

    # 对所有设备
    proc = subprocess.run(["blkid", "-o", "export"], capture_output=True, text=True, check=False)

    if proc.returncode == 0:
        cur_dev = None
        for line in proc.stdout.splitlines():
            if not line:
                continue
            if 'DEVNAME=' in line:  # 设备行，如 /dev/nvme0n1p2
                cur_dev = os.path.realpath(line.strip().removeprefix("DEVNAME="))
                continue
            key, val = line.split("=", 1)
            if key == "UUID":
                uuid_to_dev[val] = cur_dev
            elif key == "PARTUUID":
                partuuid_map[cur_dev] = val

        # 调试看看
        print(f'\n\nuuid_to_dev: {uuid_to_dev}')
        print(f'\n\npartuuid_map: {partuuid_map}')

    # 读取挂载信息
    dev_to_mount: Dict[str, Tuple[str, str]] = {}
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3:
                    dev, mnt, fs = parts[0], parts[1], parts[2]
                    dev_to_mount[os.path.realpath(dev)] = (mnt, fs)
    except Exception:
        pass
    # print(f'dev_to_mount: {dev_to_mount}')

    # 生成 DeviceMount
    devices: List[DeviceMount] = []
    for fs_uuid, dev in uuid_to_dev.items():
        m = dev_to_mount.get(os.path.realpath(dev))
        if not m:
            continue
        mount_path, fs = m
        if _looks_like_system_mount(mount_path):
            continue
        print(f'dev: {dev}')
        devices.append(DeviceMount(
            uuid=fs_uuid,
            mount_path=mount_path,
            device=dev,
            fs_type=fs,
            label=None,
            is_external=None,
            partition_uuid=partuuid_map.get(dev)  # 用 PARTUUID
        ))

    # return _dedup_by_uuid_choose_mounted(devices)
    return devices

# =========================
# Windows
# =========================

def _list_windows() -> List[DeviceMount]:
    devices: List[DeviceMount] = []

    ps_cmd = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-Command",
        "(Get-Volume | Select-Object DriveLetter, FileSystemLabel, FileSystem, UniqueId, Path | ConvertTo-Json)"
    ]
    try:
        res = subprocess.run(ps_cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and res.stdout.strip():
            import json
            data = json.loads(res.stdout)
            rows = data if isinstance(data, list) else [data]
            for r in rows:
                drive = r.get("DriveLetter")
                mount_path = (r.get("Path") or (f"{drive}:\\" if drive else None))
                if not mount_path:
                    continue
                fs = r.get("FileSystem")
                label = r.get("FileSystemLabel")
                uid_raw = r.get("UniqueId") or r.get("Path") or r.get("DriveLetter")
                uuid = normalize_uuid(uid_raw, fs_type=fs, os_name="Windows")
                part_uuid = normalize_uuid(uid_raw, os_name="Windows") if uid_raw else None  # new stable uuid

                if uuid and os.path.exists(mount_path):
                    devices.append(DeviceMount(
                        uuid=uuid, mount_path=mount_path, device=mount_path,
                        fs_type=fs, label=label, is_external=None,
                        partition_uuid=part_uuid # new stable uuid
                    ))
    except Exception:
        pass

    if not devices:
        try:
            res = subprocess.run(
                ["wmic", "volume", "get", "DriveLetter,Label,FileSystem,SerialNumber", "/format:list"],
                capture_output=True, text=True, check=False
            )
            if res.returncode == 0:
                block = {}
                for line in res.stdout.splitlines():
                    s = line.strip()
                    if not s:
                        drive = block.get("DriveLetter")
                        serial = block.get("SerialNumber")
                        if drive and serial:
                            mount_path = f"{drive}:\\"
                            uuid = normalize_uuid(serial, fs_type=block.get("FileSystem"), os_name="Windows")
                            if uuid and os.path.exists(mount_path):
                                devices.append(DeviceMount(
                                    uuid=uuid, mount_path=mount_path, device=mount_path,
                                    fs_type=block.get("FileSystem"), label=block.get("Label"), is_external=None
                                ))
                        block = {}
                        continue
                    if "=" in s:
                        k, v = s.split("=", 1)
                        block[k] = v
                drive = block.get("DriveLetter")
                serial = block.get("SerialNumber")
                if drive and serial:
                    mount_path = f"{drive}:\\"
                    uuid = normalize_uuid(serial, fs_type=block.get("FileSystem"), os_name="Windows")
                    part_uuid = normalize_uuid(serial, os_name="Windows") if serial else None # new stable uuid
                    
                    if uuid and os.path.exists(mount_path):
                        devices.append(DeviceMount(
                            uuid=uuid, mount_path=mount_path, device=mount_path,
                            fs_type=block.get("FileSystem"), label=block.get("Label"), is_external=None,
                            partition_uuid=part_uuid # new stable uuid
                        ))
        except Exception:
            pass

    uniq: Dict[str, DeviceMount] = {}
    for d in devices:
        key = (d.uuid, d.mount_path.upper())
        if key not in uniq:
            uniq[key] = d
    return list(uniq.values())

# =========================
# Helpers
# =========================

def _is_prefix_of(prefix: str, path: str) -> bool:
    if platform.system() == "Windows":
        prefix = os.path.normcase(prefix)
        path = os.path.normcase(path)
    try:
        p_prefix = str(Path(prefix).resolve())
        p_path = str(Path(path).resolve())
    except Exception:
        p_prefix = os.path.normpath(prefix)
        p_path = os.path.normpath(path)
    if not p_path.startswith(p_prefix):
        return False
    if len(p_path) == len(p_prefix):
        return True
    sep = os.sep
    return p_path[len(p_prefix)] in (sep, "/","\\")

def _looks_like_system_mount(mnt: str) -> bool:
    SKIP_PREFIX = (
        "/", "/proc", "/sys", "/dev", "/run", "/boot",
        "/snap", "/var", "/usr", "/etc", "/lib", "/lib64",
    )
    allow_prefix = ("/media", "/mnt", "/run/media")
    mnt = os.path.normpath(mnt)
    if mnt.startswith(allow_prefix):
        return False
    return any(mnt == p or mnt.startswith(p + os.sep) for p in SKIP_PREFIX)

def _dedup_by_uuid_choose_mounted(devs: List[DeviceMount]) -> List[DeviceMount]:
    by_uuid: Dict[str, DeviceMount] = {}
    for d in devs:
        if not d.uuid:
            continue
        prev = by_uuid.get(d.uuid)
        if not prev:
            by_uuid[d.uuid] = d
            continue
        if d.mount_path and not prev.mount_path:
            by_uuid[d.uuid] = d
    return list(by_uuid.values())

# === 工具函数 ===
def calculate_md5(filepath, block_size=65536):
    md5 = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None

def get_mime_type(filepath):
    try:
        return magic.from_file(filepath, mime=True)
    except Exception:
        return 'application/octet-stream'
    
# =========================
# 自测
# =========================
if __name__ == "__main__":
    print("== get_mounted_devices() ==")
    for k, v in get_mounted_devices().items():
        print(k, "=>", v)
