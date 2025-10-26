import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Eye, Sparkles, AlertCircle } from 'lucide-react'
import './OnboardingPage.css'

/**
 * 온보딩/로그인 페이지
 * - 초기 사용자 입장점
 * - WebSocket으로 시선 추적 연결
 * - 눈 깜빡임(1초 이상)으로 "시작하기" 버튼 자동 클릭
 */
function OnboardingPage({ onLogin }) {
    // 로그인 진행 중 여부
    const [isLoading, setIsLoading] = useState(false)
    // WebSocket 연결 상태
    const [wsConnected, setWsConnected] = useState(false)
    // 눈 깜빡임 감지 상태
    const [isBlinking, setIsBlinking] = useState(false)
    // 눈 깜빡임 시작 시간
    const blinkStartTimeRef = useRef(null)
    // WebSocket 참조
    const wsRef = useRef(null)
    // 버튼 참조 (자동 클릭용)
    const loginButtonRef = useRef(null)

    // 상수
    const PROLONGED_BLINK_DURATION = 1.0  // 1초 이상 눈깜빡임 = 클릭

    /**
     * WebSocket 연결 및 시선 데이터 수신
     */
    useEffect(() => {
        const connectWebSocket = () => {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
                const wsUrl = `${protocol}//${window.location.host}/ws/gaze`

                wsRef.current = new WebSocket(wsUrl)

                wsRef.current.onopen = () => {
                    console.log('✅ WebSocket 연결됨 (시선 추적)')
                    setWsConnected(true)
                }

                wsRef.current.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data)

                        // 👁️ 눈깜빡임 감지 (blink: true/false)
                        if (data.blink !== undefined) {
                            if (data.blink && !isBlinking) {
                                // 눈깜빡임 시작
                                blinkStartTimeRef.current = Date.now()
                                setIsBlinking(true)
                            } else if (!data.blink && isBlinking) {
                                // 눈깜빡임 종료
                                if (blinkStartTimeRef.current) {
                                    const blinkDuration = (Date.now() - blinkStartTimeRef.current) / 1000
                                    console.log(`👁️ 눈깜빡임: ${blinkDuration.toFixed(2)}초`)

                                    // 1초 이상 눈깜빡임 감지 → 버튼 자동 클릭
                                    if (blinkDuration >= PROLONGED_BLINK_DURATION) {
                                        console.log('🔔 1초 이상 눈깜빡임 감지! 로그인 버튼 자동 클릭')
                                        if (loginButtonRef.current && !isLoading) {
                                            loginButtonRef.current.click()
                                        }
                                    }
                                }
                                blinkStartTimeRef.current = null
                                setIsBlinking(false)
                            }
                        }
                    } catch (error) {
                        console.warn('WebSocket 데이터 파싱 오류:', error)
                    }
                }

                wsRef.current.onerror = (error) => {
                    console.error('❌ WebSocket 오류:', error)
                    setWsConnected(false)
                }

                wsRef.current.onclose = () => {
                    console.warn('⚠️ WebSocket 연결 종료')
                    setWsConnected(false)
                }
            } catch (error) {
                console.error('WebSocket 연결 실패:', error)
                setWsConnected(false)
            }
        }

        connectWebSocket()

        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [isLoading, isBlinking])

    /**
     * 로그인 버튼 클릭 핸들러
     */
    const handleLogin = async () => {
        if (isLoading) return

        setIsLoading(true)
        console.log('🔐 로그인 시작...')

        try {
            // 부모 로그인 핸들러 호출 (백엔드 API 호출)
            // 데모 모드: 백엔드에서 고정된 demo_user 사용
            await onLogin()
            console.log('✅ 로그인 성공')
        } catch (error) {
            console.error('❌ 로그인 오류:', error)
            setIsLoading(false)
        }
    }

    return (
        <div className="onboarding-page">
            <div className="onboarding-background">
                {/* 배경 애니메이션 효과 */}
                <div className="gradient-orb orb-1"></div>
                <div className="gradient-orb orb-2"></div>
                <div className="gradient-orb orb-3"></div>
            </div>

            <div className="onboarding-content">
                <motion.div
                    className="onboarding-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    {/* 로고 */}
                    <motion.div
                        className="logo-container"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                    >
                        <div className="logo-icon">
                            <Eye size={48} strokeWidth={2} />
                        </div>
                    </motion.div>

                    {/* 제목 */}
                    <motion.h1
                        className="onboarding-title"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                    >
                        GazeHome
                    </motion.h1>

                    {/* 부제목 */}
                    <motion.p
                        className="onboarding-subtitle"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                    >
                        <Sparkles size={16} className="inline-icon" />
                        시선으로 제어하는 스마트한 공간
                    </motion.p>

                    {/* 로그인 폼 */}
                    <motion.div
                        className="login-form"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                    >
                        <button
                            ref={loginButtonRef}
                            type="button"
                            className="login-button"
                            onClick={handleLogin}
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <span className="loading-spinner"></span>
                                    로그인 중...
                                </>
                            ) : (
                                <>
                                    <Eye size={20} />
                                    시작하기
                                </>
                            )}
                        </button>

                        {/* WebSocket 연결 상태 표시 */}
                        <div className="ws-status">
                            {wsConnected ? (
                                <span className="status-connected">✅ 시선 추적 활성화</span>
                            ) : (
                                <span className="status-connecting">⏳ 시선 추적 연결 중...</span>
                            )}
                        </div>

                        {/* 눈 깜빡임 감지 상태 */}
                        {isBlinking && (
                            <motion.div
                                className="blink-indicator"
                                initial={{ scale: 0.5, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ duration: 0.2 }}
                            >
                                <span className="blink-dot"></span>
                                눈 깜빡임 감지 중...
                            </motion.div>
                        )}
                    </motion.div>

                    {/* 기능 목록 */}
                    <motion.div
                        className="features-list"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                    >
                        <div className="feature-item">
                            <span className="feature-icon">👁️</span>
                            <span>시선 추적 기반 제어</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🏠</span>
                            <span>스마트홈 기기 관리</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🤖</span>
                            <span>AI 추천 시스템</span>
                        </div>
                    </motion.div>
                </motion.div>

                {/* 푸터 */}
                <motion.div
                    className="onboarding-footer"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1 }}
                >
                    <p>Powered by AIRIS</p>
                </motion.div>
            </div>
        </div>
    )
}

export default OnboardingPage
