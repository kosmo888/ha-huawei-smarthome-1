"""User-contributed protocol for Huawei product 2BMO (华为智选 海雀智能门铃Pro).

设备型号: DB001 (prodId: 2BMO, deviceTypeId: 099)
制造商: 海雀 (HQ)
Profile: https://smarthome-drcn.dbankcdn.com/device/guide/2BMO/2BMO.json

本适配器暴露:
   1. binary_sensor  门铃按键 (ringDoorBell, device_class: sound)
   2. binary_sensor  人形移动侦测 (humanBodyAlarm, device_class: motion)
   3. binary_sensor  低电量提醒 (lowPower, device_class: battery)
   4. binary_sensor  在线状态 (doorBellState, device_class: connectivity)
   5. binary_sensor  通话状态 (calling)
   6. binary_sensor  防拆告警 (deviceRemoved.removed, device_class: tamper)
   7. binary_sensor  陌生人脸告警 (strangerFace.matched)
   8. sensor         故障诊断 (faultCode.code)
   9. sensor         Wi-Fi信号强度 (netInfo.intensity, %)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext


# ---- 工具函数 ------------------------------------------------------------

def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        try:
            return int(round(float(value.strip())))
        except (TypeError, ValueError):
            return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.casefold() in {"1", "true", "on"}:
            return True
        if value.casefold() in {"0", "false", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


# ---- 适配器类 ------------------------------------------------------------

class Product2BMOAdapter:
    """华为智选 海雀智能门铃Pro (2BMO) 适配器。"""

    prod_id = "2BMO"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        if context.profile is None:
            return ()

        specs: list[EntitySpec] = []

        # 1. 门铃核心事件与传感器 (doorBell 服务)
        if context.has_service("doorBell"):
            # 门铃被按下
            def ring_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("doorBell", "ringDoorBell")) is True}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="ring",
                    name="门铃按键",
                    state=ring_state,
                    metadata={"device_class": "sound", "icon": "mdi:bell-ring"},
                )
            )

            # 人形侦测 (0:无, 1:匹配到人形, 2:持续匹配)
            def motion_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("doorBell", "humanBodyAlarm"))
                return {"is_on": val is not None and val > 0}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="motion",
                    name="人形移动侦测",
                    state=motion_state,
                    metadata={"device_class": "motion"},
                )
            )

            # 低电量提示 (0:电量充足, 1:低电)
            def low_batt_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("doorBell", "lowPower")) is True}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="low_battery",
                    name="低电量提醒",
                    state=low_batt_state,
                    metadata={"device_class": "battery"},
                )
            )

            # 在线/休眠状态 (0:休眠, 1:在线)
            def online_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("doorBell", "doorBellState")) is True}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="online",
                    name="在线状态",
                    state=online_state,
                    metadata={"device_class": "connectivity"},
                )
            )

        # 2. 门铃通话状态 (call 服务)
        if context.has_service("call"):
            def calling_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("call", "calling")) is True}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="calling",
                    name="通话状态",
                    state=calling_state,
                    metadata={"icon": "mdi:phone-in-talk"},
                )
            )

        # 3. 防拆告警 (deviceRemoved 服务)
        if context.has_service("deviceRemoved"):
            def tamper_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("deviceRemoved", "removed")) is True}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="tamper",
                    name="防拆告警",
                    state=tamper_state,
                    metadata={"device_class": "tamper"},
                )
            )

        # 4. 陌生人脸侦测 (strangerFace 服务)
        if context.has_service("strangerFace"):
            def stranger_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("strangerFace", "matched"))
                return {"is_on": val is not None and val > 0}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="stranger_face",
                    name="陌生人脸侦测",
                    state=stranger_state,
                    metadata={"icon": "mdi:account-alert"},
                )
            )

        # 5. 故障诊断 (faultCode 服务)
        if context.has_service("faultCode"):
            def fault_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("faultCode", "code"))
                return {"native_value": "低电故障" if val == 1 else "正常"}

            specs.append(
                EntitySpec(
                    platform="sensor",
                    key="fault",
                    name="故障诊断",
                    state=fault_state,
                    metadata={"icon": "mdi:alert-circle"},
                )
            )

        # 6. Wi-Fi 信号 (netInfo 服务)
        if context.has_service("netInfo"):
            def wifi_state(device: DeviceContext) -> Mapping[str, Any]:
                intensity = _as_int(device.value("netInfo", "intensity"))
                return {"native_value": intensity if intensity is not None and 0 <= intensity <= 100 else None}

            specs.append(
                EntitySpec(
                    platform="sensor",
                    key="wifi_signal",
                    name="Wi-Fi信号强度",
                    state=wifi_state,
                    metadata={
                        "unit": "%",
                        "state_class": "measurement",
                        "icon": "mdi:wifi",
                    },
                )
            )

        return tuple(specs)


ADAPTER = Product2BMOAdapter()
