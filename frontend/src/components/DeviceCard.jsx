import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
    Power, Wind, Sun, Droplets,
    Thermometer, Fan, Lightbulb, Zap
} from 'lucide-react'
import './DeviceCard.css'

/**
 * 기기 타입별 아이콘 매핑 (MongoDB 필드명)
 * 
 * MongoDB device_type:
 * - "air_purifier" → 공기청정기 (Fan)
 * - "dryer" → 건조기 (Zap)
 * - "air_conditioner" → 에어컨 (Wind)
 */
const DEVICE_ICONS = {
    'air_purifier': Fan,      // 공기청정기 (MongoDB)
    'airpurifier': Fan,       // 공기청정기 (Frontend 정규화)
    'dryer': Zap,             // 건조기
    'air_conditioner': Wind,  // 에어컨 (MongoDB)
    'aircon': Wind            // 에어컨 (Frontend 정규화)
}

// 2초 시선 유지 시간 (dwell time)
const DWELL_TIME = 2000

/**
 * 개별 기기 카드 컴포넌트
 * - 기기 상태 표시 (ON/OFF)
 * - 시선 hovering 감지 (dwell time)
 * - 2초 응시 후 자동 토글
 * - 👁️ 0.5초+ 눈깜빡임 감지 → 즉시 토글
 * - 메타데이터 표시 (온도, 습도, 밝기 등)
 * - 🔒 제어 중이면 클릭 불가
 * 
 * @param {Object} device - 기기 정보
 * @param {Function} onControl - 기기 제어 콜백
 * @param {boolean} prolongedBlink - 0.5초 이상 눈깜빡임 감지
 * @param {boolean} isPointerLocked - 전역 포인터 고정 상태
 * @param {Function} onPointerEnter - 포인터 고정 콜백 (버튼 호버 시)
 * @param {boolean} isControlling - 현재 제어 중인지 여부
 */
