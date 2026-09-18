"""User-contributed protocol for Huawei product A3DG (美的 抽油烟机).

设备类型: 抽油烟机 (Range Hood), 型号 CXW-270-J25S (prodId: A3DG, deviceTypeId: 021)
制造商: 美的 (Midea)
Profile: https://smarthome-drcn.dbankcdn.com/device/guide/A3DG/A3DG.json

核心服务:
   switch.on                  bool RW (1=开, 0=关)   烟机电源总开关
   lightSwitch.on             bool RW (1=开灯, 0=关灯) 照明灯开关
   gear.gear                  enum RW (0=停转, 1=1档, 2=2档, 3=3档) 风速档位
   status.status              enum R  (1=关机, 2=运行中, 103=延时关机中, 104=蒸汽洗中, 105=故障中, 106=用户清洁中) 工作状态
   workBurnerStatus           enum R  (leftStatus, rightStatus: 0=已关火, 1=已开火) 左右灶具联动状态
   commonFaultDetection.status bool R (0=正常, 1=异常)
   netInfo.intensity          enum R  (Wi-Fi信号)

本适配器暴露:
   1. fan 实体: 抽油烟机风扇 (开关 / 3档转速映射 / 档位控制)
   2. light 实体: 烟机照明灯 (开关控制)
   3. sensor 实体: 运行状态 (关机/运行中/延时关机/清洁中等)
   4. binary_sensor 实体: 灶具火候联动 - 左灶 (关火 / 开火)
   5. binary_sensor 实体: 灶具火候联动 - 右灶 (关火 / 开火)
   6. binary_sensor 实体: 故障告警 (device_class: problem)
   7. sensor 实体: Wi-Fi信号强度 (%)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

_STATUS_TEXT = {
    1: "关机",
    2: "运行中",
    103: "延时关机中",
    104: "蒸汽洗中",
    105: "故障中",
    106: "用户清洁中",
}

# 档位映射 (1档=33%, 2档=66%, 3档=100%)
_GEAR_TO_PERCENT = {0: 0, 1: 33, 2: 66, 3: 100}


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


class ProductA3DGAdapter:
    """美的抽油烟机 (A3DG) 适配器。"""

    prod_id = "A3DG"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        if context.profile is None:
            return ()

        specs: list[EntitySpec] = []

        # 1. 抽油烟机风扇实体 (fan)
        if context.has_service("switch") or context.has_service("gear"):
            def fan_state(device: DeviceContext) -> Mapping[str, Any]:
                is_on = _as_bool(device.value("switch", "on"))
                gear_val = _as_int(device.value("gear", "gear")) or 0
                pct = _GEAR_TO_PERCENT.get(gear_val, 0)
                return {
                    "is_on": is_on if is_on is not None else (gear_val > 0),
                    "percentage": pct if is_on else 0,
                }

            async def turn_on(device: DeviceContext, data: Mapping[str, Any]) -> None:
                pct = data.get("percentage")
                gear = 1
                if pct is not None:
                    if pct > 66:
                        gear = 3
                    elif pct > 33:
                        gear = 2
                    elif pct > 0:
                        gear = 1
                    else:
                        gear = 0
                if gear > 0:
                    await device.async_send_service("switch", {"on": 1})
                    await device.async_send_service("gear", {"gear": gear})
                else:
                    await device.async_send_service("gear", {"gear": 0})
                    await device.async_send_service("switch", {"on": 0})

            async def turn_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("gear", {"gear": 0})
                await device.async_send_service("switch", {"on": 0})

            async def set_percentage(device: DeviceContext, data: Mapping[str, Any]) -> None:
                pct = data.get("percentage", 0)
                if pct > 66:
                    gear = 3
                elif pct > 33:
                    gear = 2
                elif pct > 0:
                    gear = 1
                else:
                    gear = 0
                if gear > 0:
                    await device.async_send_service("switch", {"on": 1})
                    await device.async_send_service("gear", {"gear": gear})
                else:
                    await device.async_send_service("gear", {"gear": 0})
                    await device.async_send_service("switch", {"on": 0})

            specs.append(
                EntitySpec(
                    platform="fan",
                    key="hood",
                    name="抽油烟机",
                    state=fan_state,
                    metadata={"supports_percentage": True, "speed_count": 3},
                    actions={
                        "turn_on": turn_on,
                        "turn_off": turn_off,
                        "set_percentage": set_percentage,
                    },
                )
            )

        # 2. 烟机照明灯 (light)
        if context.has_service("lightSwitch"):
            def light_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("lightSwitch", "on"))}

            async def light_on(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("lightSwitch", {"on": 1})

            async def light_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("lightSwitch", {"on": 0})

            specs.append(
                EntitySpec(
                    platform="light",
                    key="light",
                    name="烟机照明灯",
                    state=light_state,
                    actions={"turn_on": light_on, "turn_off": light_off},
                    metadata={"icon": "mdi:lightbulb"},
                )
            )

        # 3. 运行状态 (sensor)
        if context.has_service("status"):
            def status_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("status", "status"))
                return {"native_value": _STATUS_TEXT.get(val, "关机" if val is None else f"未知({val})")}

            specs.append(
                EntitySpec(
                    platform="sensor",
                    key="work_status",
                    name="工作状态",
                    state=status_state,
                    metadata={"icon": "mdi:information-outline"},
                )
            )

        # 4. 左右灶具火候联动状态 (binary_sensor)
        if context.has_service("workBurnerStatus"):
            def left_burner_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("workBurnerStatus", "leftStatus"))
                return {"is_on": val == 1}

            def right_burner_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("workBurnerStatus", "rightStatus"))
                return {"is_on": val == 1}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="left_burner",
                    name="左灶火候状态",
                    state=left_burner_state,
                    metadata={"icon": "mdi:fire"},
                )
            )
            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="right_burner",
                    name="右灶火候状态",
                    state=right_burner_state,
                    metadata={"icon": "mdi:fire"},
                )
            )

        # 5. 故障告警 (binary_sensor)
        if context.has_service("commonFaultDetection"):
            def fault_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("commonFaultDetection", "status")) is True}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="fault",
                    name="设备故障告警",
                    state=fault_state,
                    metadata={"device_class": "problem"},
                )
            )

        # 6. Wi-Fi 信号 (sensor)
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
                    metadata={"unit": "%", "state_class": "measurement", "icon": "mdi:wifi"},
                )
            )

        return tuple(specs)


ADAPTER = ProductA3DGAdapter()
