"""User-contributed protocol for Huawei product 115J (遥控大师空调伴侣).

设备类型: 万能遥控器 / 空调伴侣 (Air Conditioner Companion), 型号 YKK-KT16A (prodId: 115J, deviceTypeId: 007)
制造商: 深圳遥看科技有限公司 (Yaokan)
Profile: https://smarthome-drcn.dbankcdn.com/device/guide/115J/115J.json

核心服务:
   airKey.power         enum RW (0=关机, 1=开机)
   airKey.mode          enum RW (0=自动, 1=除湿, 2=送风, 3=制热, 4=制冷)
   airKey.wind          enum RW (0=自动, 1=低风, 2=中风, 3=高风)
   airKey.temp          int  RW (目标温度 ℃, 16-30)
   airKey.up            enum RW (0=扫风关, 1=扫风开)
   ledOnoff.ledOnoff    bool RW (指示灯 0=关, 1=开)
   powerCon.watt        int  R  (当前功率 W)
   powerCon.power       int  R  (用电量 kWh)
   netInfo.intensity    enum R  (Wi-Fi信号)

本适配器暴露:
   1. climate 实体: 空调伴侣控制 (开关 / 模式 / 目标温度 / 风速 / 摆风)
   2. switch 实体: 指示灯开关 (ledOnoff)
   3. sensor 实体: 当前功率 (W)
   4. sensor 实体: 累计电量 (kWh)
   5. sensor 实体: Wi-Fi信号强度 (%)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

_TEMP_MIN = 16.0
_TEMP_MAX = 30.0

# 115J airKey: 0:自动, 1:除湿, 2:送风, 3:制热, 4:制冷
_DEV_TO_HVAC = {0: "auto", 1: "dry", 2: "fan_only", 3: "heat", 4: "cool"}
_HVAC_TO_DEV = {v: k for k, v in _DEV_TO_HVAC.items()}

# 115J wind: 0:自动, 1:低风, 2:中风, 3:高风
_DEV_TO_FAN = {0: "auto", 1: "low", 2: "medium", 3: "high"}
_FAN_TO_DEV = {v: k for k, v in _DEV_TO_FAN.items()}

# 115J up: 0:扫风关, 1:扫风开
_DEV_TO_SWING = {0: "off", 1: "vertical"}
_SWING_TO_DEV = {v: k for k, v in _DEV_TO_SWING.items()}


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


class Product115JAdapter:
    """遥控大师空调伴侣 (115J) 适配器。"""

    prod_id = "115J"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        if context.profile is None:
            return ()

        specs: list[EntitySpec] = []

        # 1. Climate 实体 (airKey 服务)
        if context.has_service("airKey"):
            def climate_state(device: DeviceContext) -> Mapping[str, Any]:
                power = _as_int(device.value("airKey", "power"))
                if power == 0:
                    hvac_mode = "off"
                else:
                    dev_mode = _as_int(device.value("airKey", "mode"))
                    hvac_mode = _DEV_TO_HVAC.get(dev_mode, "auto")

                target_temp = _as_float(device.value("airKey", "temp"))

                dev_fan = _as_int(device.value("airKey", "wind"))
                fan_mode = _DEV_TO_FAN.get(dev_fan, "auto")

                dev_swing = _as_int(device.value("airKey", "up"))
                swing_mode = _DEV_TO_SWING.get(dev_swing, "off")

                return {
                    "hvac_mode": hvac_mode,
                    "target_temperature": target_temp,
                    "fan_mode": fan_mode,
                    "swing_mode": swing_mode,
                }

            async def set_hvac_mode(device: DeviceContext, data: Mapping[str, Any]) -> None:
                mode = data.get("hvac_mode")
                if mode == "off":
                    await device.async_send_service("airKey", {"power": 0})
                    return
                dev_val = _HVAC_TO_DEV.get(str(mode))
                if dev_val is None:
                    return
                await device.async_send_service("airKey", {"power": 1, "mode": dev_val})

            async def set_temperature(device: DeviceContext, data: Mapping[str, Any]) -> None:
                temp = data.get("temperature")
                if temp is None:
                    return
                val = int(round(max(_TEMP_MIN, min(_TEMP_MAX, float(temp)))))
                await device.async_send_service("airKey", {"temp": val})

            async def set_fan_mode(device: DeviceContext, data: Mapping[str, Any]) -> None:
                fan = data.get("fan_mode")
                val = _FAN_TO_DEV.get(str(fan))
                if val is not None:
                    await device.async_send_service("airKey", {"wind": val})

            async def set_swing_mode(device: DeviceContext, data: Mapping[str, Any]) -> None:
                swing = data.get("swing_mode")
                val = _SWING_TO_DEV.get(str(swing))
                if val is not None:
                    await device.async_send_service("airKey", {"up": val})

            async def turn_on(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("airKey", {"power": 1})

            async def turn_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("airKey", {"power": 0})

            specs.append(
                EntitySpec(
                    platform="climate",
                    key="ac",
                    name="空调",
                    state=climate_state,
                    metadata={
                        "hvac_modes": ["off", "auto", "cool", "heat", "fan_only", "dry"],
                        "fan_modes": ["auto", "low", "medium", "high"],
                        "swing_modes": ["off", "vertical"],
                        "min_temp": _TEMP_MIN,
                        "max_temp": _TEMP_MAX,
                        "temp_step": 1.0,
                    },
                    actions={
                        "set_hvac_mode": set_hvac_mode,
                        "set_temperature": set_temperature,
                        "set_fan_mode": set_fan_mode,
                        "set_swing_mode": set_swing_mode,
                        "turn_on": turn_on,
                        "turn_off": turn_off,
                    },
                )
            )

        # 2. 指示灯开关 (ledOnoff)
        if context.has_service("ledOnoff"):
            def led_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"is_on": _as_bool(device.value("ledOnoff", "ledOnoff"))}

            async def led_on(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("ledOnoff", {"ledOnoff": 1})

            async def led_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
                await device.async_send_service("ledOnoff", {"ledOnoff": 0})

            specs.append(
                EntitySpec(
                    platform="switch",
                    key="led",
                    name="指示灯",
                    state=led_state,
                    actions={"turn_on": led_on, "turn_off": led_off},
                    metadata={"icon": "mdi:led-on"},
                )
            )

        # 3. 功率与电量监测 (powerCon)
        if context.has_service("powerCon"):
            def watt_state(device: DeviceContext) -> Mapping[str, Any]:
                return {"native_value": _as_int(device.value("powerCon", "watt"))}

            def power_state(device: DeviceContext) -> Mapping[str, Any]:
                # power 字段单位为 kWh 或基础电量
                return {"native_value": _as_float(device.value("powerCon", "power"))}

            specs.append(
                EntitySpec(
                    platform="sensor",
                    key="power_watt",
                    name="当前功率",
                    state=watt_state,
                    metadata={"device_class": "power", "unit": "W", "state_class": "measurement"},
                )
            )
            specs.append(
                EntitySpec(
                    platform="sensor",
                    key="energy_consumption",
                    name="累计用电量",
                    state=power_state,
                    metadata={"device_class": "energy", "unit": "kWh", "state_class": "total_increasing"},
                )
            )

        # 4. Wi-Fi 信号 (netInfo)
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


ADAPTER = Product115JAdapter()
