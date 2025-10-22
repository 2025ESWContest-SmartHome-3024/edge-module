"""추천 API 테스트 가이드."""
import asyncio
import httpx

BASE_URL = "http://localhost:8080"


async def test_receive_recommendation():
    """테스트 1️⃣: AI Server → Edge 추천 받기."""
    print("\n========== TEST 1️⃣: RECEIVE RECOMMENDATION ==========")
    
    payload = {
        "title": "에어컨 킬까요?",
        "content": "실내 온도가 26도까지 올라갔습니다. 에어컨을 켜서 온도를 낮추는 것을 추천합니다."
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{BASE_URL}/api/recommendations/receive",
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 200
        assert response.json()["message"] == "received"


async def test_send_feedback_yes():
    """테스트 2️⃣: Backend → AI Server 피드백 (YES)."""
    print("\n========== TEST 2️⃣: FEEDBACK (YES) ==========")
    
    payload = {
        "title": "에어컨 킬까요?",
        "confirm": True
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{BASE_URL}/api/recommendations/feedback",
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 200
        assert "[EDGE]" in response.json()["message"]


async def test_send_feedback_no():
    """테스트 3️⃣: Backend → AI Server 피드백 (NO)."""
    print("\n========== TEST 3️⃣: FEEDBACK (NO) ==========")
    
    payload = {
        "title": "에어컨 킬까요?",
        "confirm": False
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{BASE_URL}/api/recommendations/feedback",
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 200
        assert "[EDGE]" in response.json()["message"]


async def main():
    """모든 테스트 실행."""
    try:
        await test_receive_recommendation()
        await test_send_feedback_yes()
        await test_send_feedback_no()
        print("\n✅ 모든 테스트 통과!")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")


if __name__ == "__main__":
    asyncio.run(main())
