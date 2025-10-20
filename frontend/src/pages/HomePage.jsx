import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Eye, LogOut, Settings, Sparkles,
    X, Bell, TrendingUp, User
} from 'lucide-react'
import GazeCursor from '../components/GazeCursor'
import DeviceCard from '../components/DeviceCard'
import RecommendationModal from '../components/RecommendationModal'
import './HomePage.css'

/**
 * 홈 페이지 (메인 대시보드)
 * - 스마트홈 기기 제어
 * - 시선 추적 커서 표시
 * - 실시간 시선 위치 기반 dwell time 제어
 * - AI 추천 모달 주기적 표시
 * - 👁️ 0.5초+ 눈깜빡임 감지 → 클릭 인식
 */
function HomePage({ onLogout }) {
    // 연결된 기기 목록
    const [devices, setDevices] = useState([])
    // AI 추천 목록
    const [recommendations, setRecommendations] = useState([])
    // 추천 모달 표시 여부
    const [showRecommendations, setShowRecommendations] = useState(false)
    // 실시간 시선 위치 (x, y)
    const [gazePosition, setGazePosition] = useState({ x: 0, y: 0 })
    // WebSocket 연결 상태
    const [isConnected, setIsConnected] = useState(false)
    // 🔍 시선 인식 가능 여부 (false = 눈이 감겼거나 인식 불가)
    const [calibrated, setCalibrated] = useState(true)
    // 로그인한 사용자명
    const [username, setUsername] = useState('')
    // 👁️ 0.5초 이상 눈깜빡임 감지
    const [prolongedBlink, setProlongedBlink] = useState(false)
    // 👁️ 현재 눈깜빡임 상태 (포인터 고정용)
    const [blink, setBlink] = useState(false)
    // 🔒 글로벌 포인터 고정 상태 (버튼 위 포인터 1.5초 고정)
    const [isPointerLocked, setIsPointerLocked] = useState(false)

    /**
     * 포인터 1.5초 고정 함수
     * - 버튼 클릭 시 호출
     * - 1.5초 동안 hovering 감지 차단
     */
    const lockPointer = (duration = 1500) => {
        setIsPointerLocked(true)
        setTimeout(() => {
            setIsPointerLocked(false)
        }, duration)
    }

    /**
     * 초기화: 사용자명 로드, 기기/추천 로드, WebSocket 연결
     */
    useEffect(() => {
        // localStorage에서 사용자명 로드
        const storedUsername = localStorage.getItem('gazehome_username') || '사용자'
        setUsername(storedUsername)

        loadDevices()
        loadRecommendations()
        connectGazeStream()

        // 30초마다 추천 업데이트 및 모달 표시
        const interval = setInterval(() => {
            loadRecommendations()
            setShowRecommendations(true)
        }, 30000)

        return () => {
            clearInterval(interval)
        }
    }, [])

    /**
     * 스마트홈 기기 목록 로드
     */
    const loadDevices = async () => {
        try {
            const response = await fetch('/api/devices')
            const data = await response.json()
            setDevices(data)
        } catch (error) {
            console.error('기기 로드 실패:', error)
        }
    }

    /**
     * AI 추천 로드
     */
    const loadRecommendations = async () => {
        try {
            const response = await fetch('/api/recommendations')
            const data = await response.json()
            setRecommendations(data)
        } catch (error) {
            console.error('추천 로드 실패:', error)
        }
    }

    /**
     * WebSocket을 통한 시선 스트림 연결
     * - 실시간 시선 위치 수신
     * - 연결 끊김 시 자동 재연결
     */
    const connectGazeStream = () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/gaze`)

        ws.onopen = () => {
            console.log('시선 스트림 연결됨')
            setIsConnected(true)
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)

            // 시선 업데이트 메시지 처리
            if (data.type === 'gaze_update' && data.gaze) {
                setGazePosition({ x: data.gaze[0], y: data.gaze[1] })

                // 👁️ 현재 눈깜빡임 상태 (포인터 고정)
                if (data.blink !== undefined) {
                    setBlink(data.blink)
                }

                // � 시선 인식 가능 여부 (false = 시선 불인식, 포인터 마지막 위치 고정)
                if (data.calibrated !== undefined) {
                    setCalibrated(data.calibrated)
                }

                // �👁️ 1초 이상 눈깜빡임 감지
                if (data.prolonged_blink !== undefined) {
                    setProlongedBlink(data.prolonged_blink)

                    if (data.prolonged_blink) {
                        console.log('[HomePage] 눈깜빡임 1초+ 감지 - 클릭으로 인식!')
                    }
                }
            }
        }

        ws.onerror = (error) => {
            console.error('WebSocket 오류:', error)
            setIsConnected(false)
        }

        ws.onclose = () => {
            console.log('WebSocket 연결 끊김')
            setIsConnected(false)
            // 3초 후 재연결 시도
            setTimeout(connectGazeStream, 3000)
        }
    }

    /**
     * 기기 제어
     * @param {string} deviceId - 기기 ID
     * @param {string} action - 제어 액션 (toggle, on, off 등)
     * @param {Object} params - 추가 파라미터
     */
    const handleDeviceControl = async (deviceId, action, params = {}) => {
        try {
            const response = await fetch(`/api/devices/${deviceId}/control`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, params }),
            })

            const result = await response.json()

            if (result.success) {
                // 제어 성공 시 기기 목록 갱신
                await loadDevices()
            }
        } catch (error) {
            console.error('기기 제어 실패:', error)
        }
    }

    /**
     * 추천 수락 핸들러
     * - 추천된 액션 실행
     * - 사용자 피드백 전송
     */
    const handleRecommendationAccept = async (recommendation) => {
        // 추천 액션 실행
        await handleDeviceControl(
            recommendation.device_id,
            recommendation.action,
            recommendation.params
        )

        // 피드백 전송
        try {
            await fetch('/api/recommendations/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recommendation_id: recommendation.id,
                    accepted: true,
                    rating: 5,
                }),
            })
        } catch (error) {
            console.error('피드백 전송 실패:', error)
        }

        setShowRecommendations(false)
    }

    return (
        <div className="home-page">
            {/* 시선 커서 표시 */}
            <GazeCursor x={gazePosition.x} y={gazePosition.y} visible={isConnected} blink={blink} calibrated={calibrated} />

            {/* 헤더 */}
            <header className="home-header">
                <div className="container">
                    <div className="header-content">
                        {/* 좌측: 로고 및 연결 상태 */}
                        <div className="header-left">
                            <div className="logo">
                                <Eye size={32} />
                                <span>GazeHome</span>
                            </div>
                            <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                                <div className="status-dot"></div>
                                {isConnected ? '시선 추적 중' : '연결 끊김'}
                            </div>
                        </div>

                        {/* 우측: 알림, 사용자 메뉴, 설정, 로그아웃 버튼 */}
                        <div className="header-right">
                            {/* 알림 버튼 */}
                            <button
                                className="notification-button"
                                onClick={() => setShowRecommendations(true)}
                            >
                                <Bell size={20} />
                                {recommendations.length > 0 && (
                                    <span className="notification-badge">{recommendations.length}</span>
                                )}
                            </button>

                            {/* 사용자 메뉴 */}
                            <div className="user-menu">
                                <User size={20} />
                                <span>{username}</span>
                            </div>

                            {/* 설정 버튼 */}
                            <button className="icon-button" onClick={() => window.location.href = '/settings'} title="설정">
                                <Settings size={20} />
                            </button>

                            {/* 로그아웃 버튼 */}
                            <button className="icon-button" onClick={onLogout}>
                                <LogOut size={20} />
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* 메인 콘텐츠 */}
            <main className="home-main">
                <div className="container">
                    {/* 환영 섹션 */}
                    <motion.div
                        className="welcome-section"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <h1>안녕하세요, {username}님! 👋</h1>
                        <p>시선으로 스마트홈을 제어해보세요</p>
                    </motion.div>

                    {/* 기기 그리드 */}
                    <motion.div
                        className="devices-section"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                    >
                        <div className="section-header">
                            <h2>기기 목록</h2>
                            <span className="device-count">{devices.length}개 기기</span>
                        </div>

                        <div className="devices-grid">
                            {devices.map((device, index) => (
                                <motion.div
                                    key={device.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.1 * index }}
                                >
                                    <DeviceCard
                                        device={device}
                                        onControl={handleDeviceControl}
                                        prolongedBlink={prolongedBlink}
                                        isPointerLocked={isPointerLocked}
                                        onPointerEnter={lockPointer}
                                    />
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                </div>
            </main>

            {/* 추천 모달 */}
            <AnimatePresence>
                {showRecommendations && recommendations.length > 0 && (
                    <RecommendationModal
                        recommendations={recommendations}
                        onAccept={handleRecommendationAccept}
                        onClose={() => setShowRecommendations(false)}
                        prolongedBlink={prolongedBlink}
                        isPointerLocked={isPointerLocked}
                        onPointerEnter={lockPointer}
                    />
                )}
            </AnimatePresence>
        </div>
    )
}

export default HomePage