function DeviceCard({ device, onControl, prolongedBlink, isPointerLocked, onPointerEnter, isControlling = false }) {
    // 현재 시선이 카드 위에 있는지 여부
    const [isHovering, setIsHovering] = useState(false)
    // 시선 유지 진행률 (0-1)
    const [dwellProgress, setDwellProgress] = useState(0)
    // 🔒 클릭 후 포인터 고정 상태
    const [isLocked, setIsLocked] = useState(false)

    const cardRef = useRef(null)
    const hoverStartTimeRef = useRef(null)
    const animationFrameRef = useRef(null)
    const lockTimerRef = useRef(null)

    // ⏱️ 포인터 고정 시간 (ms)
    const LOCK_DURATION = 1500  // 1.5초

    // 이전 prolongedBlink 상태 추적 (상태 변화 감지용)
    const prevBlinkRef = useRef(false)

    /**
     * 👁️ 눈깜빡임 클릭 감지
     * - 카드 위에서 1초 눈깜빡임 → 즉시 토글
     * prolongedBlink가 false → true 전환 감지 (깜빡임 완료)
     */
    useEffect(() => {
        if (isLocked) return

        // 이전 상태: false, 현재 상태: true (깜빡임 END)
        if (!prevBlinkRef.current && prolongedBlink) {
            prevBlinkRef.current = prolongedBlink

            // 카드의 화면상 위치 확인
            if (!cardRef.current) return

            const rect = cardRef.current.getBoundingClientRect()
            const gazeCursor = document.querySelector('.gaze-cursor')

            if (!gazeCursor) return

            // 시선 커서 위치
            const cursorRect = gazeCursor.getBoundingClientRect()
            const cursorX = cursorRect.left + cursorRect.width / 2
            const cursorY = cursorRect.top + cursorRect.height / 2

            // 시선이 카드 내부에 있는지 확인
            const isInside =
                cursorX >= rect.left &&
                cursorX <= rect.right &&
                cursorY >= rect.top &&
                cursorY <= rect.bottom

            if (isInside) {
                // 👁️ 카드 위에서 1초 깜빡임 감지 → 즉시 토글
                console.log(`[DeviceCard] 👁️ 1초 깜빡임 클릭 감지: ${device.name}`)
                handleToggle()

                // 🔒 1.5초 포인터 고정
                setIsLocked(true)

                if (lockTimerRef.current) {
                    clearTimeout(lockTimerRef.current)
                }

                lockTimerRef.current = setTimeout(() => {
                    console.log(`[DeviceCard] 포인터 고정 해제`)
                    setIsLocked(false)
                }, LOCK_DURATION)

                // 상태 초기화
                setIsHovering(false)
                setDwellProgress(0)
                hoverStartTimeRef.current = null
            }
        } else {
            // 상태 업데이트
            prevBlinkRef.current = prolongedBlink
        }
    }, [prolongedBlink, isLocked, device.name])

    /**
     * 시선 위치 기반 hovering 감지
     * - requestAnimationFrame으로 지속적으로 시선 커서 위치 추적
     * - 카드와 시선 커서의 충돌 검사
     * - 2초 이상 응시 시 기기 토글
     * - 🔒 클릭 후 1.5초간 타이머 일시 정지 (고정)
     */
    useEffect(() => {
        const checkHover = () => {
            if (!cardRef.current) return

            // 카드의 화면상 위치 가져오기
            const rect = cardRef.current.getBoundingClientRect()
            // 시선 커서 요소 찾기
            const gazeCursor = document.querySelector('.gaze-cursor')

            if (!gazeCursor) {
                animationFrameRef.current = requestAnimationFrame(checkHover)
                return
            }

            // 시선 커서의 화면상 위치 계산
            const cursorRect = gazeCursor.getBoundingClientRect()
            const cursorX = cursorRect.left + cursorRect.width / 2
            const cursorY = cursorRect.top + cursorRect.height / 2

            // 시선 커서가 카드 내부에 있는지 확인
            const isInside =
                cursorX >= rect.left &&
                cursorX <= rect.right &&
                cursorY >= rect.top &&
                cursorY <= rect.bottom

            if (isInside) {
                // 포인터 고정이 해제되고 새로운 응시를 시작해야 할 때
                if (!isLocked && !isHovering) {
                    setIsHovering(true)
                    hoverStartTimeRef.current = Date.now()
                    console.log(`[DeviceCard] 시선 감지: ${device.name}`)
                }

                // 경과 시간 계산 (포인터 고정 중에는 타이머 멈춤)
                if (isHovering && hoverStartTimeRef.current && !isLocked) {
                    const elapsed = Date.now() - hoverStartTimeRef.current
                    const progress = Math.min(elapsed / DWELL_TIME, 1)
                    setDwellProgress(progress)

                    if (progress >= 1) {
                        // 2초 완료: 기기 토글
                        console.log(`[DeviceCard] 시선 유지 완료! ${device.name} 토글`)
                        handleToggle()

                        // 🔒 1.5초 포인터 고정 시작
                        console.log(`[DeviceCard] 포인터 고정 시작 (${LOCK_DURATION}ms)`)
                        setIsLocked(true)
                        setIsHovering(false)
                        setDwellProgress(0)
                        hoverStartTimeRef.current = null

                        // 기존 타이머 정리
                        if (lockTimerRef.current) {
                            clearTimeout(lockTimerRef.current)
                        }

                        // 1.5초 후 포인터 고정 해제
                        lockTimerRef.current = setTimeout(() => {
                            console.log(`[DeviceCard] 포인터 고정 해제 - 새로운 응시 대기`)
                            setIsLocked(false)
                            // isHovering, dwellProgress, hoverStartTimeRef는 자동으로 재설정됨
                        }, LOCK_DURATION)
                    }
                }
            } else {
                // 포인터가 카드 밖으로 나감
                if (isHovering) {
                    console.log(`[DeviceCard] 시선 벗어남: ${device.name} (진행률: ${(dwellProgress * 100).toFixed(0)}%)`)
                    setIsHovering(false)
                    setDwellProgress(0)
                    hoverStartTimeRef.current = null
                }
            }

            animationFrameRef.current = requestAnimationFrame(checkHover)
        }

        animationFrameRef.current = requestAnimationFrame(checkHover)

        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current)
            }
            if (lockTimerRef.current) {
                clearTimeout(lockTimerRef.current)
            }
        }
    }, [isHovering, dwellProgress, device.name, isLocked])

    /**
     * 기기 토글 핸들러 (시선 클릭 시 AI 서버로 요청)
     * 
     * 1. POST /api/devices/{device_id}/click 호출 (Backend)
     * 2. Backend가 기기 제어 및 AI 추천 생성
     * 3. 변환된 액션과 메시지 수신
     * 4. 결과를 custom event로 HomePage에 전달
     * 5. HomePage에서 상태 업데이트 및 모달 표시
     */
    const handleToggle = async () => {
        try {
            console.log(`[DeviceCard] 🎯 기기 제어 시작: ${device.name}`)

            // Backend의 POST /api/devices/{device_id}/click 호출
            // 요청 형식: { "user_id": "...", "action": "toggle" }
            // 응답 형식: 
            // {
            //   "success": true,
            //   "device_id": "...",
            //   "device_name": "...",
            //   "device_type": "...",
            //   "action": "aircon_off",    (변환된 액션)
            //   "message": "[GATEWAY] 스마트 기기(에어컨) 제어 완료",
            //   "result": {}
            // }
            const response = await fetch(`/api/devices/${device.device_id || device.id}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: localStorage.getItem('gazehome_user_id') || 'default_user',
                    action: 'toggle'  // Backend에서 변환됨
                })
            })

            const result = await response.json()

            console.log(`[DeviceCard] 💬 Backend 응답:`, result)

            if (result.success) {
                console.log(`[DeviceCard] ✅ 기기 제어 완료: ${result.message}`)
                console.log(`[DeviceCard] 📤 변환된 액션: ${result.action}`)

                // ✅ HomePage에서 처리하기 위해 custom event 발생
                // action 필드를 포함하여 HomePage에서 상태 업데이트 가능하도록 함
                const event = new CustomEvent('device-clicked', {
                    detail: {
                        device_id: device.device_id || device.id,
                        device_name: device.device_name || device.name,
                        recommendation: {
                            action: result.action,          // 변환된 액션 포함
                            message: result.message,
                            reason: result.message,
                            success: true
                        }
                    }
                })
                window.dispatchEvent(event)

                console.log(`[DeviceCard] 📢 HomePage에 custom event 전송 (action: ${result.action})`)
            } else {
                console.error(`[DeviceCard] ❌ 기기 제어 실패:`, result)

                // 실패 시에도 event 전송 (상태 표시용)
                const event = new CustomEvent('device-clicked', {
                    detail: {
                        device_id: device.device_id || device.id,
                        device_name: device.device_name || device.name,
                        recommendation: {
                            action: 'error',
                            message: result.message || '기기 제어 실패',
                            success: false
                        }
                    }
                })
                window.dispatchEvent(event)
            }
        } catch (error) {
            console.error(`[DeviceCard] ❌ 클릭 처리 오류:`, error)
        }
    }

    // 기기 타입에 맞는 아이콘 가져오기
    const Icon = DEVICE_ICONS[device.type] || Power
    // 기기 상태 (on/off)
    const isOn = device.state === 'on'

    return (
        <motion.div
            ref={cardRef}
            className={`device-card ${isOn ? 'on' : 'off'} ${isHovering ? 'hovering' : ''}`}
            whileHover={{ y: -4 }}
            transition={{ duration: 0.2 }}
        >
            {/* 시선 hovering 진행 상황 표시 (원형 진행 바) */}
            {isHovering && (
                <svg className="hover-progress-ring" viewBox="0 0 100 100">
                    <circle
                        cx="50"
                        cy="50"
                        r="48"
                        fill="none"
                        stroke="rgba(102, 126, 234, 0.2)"
                        strokeWidth="4"
                    />
                    {/* 진행 상황을 나타내는 호 */}
                    <motion.circle
                        cx="50"
                        cy="50"
                        r="48"
                        fill="none"
                        stroke="var(--primary)"
                        strokeWidth="4"
                        strokeLinecap="round"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: dwellProgress }}
                        style={{
                            transform: 'rotate(-90deg)',
                            transformOrigin: '50% 50%',
                        }}
                    />
                </svg>
            )}

            {/* 카드 헤더: 아이콘 및 상태 */}
            <div className="device-header">
                <div className={`device-icon ${isOn ? 'active' : ''}`}>
                    <Icon size={24} />
                </div>
                <div className={`device-status ${isOn ? 'on' : 'off'}`}>
                    {isOn ? 'ON' : 'OFF'}
                </div>
            </div>

            {/* 기기 정보: 이름, 위치 */}
            <div className="device-info">
                <h3 className="device-name">{device.name}</h3>
                <p className="device-room">{device.room}</p>
            </div>

            {/* 기기 메타데이터: 온도, 습도, 밝기 등 */}
            <div className="device-metadata">
                {device.metadata.current_temp && (
                    <div className="metadata-item">
                        <Thermometer size={16} />
                        <span>{device.metadata.current_temp}°C</span>
                    </div>
                )}
                {device.metadata.target_temp && (
                    <div className="metadata-item">
                        <Sun size={16} />
                        <span>목표: {device.metadata.target_temp}°C</span>
                    </div>
                )}
                {device.metadata.mode && (
                    <div className="metadata-item">
                        <Wind size={16} />
                        <span>{device.metadata.mode}</span>
                    </div>
                )}
                {device.metadata.brightness !== undefined && (
                    <div className="metadata-item">
                        <Lightbulb size={16} />
                        <span>{device.metadata.brightness}%</span>
                    </div>
                )}
                {device.metadata.pm25 !== undefined && (
                    <div className="metadata-item">
                        <Droplets size={16} />
                        <span>PM2.5: {device.metadata.pm25}μg/m³</span>
                    </div>
                )}
                {device.metadata.time_remaining !== undefined && (
                    <div className="metadata-item">
                        <Sun size={16} />
                        <span>남은시간: {device.metadata.time_remaining}분</span>
                    </div>
                )}
                {device.metadata.temperature !== undefined && (
                    <div className="metadata-item">
                        <Thermometer size={16} />
                        <span>{device.metadata.temperature}°C</span>
                    </div>
                )}
            </div>

            {/* 제어 버튼 */}
            <div className="device-controls">
                <button
                    className={`control-button ${isOn ? 'on' : 'off'}`}
                    onClick={handleToggle}
                    onMouseEnter={() => {
                        if (onPointerEnter) {
                            console.log(`[DeviceCard Button] 포인터 버튼 진입 - 1.5초 고정`)
                            onPointerEnter(1500)
                        }
                    }}
                >
                    <Power size={18} />
                    {isOn ? '끄기' : '켜기'}
                </button>
            </div>

            {/* 시선 유지 표시기 */}
            {isHovering && (
                <div className="dwell-indicator">
                    <span>2초간 응시하여 토글</span>
                    <div className="dwell-bar">
                        <motion.div
                            className="dwell-fill"
                            initial={{ width: 0 }}
                            animate={{ width: `${dwellProgress * 100}%` }}
                        />
                    </div>
                </div>
            )}
        </motion.div>
    )
}

export default DeviceCard
