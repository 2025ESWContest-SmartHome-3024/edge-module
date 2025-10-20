import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
    Power, Wind, Sun, Droplets,
    Thermometer, Fan, Lightbulb
} from 'lucide-react'
import './DeviceCard.css'

/**
 * 기기 타입별 아이콘 매핑
 */
const DEVICE_ICONS = {
    air_conditioner: Wind,
    air_purifier: Fan,
    light: Lightbulb,
    thermostat: Thermometer,
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
 * 
 * @param {Object} device - 기기 정보
 * @param {Function} onControl - 기기 제어 콜백
 * @param {boolean} prolongedBlink - 0.5초 이상 눈깜빡임 감지
 */
function DeviceCard({ device, onControl, prolongedBlink }) {
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

    /**
     * 👁️ 눈깜빡임 클릭 감지
     * - 카드 위에서 0.5초+ 눈깜빡임 → 즉시 토글
     */
    useEffect(() => {
        if (!prolongedBlink || isLocked) return

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
            // 👁️ 카드 위에서 눈깜빡임 감지 → 즉시 토글
            console.log(`[DeviceCard] 👁️ 깜빡임 클릭 감지: ${device.name}`)
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
                if (!isHovering) {
                    // hovering 시작 (포인터 고정 중이면 시작하지 않음)
                    if (!isLocked) {
                        setIsHovering(true)
                        hoverStartTimeRef.current = Date.now()
                        console.log(`[DeviceCard] 시선 감지: ${device.name}`)
                    }
                }

                // 경과 시간 계산 (0-1 범위의 진행률)
                // 🔒 포인터 고정 중이면 타이머 멈춤 (진행률 유지)
                if (!isLocked && hoverStartTimeRef.current) {
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

                        // 기존 타이머 정리
                        if (lockTimerRef.current) {
                            clearTimeout(lockTimerRef.current)
                        }

                        // 1.5초 후 포인터 고정 해제 + 상태 초기화
                        lockTimerRef.current = setTimeout(() => {
                            console.log(`[DeviceCard] 포인터 고정 해제 - 새로운 응시 대기`)
                            setIsLocked(false)
                            setIsHovering(false)
                            setDwellProgress(0)
                            hoverStartTimeRef.current = null
                        }, LOCK_DURATION)

                        // 즉시 hovering 상태만 리셋 (진행 바 UI 업데이트)
                        setIsHovering(false)
                        setDwellProgress(0)
                        hoverStartTimeRef.current = null
                    }
                }
            } else {
                if (isHovering) {
                    // hovering 종료
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
     * 기기 토글 핸들러
     */
    const handleToggle = () => {
        onControl(device.id, 'toggle')
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
            </div>

            {/* 제어 버튼 */}
            <div className="device-controls">
                <button
                    className={`control-button ${isOn ? 'on' : 'off'}`}
                    onClick={handleToggle}
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
