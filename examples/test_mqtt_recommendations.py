"""MQTT 기반 추천 시스템 테스트 가이드."""
import asyncio
import json
import paho.mqtt.client as mqtt
import time

MQTT_BROKER = "your-mqtt-broker.com"  # MQTT 브로커 주소로 변경
MQTT_PORT = 1883

# Topic 정의
TOPIC_RECOMMENDATIONS_RECEIVE = "gaze/recommendations/receive"
TOPIC_RECOMMENDATIONS_FEEDBACK = "gaze/recommendations/feedback"


def setup_mqtt_subscriber():
    """MQTT Subscriber 설정 (AI Server 시뮬레이션)."""
    print(f"\n========== MQTT Subscriber (AI Server) ==========")
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Subscribing to: {TOPIC_RECOMMENDATIONS_FEEDBACK}")
    print("=" * 50)
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to MQTT Broker")
            # 피드백 토픽 구독
            client.subscribe(TOPIC_RECOMMENDATIONS_FEEDBACK)
            print(f"✅ Subscribed to {TOPIC_RECOMMENDATIONS_FEEDBACK}")
        else:
            print(f"❌ Connection failed with code {rc}")
    
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"\n📨 Feedback received:")
            print(f"   Title: {payload.get('title')}")
            print(f"   Confirm: {payload.get('confirm')}")
            print(f"   ({payload.get('confirm')} = YES, {not payload.get('confirm')} = NO)")
        except Exception as e:
            print(f"❌ Error processing message: {e}")
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    return client


def send_recommendation(client: mqtt.Client, title: str, content: str):
    """AI Server → Edge: 추천 전송."""
    print(f"\n========== Sending Recommendation ==========")
    
    payload = {
        "title": title,
        "content": content
    }
    
    print(f"Publishing to {TOPIC_RECOMMENDATIONS_RECEIVE}:")
    print(f"  Title: {title}")
    print(f"  Content: {content}")
    
    client.publish(
        TOPIC_RECOMMENDATIONS_RECEIVE,
        json.dumps(payload),
        qos=1
    )
    
    print("✅ Recommendation published")


def main():
    """전체 테스트 시나리오."""
    try:
        # MQTT Subscriber 생성 (AI Server 역할)
        subscriber = setup_mqtt_subscriber()
        subscriber.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        subscriber.loop_start()
        
        # 연결 대기
        time.sleep(2)
        
        # Publisher 생성 (프론트엔드/테스트 역할)
        publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        publisher.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        publisher.loop_start()
        
        # 시나리오 1: 추천 전송
        print("\n\n" + "=" * 60)
        print("SCENARIO 1: AI가 추천을 Edge로 전송")
        print("=" * 60)
        
        send_recommendation(
            publisher,
            title="에어컨 킬까요?",
            content="실내 온도가 26도까지 올라갔습니다. 에어컨을 켜서 온도를 낮추는 것을 추천합니다."
        )
        
        # 피드백 대기
        time.sleep(3)
        
        # 시나리오 2: 추천 전송
        print("\n\n" + "=" * 60)
        print("SCENARIO 2: 다른 추천 전송")
        print("=" * 60)
        
        send_recommendation(
            publisher,
            title="불 꺼드릴까요?",
            content="더 이상 필요하지 않은 조명을 꺼서 에너지를 절약하는 것을 추천합니다."
        )
        
        # 피드백 대기
        time.sleep(3)
        
        print("\n\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        print("\n테스트 흐름:")
        print("1️⃣ AI Server가 MQTT로 추천 발행 (gaze/recommendations/receive)")
        print("2️⃣ Edge가 MQTT 메시지 수신")
        print("3️⃣ Edge가 WebSocket으로 Frontend에 추천 전달")
        print("4️⃣ Frontend가 사용자 응답 (YES/NO) → REST API로 Edge에 전송")
        print("5️⃣ Edge가 피드백을 MQTT로 AI Server에 발행 (gaze/recommendations/feedback)")
        print("6️⃣ AI Server가 피드백 수신 ✅")
        
        # 정리
        subscriber.loop_stop()
        publisher.loop_stop()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
