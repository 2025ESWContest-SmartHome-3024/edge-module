"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
from __future__ import annotations

from typing import Any, Literal
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()


# Mock 디바이스 데이터베이스
# 프로덕션 환경에서는 Home Assistant, MQTT 또는 다른 스마트 홈 플랫폼에 연결됩니다
DEVICES = {
    "ac_001": {
        "id": "ac_001",
        "name": "거실 에어컨",
        "type": "air_conditioner",
        "room": "거실",
        "state": "off",
        "current_temp": 26,
        "target_temp": 24,
        "mode": "cool",
        "fan_speed": "auto"
    },
    "purifier_001": {
        "id": "purifier_001",
        "name": "침실 공기청정기",
        "type": "air_purifier",
        "room": "침실",
        "state": "on",
        "mode": "auto",
        "pm25": 12,
        "fan_speed": "medium"
    },
    "light_001": {
        "id": "light_001",
        "name": "거실 조명",
        "type": "light",
        "room": "거실",
        "state": "on",
        "brightness": 80,
        "color_temp": 4000
    },
    "thermostat_001": {
        "id": "thermostat_001",
        "name": "온도조절기",
        "type": "thermostat",
        "room": "거실",
        "state": "on",
        "current_temp": 23.5,
        "target_temp": 24,
        "mode": "heat"
    }
}


# Pydantic 모델
class DeviceType(str, Enum):
    """디바이스 종류."""
    AIR_CONDITIONER = "air_conditioner"
    AIR_PURIFIER = "air_purifier"
    LIGHT = "light"
    THERMOSTAT = "thermostat"


class DeviceState(str, Enum):
    """디바이스 상태."""
    ON = "on"
    OFF = "off"


class Device(BaseModel):
    """디바이스 정보."""
    id: str
    name: str
    type: DeviceType
    room: str
    state: DeviceState
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceControl(BaseModel):
    """디바이스 제어 명령."""
    action: str = Field(..., description="수행할 동작 (예: 'turn_on', 'set_temperature')")
    params: dict[str, Any] = Field(default_factory=dict, description="동작 파라미터")


class DeviceControlResponse(BaseModel):
    """디바이스 제어 응답."""
    success: bool
    device_id: str
    action: str
    message: str
    new_state: dict[str, Any] | None = None


@router.get("", response_model=list[Device])
async def get_devices():
    """모든 사용 가능한 디바이스를 가져옵니다.
    
    Returns:
        디바이스 목록
    """
    devices = []
    for device_data in DEVICES.values():
        # 디바이스 필드와 메타데이터 분리
        metadata = {k: v for k, v in device_data.items() 
                   if k not in ["id", "name", "type", "room", "state"]}
        
        devices.append(Device(
            id=device_data["id"],
            name=device_data["name"],
            type=device_data["type"],
            room=device_data["room"],
            state=device_data["state"],
            metadata=metadata
        ))
    
    return devices


@router.get("/{device_id}")
async def get_device(device_id: str):
    """특정 디바이스의 상세 정보를 가져옵니다.
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        디바이스 정보
    """
    if device_id not in DEVICES:
        raise HTTPException(status_code=404, detail=f"디바이스 {device_id}를 찾을 수 없습니다")
    
    return DEVICES[device_id]


@router.post("/{device_id}/control", response_model=DeviceControlResponse)
async def control_device(device_id: str, command: DeviceControl):
    """디바이스를 제어합니다.
    
    예시:
    - 켜기/끄기: {"action": "turn_on"} 또는 {"action": "turn_off"}
    - 온도 설정: {"action": "set_temperature", "params": {"temperature": 24}}
    - 모드 설정: {"action": "set_mode", "params": {"mode": "cool"}}
    - 밝기 설정: {"action": "set_brightness", "params": {"brightness": 50}}
    
    Args:
        device_id: 디바이스 ID
        command: 제어 명령
        
    Returns:
        제어 결과
    """
    if device_id not in DEVICES:
        raise HTTPException(status_code=404, detail=f"디바이스 {device_id}를 찾을 수 없습니다")
    
    device = DEVICES[device_id]
    action = command.action
    params = command.params
    
    try:
        # 공통 동작 처리
        if action == "turn_on":
            device["state"] = "on"
            message = f"{device['name']} 켜짐"
        
        elif action == "turn_off":
            device["state"] = "off"
            message = f"{device['name']} 꺼짐"
        
        elif action == "toggle":
            device["state"] = "off" if device["state"] == "on" else "on"
            message = f"{device['name']} 상태 변경: {device['state']}"
        
        # 디바이스별 동작
        elif action == "set_temperature":
            if device["type"] in ["air_conditioner", "thermostat"]:
                temp = params.get("temperature")
                if temp is None:
                    raise ValueError("온도 파라미터가 필요합니다")
                device["target_temp"] = temp
                message = f"{device['name']} 온도 설정: {temp}°C"
            else:
                raise ValueError(f"디바이스 {device_id}는 온도 제어를 지원하지 않습니다")
        
        elif action == "set_mode":
            mode = params.get("mode")
            if mode is None:
                raise ValueError("모드 파라미터가 필요합니다")
            device["mode"] = mode
            message = f"{device['name']} 모드 설정: {mode}"
        
        elif action == "set_brightness":
            if device["type"] == "light":
                brightness = params.get("brightness")
                if brightness is None:
                    raise ValueError("밝기 파라미터가 필요합니다")
                device["brightness"] = brightness
                message = f"{device['name']} 밝기 설정: {brightness}%"
            else:
                raise ValueError(f"디바이스 {device_id}는 밝기 제어를 지원하지 않습니다")
        
        elif action == "set_fan_speed":
            if device["type"] in ["air_conditioner", "air_purifier"]:
                fan_speed = params.get("fan_speed")
                if fan_speed is None:
                    raise ValueError("팬 속도 파라미터가 필요합니다")
                device["fan_speed"] = fan_speed
                message = f"{device['name']} 팬 속도 설정: {fan_speed}"
            else:
                raise ValueError(f"디바이스 {device_id}는 팬 속도 제어를 지원하지 않습니다")
        
        else:
            raise ValueError(f"알 수 없는 동작: {action}")
        
        # TODO: 실제 스마트 홈 플랫폼에 명령 전송 (Home Assistant, MQTT 등)
        # await send_to_home_assistant(device_id, action, params)
        
        return DeviceControlResponse(
            success=True,
            device_id=device_id,
            action=action,
            message=message,
            new_state=device
        )
    
    except Exception as e:
        return DeviceControlResponse(
            success=False,
            device_id=device_id,
            action=action,
            message=f"오류: {str(e)}",
            new_state=None
        )


@router.get("/room/{room_name}")
async def get_devices_by_room(room_name: str):
    """특정 방의 모든 디바이스를 가져옵니다.
    
    Args:
        room_name: 방 이름
        
    Returns:
        해당 방의 디바이스 목록
    """
    devices = [
        device for device in DEVICES.values()
        if device["room"] == room_name
    ]
    
    if not devices:
        raise HTTPException(status_code=404, detail=f"방 {room_name}에서 디바이스를 찾을 수 없습니다")
    
    return devices


@router.get("/type/{device_type}")
async def get_devices_by_type(device_type: DeviceType):
    """Get all devices of a specific type."""
    devices = [
        device for device in DEVICES.values()
        if device["type"] == device_type.value
    ]
    
    return devices
