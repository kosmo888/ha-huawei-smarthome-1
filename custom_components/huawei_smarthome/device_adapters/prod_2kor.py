"""User-contributed protocol for Huawei product 2KOR (香山 iN9201B 智能营养秤).

设备类型: 厨房秤 / 营养秤 (Nutrition Scale), 型号 iN9201B (prodId: 2KOR, deviceTypeId: 227)
制造商: 香山衡器 (Xiangshan)
Profile: https://smarthome-drcn.dbankcdn.com/device/guide/2KOR/2KOR.json

核心服务:
   weight.weight        string R   实时重量数据 (如 "125.5")
   unit.unit            enum   RW  单位 (0=g, 1=ml(水), 2=ml(牛奶))
   connect.connect      enum   RW  连接状态 (0=未连接, 1=正在连接, 2=已连接)
   alert.alert          enum   R   告警提示 (1=低电提醒)
   switchOff.switchOff  enum   W   关机 (0=关机)
   netInfo.intensity    enum   R   Wi-Fi信号

本适配器暴露:
   1. sensor 实体: 重量读数 (weight, unit: g)
   2. select 实体: 称重单位选择 (g / ml(水) / ml(牛奶))
   3. binary_sensor 实体: 蓝牙/Wi-Fi在线连接状态 (connectivity)
   4. binary_sensor 实体: 低电量提醒 (battery)
   5. button 实体: 远程关机 (switchOff)
   6. sensor 实体: Wi-Fi信号强度 (%)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

_UNIT_OPTIONS = ["g", "ml(水)", "ml(牛奶)"]
_UNIT_VAL_TO_NAME = {0: "g", 1: "ml(水)", 2: "ml(牛奶)"}
_UNIT_NAME_TO_VAL = {v: k for k, v in _UNIT_VAL_TO_NAME.items()}


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


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Product2KORAdapter:
    """香山智能营养秤 (2KOR) 适配器。"""

    prod_id = "2KOR"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        if context.profile is None:
            return ()

        specs: list[EntitySpec] = []

        # 1. 实时称重重量 (sensor)
        if context.has_service("weight"):
            def weight_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_float(device.value("weight", "weight"))
                return {"native_value": val}

            specs.append(
                EntitySpec(
                    platform="sensor",
                    key="weight",
                    name="重量读数",
                    state=weight_state,
                    metadata={
                        "unit": "g",
                        "state_class": "measurement",
                        "icon": "mdi:scale",
                    },
                )
            )

        # 2. 单位选择 (select)
        if context.has_service("unit"):
            def unit_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("unit", "unit"))
                return {"current_option": _UNIT_VAL_TO_NAME.get(val, "g")}

            async def set_unit(device: DeviceContext, data: Mapping[str, Any]) -> None:
                opt = data.get("option")
                val = _UNIT_NAME_TO_VAL.get(str(opt))
                if val is not None:
                    await device.async_send_service("unit", {"unit": val})

            specs.append(
                EntitySpec(
                    platform="select",
                    key="unit",
                    name="称量单位",
                    state=unit_state,
                    metadata={"options": _UNIT_OPTIONS},
                    actions={"select_option": set_unit},
                )
            )

        # 3. 连接状态 (binary_sensor)
        if context.has_service("connect"):
            def connect_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("connect", "connect"))
                return {"is_on": val == 2}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="connected",
                    name="连接状态",
                    state=connect_state,
                    metadata={"device_class": "connectivity"},
                )
            )

        # 4. 低电量提示 (binary_sensor)
        if context.has_service("alert"):
            def alert_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("alert", "alert"))
                return {"is_on": val == 1}

            specs.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="low_battery",
                    name="低电量提醒",
                    state=alert_state,
                    metadata={"device_class": "battery"},
                )
            )

        # 5. 关机按钮 (button)
        if context.has_service("switchOff"):
            async def press_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("switchOff", {"switchOff": 0})

            specs.append(
                EntitySpec(
                    platform="button",
                    key="power_off",
                    name="关机",
                    state=lambda _d: {},
                    actions={"press": press_off},
                    metadata={"icon": "mdi:power"},
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


ADAPTER = Product2KORAdapter()
