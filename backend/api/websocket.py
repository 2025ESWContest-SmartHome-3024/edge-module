"""실시간 시선 스트리밍을 위한 WebSocket 엔드포인트."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.gaze_tracker import WebGazeTracker


router = APIRouter()


class ConnectionManager:
    """WebSocket 연결을 관리합니다."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """새로운 연결을 수락하고 등록합니다.
        
        Args:
            websocket: WebSocket 연결
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] 클라이언트 연결됨. 총 연결 수: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """연결을 제거합니다.
        
        Args:
            websocket: 제거할 WebSocket 연결
        """
        self.active_connections.remove(websocket)
        print(f"[WebSocket] 클라이언트 연결 해제됨. 총 연결 수: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """모든 연결된 클라이언트에 메시지를 전송합니다.
        
        Args:
            message: 전송할 메시지 딕셔너리
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WebSocket] 클라이언트에 전송 오류: {e}")
                disconnected.append(connection)
        
        # 연결 해제된 클라이언트 정리
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)


# 전역 연결 관리자
manager = ConnectionManager()


@router.websocket("/gaze")
async def websocket_gaze(websocket: WebSocket):
    """실시간 시선 스트리밍용 WebSocket 엔드포인트.
    
    약 30-60 FPS로 시선 좌표를 연결된 클라이언트에 전송합니다.
    """
    await manager.connect(websocket)
    
    try:
        # 순환 의존성을 피하기 위해 여기서 임포트
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None or not gaze_tracker.is_running:
            await websocket.send_json({
                "type": "error",
                "message": "시선 추적기가 초기화되지 않았습니다"
            })
            await websocket.close()
            return
        
        # 초기 캘리브레이션 상태 전송
        state = gaze_tracker.get_current_state()
        await websocket.send_json({
            "type": "calibration_status",
            "calibrated": state["calibrated"],
            "message": "시선 추적기에 연결됨"
        })
        
        # 시선 데이터 스트리밍
        last_sent_time = 0
        min_interval = 1.0 / 30.0  # 최대 30 FPS (클라이언트를 압도하지 않기 위해)
        
        while True:
            state = gaze_tracker.get_current_state()
            current_time = asyncio.get_event_loop().time()
            
            # 업데이트 속도 제한
            if current_time - last_sent_time >= min_interval:
                # JSON 직렬화를 위해 numpy 타입을 Python 네이티브 타입으로 변환
                message = {
                    "type": "gaze_update",
                    "timestamp": current_time,
                    "gaze": state["gaze"],
                    "raw_gaze": state["raw_gaze"],
                    "blink": bool(state["blink"]) if state["blink"] is not None else False,
                    "calibrated": bool(state["calibrated"]) if state["calibrated"] is not None else False
                }
                
                await websocket.send_json(message)
                last_sent_time = current_time
            
            # 바쁜 대기를 방지하기 위해 작은 대기
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] 시선 스트림 오류: {e}")
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/control")
async def websocket_control(websocket: WebSocket):
    """제어 명령을 수신하기 위한 WebSocket 엔드포인트.
    
    캘리브레이션 트리거, 설정 변경 등의 명령을 수락합니다.
    """
    await websocket.accept()
    
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            await websocket.send_json({
                "type": "error",
                "message": "시선 추적기가 초기화되지 않았습니다"
            })
            await websocket.close()
            return
        
        while True:
            data = await websocket.receive_json()
            command = data.get("command")
            
            if command == "start_calibration":
                # TODO: 캘리브레이션 워크플로우 구현
                await websocket.send_json({
                    "type": "response",
                    "command": command,
                    "status": "not_implemented",
                    "message": "캘리브레이션 워크플로우가 아직 구현되지 않았습니다"
                })
            
            elif command == "load_calibration":
                calibration_file = data.get("file")
                try:
                    gaze_tracker.load_calibration(calibration_file)
                    await websocket.send_json({
                        "type": "response",
                        "command": command,
                        "status": "success",
                        "message": f"캘리브레이션 로드됨: {calibration_file}"
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "response",
                        "command": command,
                        "status": "error",
                        "message": str(e)
                    })
            
            elif command == "save_calibration":
                calibration_file = data.get("file")
                try:
                    gaze_tracker.save_calibration(calibration_file)
                    await websocket.send_json({
                        "type": "response",
                        "command": command,
                        "status": "success",
                        "message": f"캘리브레이션 저장됨: {calibration_file}"
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "response",
                        "command": command,
                        "status": "error",
                        "message": str(e)
                    })
            
            else:
                await websocket.send_json({
                    "type": "response",
                    "command": command,
                    "status": "unknown",
                    "message": f"알 수 없는 명령: {command}"
                })
    
    except WebSocketDisconnect:
        print("[WebSocket] 제어 클라이언트 연결 해제됨")
    except Exception as e:
        print(f"[WebSocket] 제어 소켓 오류: {e}")
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/features")
async def websocket_features(websocket: WebSocket):
    """캘리브레이션 중 실시간 특징 추출용 WebSocket 엔드포인트.
    
    캘리브레이션 목적으로 원본 특징 및 얼굴 감지 상태를 스트리밍합니다.
    """
    await websocket.accept()
    
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None or gaze_tracker.cap is None:
            await websocket.send_json({
                "type": "error",
                "message": "시선 추적기가 초기화되지 않았습니다"
            })
            await websocket.close()
            return
        
        print("[WebSocket] 캘리브레이션용 특징 스트림 연결됨")
        
        # 캘리브레이션을 위해 낮은 속도로 특징 스트리밍
        last_sent_time = 0
        min_interval = 1.0 / 30.0  # 최대 30 FPS
        
        while True:
            current_time = asyncio.get_event_loop().time()
            
            if current_time - last_sent_time >= min_interval:
                # 프레임 읽기 및 특징 추출
                ret, frame = gaze_tracker.cap.read()
                if not ret:
                    await asyncio.sleep(0.01)
                    continue
                
                # 특징 추출
                features, blink_detected = gaze_tracker.gaze_estimator.extract_features(frame)
                
                # 특징 데이터 전송 (numpy 타입을 Python 네이티브 타입으로 변환)
                message = {
                    "type": "features",
                    "timestamp": current_time,
                    "has_face": features is not None,
                    "blink": bool(blink_detected),  # numpy.bool_을 Python bool로 변환
                    "features": features.tolist() if features is not None else None
                }
                
                await websocket.send_json(message)
                last_sent_time = current_time
            
            # 바쁜 대기를 방지하기 위해 작은 대기
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        print("[WebSocket] 특징 스트림 연결 해제됨")
    except Exception as e:
        print(f"[WebSocket] 특징 스트림 오류: {e}")
        try:
            await websocket.close()
        except:
            pass
