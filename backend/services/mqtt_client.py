"""MQTT 클라이언트 - AI 서버와 추천 통신."""
from __future__ import annotations

import json
import logging
import asyncio
from typing import Callable, Dict, Any, Optional

import paho.mqtt.client as mqtt
from backend.core.config import settings

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT 클라이언트 - 추천 수신/피드백 전송."""
    
    def __init__(self):
        """MQTT 클라이언트 초기화."""
        self.broker = settings.mqtt_broker
        self.port = settings.mqtt_port
        self.client = None
        self.is_connected = False
        self.callbacks: Dict[str, Callable] = {}
        
        # Topic 정의
        self.topics = {
            "recommendations_receive": "gaze/recommendations/receive",
            "recommendations_feedback": "gaze/recommendations/feedback"
        }
        
        logger.info(f"MQTTClient initialized: broker={self.broker}:{self.port}")
    
    def connect(self):
        """MQTT Broker에 연결."""
        if not self.broker:
            logger.warning("MQTT broker not configured, skipping connection")
            return False
        
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            logger.info(f"Connecting to MQTT broker: {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            # 연결 대기 (최대 5초)
            for _ in range(50):
                if self.is_connected:
                    logger.info("Connected to MQTT broker")
                    return True
                asyncio.sleep(0.1)
            
            logger.warning("MQTT connection timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """MQTT Broker 연결 해제."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info("Disconnected from MQTT broker")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백."""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT connection established")
            
            # 추천 수신 topic 구독
            client.subscribe(self.topics["recommendations_receive"])
            logger.info(f"Subscribed to {self.topics['recommendations_receive']}")
            
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT 연결 해제 콜백."""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT 메시지 수신 콜백."""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.info(f"MQTT message received: topic={topic}, payload={payload}")
            
            # 등록된 콜백 실행
            if topic in self.callbacks:
                callback = self.callbacks[topic]
                callback(payload)
            else:
                logger.warning(f"No callback registered for topic: {topic}")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to decode MQTT message: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    def on_recommendations_receive(self, callback: Callable):
        """추천 수신 콜백 등록."""
        self.callbacks[self.topics["recommendations_receive"]] = callback
        logger.info(f"Registered callback for recommendations_receive")
    
    def publish_feedback(self, title: str, confirm: bool) -> bool:
        """기능: 추천 피드백을 AI Server로 발행.
        
        args: title, confirm
        return: 발행 성공 여부
        """
        if not self.is_connected:
            logger.error("MQTT not connected, cannot publish feedback")
            return False
        
        try:
            payload = {
                "title": title,
                "confirm": confirm
            }
            
            topic = self.topics["recommendations_feedback"]
            logger.info(f"Publishing feedback: title={title}, confirm={confirm}")
            
            self.client.publish(
                topic,
                json.dumps(payload),
                qos=1  # At least once delivery
            )
            
            logger.info(f"Feedback published to {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish feedback: {e}")
            return False


# 전역 MQTT 클라이언트 인스턴스
mqtt_client = MQTTClient()
