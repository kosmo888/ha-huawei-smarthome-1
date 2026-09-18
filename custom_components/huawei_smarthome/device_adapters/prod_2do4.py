"""User-contributed protocol for Huawei product 2DO4 (讯飞智能录音笔 H1).

设备类型: 数码录音笔 (Voice Recorder), 型号 B2Y21M (prodId: 2DO4, deviceTypeId: 000)
制造商: 听见科技 / 科大讯飞 (iFLYTEK)
Profile: https://smarthome-drcn.dbankcdn.com/device/guide/2DO4/2DO4.json

核心服务:
   commonMode1.mode     enum RW (0=无模式, 1=模式1, 2=模式2, 3=模式3) 录音模式
   netInfo.intensity    enum R  (Wi-Fi信号)

本适配器暴露:
   1. select 实体: 录音模式选择 (无模式 / 采访模式 / 会议模式 / 演讲模式)
   2. sensor 实体: Wi-Fi信号强度 (%)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

_MODE_OPTIONS = ["无模式", "采访模式", "会议模式", "演讲模式"]
_MODE_VAL_TO_NAME = {0: "无模式", 1: "采访模式", 2: "会议模式", 3: "演讲模式"}
_MODE_NAME_TO_VAL = {v: k for k, v in _MODE_VAL_TO_NAME.items()}


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


class Product2DO4Adapter:
    """讯飞智能录音笔 H1 (2DO4) 适配器。"""

    prod_id = "2DO4"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        if context.profile is None:
            return ()

        specs: list[EntitySpec] = []

        # 1. 录音模式 (select)
        if context.has_service("commonMode1"):
            def mode_state(device: DeviceContext) -> Mapping[str, Any]:
                val = _as_int(device.value("commonMode1", "mode"))
                return {"current_option": _MODE_VAL_TO_NAME.get(val, "无模式")}

            async def set_mode(device: DeviceContext, data: Mapping[str, Any]) -> None:
                opt = data.get("option")
                val = _MODE_NAME_TO_VAL.get(str(opt))
                if val is not None:
                    await device.async_send_service("commonMode1", {"mode": val})

            specs.append(
                EntitySpec(
                    platform="select",
                    key="record_mode",
                    name="录音模式",
                    state=mode_state,
                    metadata={"options": _MODE_OPTIONS, "icon": "mdi:microphone"},
                    actions={"select_option": set_mode},
                )
            )

        # 2. Wi-Fi 信号 (sensor)
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


ADAPTER = Product2DO4Adapter()
