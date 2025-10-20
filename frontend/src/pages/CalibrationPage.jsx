import { useState, useEffect, useRef } from 'react'
import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, CheckCircle, AlertCircle } from 'lucide-react'
import './CalibrationPage.css'

/**
 * 시선 보정 페이지
 * - 9포인트 웹 기반 보정
 * - 실시간 얼굴 인식 및 특징점 수집
 * - 자동 모델 학습
 * - 웹 UI 기반 Kalman 필터 파인튜닝
 * 
 * @param {Function} onComplete - 보정 완료 콜백
 */
function CalibrationPage({ onComplete }) {
    // 보정 상태 (init, ready, calibrating, training, tuning, completed, error)
    const [status, setStatus] = useState('init')
    // 백엔드 세션 ID
    const [sessionId, setSessionId] = useState(null)
    // 보정 포인트 배열
    const [points, setPoints] = useState([])
    // 현재 포인트 인덱스
    const [currentPointIndex, setCurrentPointIndex] = useState(0)
    // 수집된 샘플 개수
    const [samplesCollected, setSamplesCollected] = useState(0)
    // 현재 단계 (waiting, pulsing, capturing)
    const [phase, setPhase] = useState('waiting')
    // 얼굴 인식 여부
    const [hasFace, setHasFace] = useState(false)
    // 사용자 메시지
    const [message, setMessage] = useState('보정을 시작하려면 준비 버튼을 누르세요')

    // WebSocket 참조
    const wsRef = useRef(null)
    const canvasRef = useRef(null)
    const captureTimerRef = useRef(null)
    // Ref를 사용해 stale closure 방지
    const phaseRef = useRef('waiting')
    const sessionIdRef = useRef(null)
    const currentPointIndexRef = useRef(0)
    const pointsRef = useRef([])
    // 로컬 샘플 버퍼
    const samplesBufferRef = useRef({})

    const samplesPerPoint = 25
    // 각 포인트당 캡처 시간 (초)
    const captureTimeSeconds = 2.5

    /**
     * 클린업: WebSocket 종료, 타이머 정리
     */
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
            if (captureTimerRef.current) {
                clearTimeout(captureTimerRef.current)
            }
        }
    }, [])

    /**
     * 보정 세션 시작
     * - 백엔드에서 9포인트 보정 시작
     * - WebSocket 연결
     * - 첫 번째 포인트에서 펄스 애니메이션 시작
     */
    const startCalibration = async () => {
        try {
            setStatus('ready')
            setMessage('보정 세션을 시작하는 중...')

            // 백엔드에서 보정 세션 시작
            const response = await fetch('/api/calibration/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    method: 'nine_point',
                    screen_width: window.screen.width,
                    screen_height: window.screen.height,
                }),
            })

            if (!response.ok) {
                const errorText = await response.text()
                throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`)
            }

            const data = await response.json()
            setSessionId(data.session_id)
            sessionIdRef.current = data.session_id
            setPoints(data.points)
            pointsRef.current = data.points

            console.log('[CalibrationPage] 보정 시작 - 포인트:', data.points)

            // 특징 스트림 WebSocket 연결
            connectWebSocket()

            setStatus('calibrating')
            setPhase('pulsing')
            phaseRef.current = 'pulsing'
            setCurrentPointIndex(0)
            currentPointIndexRef.current = 0
            setMessage('첫 번째 점을 응시하세요')

            // 펄스 애니메이션 시작
            startPulseAnimation()

        } catch (error) {
            console.error('보정 시작 실패:', error)
            setStatus('error')
            setMessage('보정 시작 실패: ' + error.message)
        }
    }

    /**
     * WebSocket을 통한 특징 스트림 연결
     * - 실시간 얼굴 인식 및 특징점 수신
     * - 캡처 단계에서 샘플 수집
     */
    const connectWebSocket = () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/features`)

        ws.onopen = () => {
            console.log('[CalibrationPage] WebSocket 연결됨')
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)

            console.log('[CalibrationPage] WebSocket 메시지:', data.type, {
                has_face: data.has_face,
                blink: data.blink,
                has_features: !!data.features,
                phase: phaseRef.current
            })

            if (data.type === 'features') {
                // 얼굴 인식 상태 업데이트 (깜빡임 제외)
                setHasFace(data.has_face && !data.blink)

                // 캡처 단계에서만 샘플 수집
                if (phaseRef.current === 'capturing' && data.has_face && !data.blink && data.features) {
                    console.log('[CalibrationPage] 샘플 수집 중...')
                    collectSample(data.features)
                }
            }
        }

        ws.onerror = (error) => {
            console.error('[CalibrationPage] WebSocket 오류:', error)
        }

        ws.onclose = () => {
            console.log('[CalibrationPage] WebSocket 연결 끊김')
        }

        wsRef.current = ws
    }

    /**
     * 펄스 애니메이션 시작
     * - 1초 펄스 후 캡처 단계 시작
     * - 캡처 시간 후 자동으로 다음 포인트로 이동
     */
    const startPulseAnimation = () => {
        setPhase('pulsing')
        phaseRef.current = 'pulsing'
        setSamplesCollected(0)

        // 1초 펄스, 그 후 캡처 시작
        setTimeout(() => {
            setPhase('capturing')
            phaseRef.current = 'capturing'

            // 캡처 시간 후 자동으로 다음 포인트로 이동
            captureTimerRef.current = setTimeout(() => {
                moveToNextPoint()
            }, captureTimeSeconds * 1000)
        }, 1000)
    }

    /**
     * 특징점으로부터 샘플 수집
     * @param {Array} features - 얼굴 특징점
     */
    const collectSample = (features) => {
        const idx = currentPointIndexRef.current
        const pts = pointsRef.current

        if (phaseRef.current !== 'capturing' || !pts[idx]) {
            console.log('[CalibrationPage] 샘플 수집 불가:', {
                phase: phaseRef.current,
                hasPoint: !!pts[idx],
                idx: idx,
                totalPoints: pts.length
            })
            return
        }

        const currentPoint = pts[idx]

        // 로컬 버퍼에 저장
        if (!samplesBufferRef.current[idx]) {
            samplesBufferRef.current[idx] = []
        }

        // 포인트당 샘플 수 제한
        if (samplesBufferRef.current[idx].length >= samplesPerPoint) {
            return
        }

        samplesBufferRef.current[idx].push({
            features: features,
            point_x: currentPoint.x,
            point_y: currentPoint.y,
        })

        const count = samplesBufferRef.current[idx].length
        console.log(`[CalibrationPage] 샘플 ${count}개 수집 (포인트 ${idx})`)

        // UI 카운터 업데이트
        setSamplesCollected(count)
    }

    /**
     * 다음 포인트로 이동
     * - 현재 포인트의 샘플들을 백엔드에 전송
     * - 튜닝 모드 또는 정상 모드 처리
     */
    const moveToNextPoint = async () => {
        // 즉시 샘플 수집 중지
        setPhase('moving')
        phaseRef.current = 'moving'

        // 기존 타이머 정리
        if (captureTimerRef.current) {
            clearTimeout(captureTimerRef.current)
            captureTimerRef.current = null
        }

        const sid = sessionIdRef.current
        const idx = currentPointIndexRef.current

        // 튜닝 모드 확인 (세션 ID 없음)
        if (!sid || status === 'tuning') {
            // 튜닝 모드 - 로컬에서만 포인트 이동
            const samples = samplesBufferRef.current[idx] || []
            console.log(`[Tuning] 포인트 ${idx}에서 ${samples.length}개 샘플 수집`)

            const newIdx = idx + 1
            if (newIdx < pointsRef.current.length) {
                // 다음 튜닝 포인트로 이동
                setCurrentPointIndex(newIdx)
                currentPointIndexRef.current = newIdx
                setSamplesCollected(0)
                startPulseAnimation()
                setMessage(`파인튜닝: 포인트 ${newIdx + 1}/3 - 응시하세요`)
            } else {
                // 튜닝 완료 - 분산 계산 및 백엔드에 전송
                console.log('[CalibrationPage] Kalman 튜닝 데이터 수집 완료')
                await computeAndApplyKalmanVariance()
                finishCalibration()
            }
            return
        }

        // 정상 보정 모드
        if (!sid) {
            console.error('세션 ID 없음')
            return
        }

        // 이 포인트의 버퍼링된 샘플들 전송
        const samples = samplesBufferRef.current[idx] || []
        console.log(`포인트 ${idx}에서 ${samples.length}개 샘플 전송`)

        if (samples.length < 3) {
            console.warn(`포인트 ${idx}에서 ${samples.length}개 샘플만 수집됨 - 재시도...`)
            // 샘플이 부족하면 더 기다림
            captureTimerRef.current = setTimeout(() => {
                moveToNextPoint()
            }, 1000)
            return
        }

        // 모든 샘플 한 번에 전송
        try {
            for (const sample of samples) {
                const response = await fetch('/api/calibration/collect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sid,
                        features: Array.from(sample.features),  // numpy 배열을 JS 배열로 변환
                        point_x: sample.point_x,
                        point_y: sample.point_y,
                    }),
                })

                if (!response.ok) {
                    const error = await response.json()
                    console.warn(`[CalibrationPage] 샘플 전송 실패: ${response.status} - ${error.detail}`)
                }
            }
        } catch (error) {
            console.error('샘플 전송 실패:', error)
        }

        try {
            const response = await fetch(`/api/calibration/next-point`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sid
                }),
            })

            const data = await response.json()

            if (data.has_next) {
                const newIdx = idx + 1
                setCurrentPointIndex(newIdx)
                currentPointIndexRef.current = newIdx
                setSamplesCollected(0)
                startPulseAnimation()
                setMessage(`포인트 ${newIdx + 1} / ${pointsRef.current.length}`)
            } else {
                // 모든 포인트 수집 완료
                if (status === 'tuning') {
                    // 튜닝 완료
                    console.log('[CalibrationPage] Kalman 튜닝 완료')
                    finishCalibration()
                } else {
                    // 정상 보정 완료, 학습으로 이동
                    completeCalibration()
                }
            }

        } catch (error) {
            console.error('다음 포인트 이동 실패:', error)
        }
    }

    /**
     * 보정 완료: 모델 학습 및 Kalman 튜닝 시작
     */
    const completeCalibration = async () => {
        const sid = sessionIdRef.current

        if (!sid) {
            console.error('완료 시 세션 ID 없음')
            return
        }

        try {
            setStatus('training')
            setMessage('모델 학습 중...')

            // localStorage에서 사용자명 가져오기
            const username = localStorage.getItem('gazehome_username') || 'default'

            const response = await fetch('/api/calibration/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sid,
                    username: username,
                }),
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(`HTTP ${response.status}: ${errorData.detail || '알 수 없는 오류'}`)
            }

            const result = await response.json()

            if (result.success) {
                // 라즈베리파이 최적화: Kalman 튜닝 건너뜀 (NoOp 필터 사용)
                // Kalman 필터 튜닝은 CPU 부하가 높으므로 비활성화
                console.log('[CalibrationPage] Kalman 튜닝 건너뜀 (NoOp 필터 사용)')
                finishCalibration()

            } else {
                setStatus('error')
                setMessage(`보정 실패: ${result.message || '알 수 없는 오류'}`)
            }

        } catch (error) {
            console.error('보정 완료 실패:', error)
            setStatus('error')
            setMessage(`보정 실패: ${error.message || '알 수 없는 오류'}`)
        }
    }

    /**
     * Kalman 필터 파인튜닝 시작
     * - 3개의 튜닝 포인트 생성 (상단 중앙, 좌측 하단, 우측 하단)
     * - 각 포인트에서 특징점 샘플 수집
     * - 분산 계산 및 Kalman 필터 업데이트
     */
    const startKalmanTuning = async () => {
        try {
            console.log('[CalibrationPage] 웹 UI에서 Kalman 튜닝 시작...')

            // 3개 튜닝 포인트 생성
            const screenWidth = window.screen.width
            const screenHeight = window.screen.height

            const tuningPoints = [
                { x: screenWidth / 2, y: screenHeight / 4, index: 0, total: 3 },        // 상단 중앙
                { x: screenWidth / 4, y: 3 * screenHeight / 4, index: 1, total: 3 },    // 좌측 하단
                { x: 3 * screenWidth / 4, y: 3 * screenHeight / 4, index: 2, total: 3 } // 우측 하단
            ]

            console.log('[CalibrationPage] 튜닝 포인트:', tuningPoints)

            setPoints(tuningPoints)
            pointsRef.current = tuningPoints
            setCurrentPointIndex(0)
            currentPointIndexRef.current = 0
            setSamplesCollected(0)
            samplesBufferRef.current = {}

            // 첫 번째 튜닝 포인트에서 시작
            startPulseAnimation()
            setMessage(`파인튜닝: 포인트 1/3 - 응시하세요`)

        } catch (error) {
            console.error('[CalibrationPage] Kalman 튜닝 오류:', error)
            // 튜닝 건너뛰고 완료로 이동
            finishCalibration()
        }
    }

    /**
     * Kalman 분산 계산 및 적용
     * - 튜닝 샘플들로부터 X, Y 분산 계산
     * - 백엔드에 분산 값 전송하여 Kalman 필터 업데이트
     */
    const computeAndApplyKalmanVariance = async () => {
        try {
            // 튜닝 샘플들로부터 모든 시선 위치 수집
            const allGazePositions = []

            for (let i = 0; i < pointsRef.current.length; i++) {
                const samples = samplesBufferRef.current[i] || []
                samples.forEach(sample => {
                    if (sample.point_x && sample.point_y) {
                        allGazePositions.push([sample.point_x, sample.point_y])
                    }
                })
            }

            console.log(`[Kalman 튜닝] ${allGazePositions.length}개 시선 위치 수집`)

            if (allGazePositions.length < 2) {
                console.warn('[Kalman 튜닝] 분산 계산을 위한 데이터 부족')
                return
            }

            // 분산 계산
            const xValues = allGazePositions.map(pos => pos[0])
            const yValues = allGazePositions.map(pos => pos[1])

            const meanX = xValues.reduce((a, b) => a + b, 0) / xValues.length
            const meanY = yValues.reduce((a, b) => a + b, 0) / yValues.length

            const varianceX = xValues.reduce((sum, val) => sum + Math.pow(val - meanX, 2), 0) / xValues.length
            const varianceY = yValues.reduce((sum, val) => sum + Math.pow(val - meanY, 2), 0) / yValues.length

            console.log(`[Kalman 튜닝] 분산 - X: ${varianceX.toFixed(2)}, Y: ${varianceY.toFixed(2)}`)

            // 백엔드에 분산 값 전송
            await fetch('/api/calibration/update-kalman-variance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    variance_x: Math.max(varianceX, 1e-4),
                    variance_y: Math.max(varianceY, 1e-4)
                }),
            })

            console.log('[Kalman 튜닝] Kalman 필터에 분산 적용됨')

        } catch (error) {
            console.error('[Kalman 튜닝] 분산 계산 오류:', error)
        }
    }

    /**
     * 보정 완료
     * - WebSocket 종료
     * - 2초 후 홈으로 이동
     */
    const finishCalibration = () => {
        setStatus('completed')
        setMessage('보정 완료!')

        // WebSocket 종료
        if (wsRef.current) {
            wsRef.current.close()
        }

        // 2초 후 홈으로 이동
        setTimeout(() => {
            onComplete()
        }, 2000)
    }

    const currentPoint = points[currentPointIndex]

    return (
        <div className="calibration-page">
            <AnimatePresence mode="wait">
                {/* 초기 상태: 보정 안내 */}
                {status === 'init' && (
                    <motion.div
                        className="calibration-intro"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <div className="intro-content">
                            <div className="intro-icon">
                                <Eye size={64} />
                            </div>
                            <h1>시선 보정</h1>
                            <p>정확한 시선 추적을 위해 보정이 필요합니다.</p>
                            <ul className="calibration-steps">
                                <li>화면에 표시되는 9개의 점을 응시합니다</li>
                                <li>각 점마다 2-3초간 응시해주세요</li>
                                <li>얼굴을 움직이지 마세요</li>
                                <li>깜빡임은 자연스럽게 해도 됩니다</li>
                            </ul>
                            <button className="start-button" onClick={startCalibration}>
                                <Eye size={20} />
                                보정 시작
                            </button>
                        </div>
                    </motion.div>
                )}

                {/* 보정 중: 포인트 및 진행 상황 표시 */}
                {(status === 'calibrating' || status === 'ready') && currentPoint && (
                    <motion.div
                        className="calibration-canvas"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        {/* 보정 포인트 */}
                        <CalibrationPoint
                            x={currentPoint.x}
                            y={currentPoint.y}
                            phase={phase}
                            progress={samplesCollected / samplesPerPoint}
                            hasFace={hasFace}
                        />

                        {/* 상태 바 */}
                        <div className="calibration-status-bar">
                            <div className="status-info">
                                <div className={`face-indicator ${hasFace ? 'active' : ''}`}>
                                    {hasFace ? '얼굴 인식됨' : '얼굴을 인식하는 중...'}
                                </div>
                                <div className="point-counter">
                                    포인트 {currentPointIndex + 1} / {points.length}
                                </div>
                            </div>
                            <div className="progress-bar">
                                <motion.div
                                    className="progress-fill"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${(samplesCollected / samplesPerPoint) * 100}%` }}
                                />
                            </div>
                            <div className="message">{message}</div>
                        </div>
                    </motion.div>
                )}

                {/* 학습 중 */}
                {status === 'training' && (
                    <motion.div
                        className="calibration-status"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <div className="status-icon">
                            <div className="loading-spinner"></div>
                        </div>
                        <h2>모델 학습 중...</h2>
                        <p>잠시만 기다려주세요</p>
                    </motion.div>
                )}

                {/* 보정 완료 */}
                {status === 'completed' && (
                    <motion.div
                        className="calibration-status success"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <motion.div
                            className="status-icon"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                        >
                            <CheckCircle size={64} />
                        </motion.div>
                        <h2>보정 완료!</h2>
                        <p>이제 시선 추적을 사용할 수 있습니다</p>
                    </motion.div>
                )}

                {/* 보정 실패 */}
                {status === 'error' && (
                    <motion.div
                        className="calibration-status error"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <div className="status-icon">
                            <AlertCircle size={64} />
                        </div>
                        <h2>보정 실패</h2>
                        <p>{message}</p>
                        <button className="retry-button" onClick={startCalibration}>
                            다시 시도
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

/**
 * 보정 포인트 컴포넌트
 * - 펄싱 원형 애니메이션
 * - 캡처 단계에서 진행 상황 표시
 * - 얼굴 인식 상태 시각적 피드백
 */
function CalibrationPoint({ x, y, phase, progress, hasFace }) {
    // 기본 반경
    const baseRadius = 20
    // 펄싱 단계에서는 반경이 변함
    const pulseRadius = phase === 'pulsing' ? 15 + 15 * Math.abs(Math.sin(Date.now() / 200)) : baseRadius

    // 캡처 진행률 (시간 기반)
    const [captureProgress, setCaptureProgress] = React.useState(0)

    /**
     * 캡처 단계에서 진행률 애니메이션
     */
    React.useEffect(() => {
        if (phase === 'capturing') {
            const startTime = Date.now()
            const duration = 1000 // 1초

            const interval = setInterval(() => {
                const elapsed = Date.now() - startTime
                const prog = Math.min(elapsed / duration, 1.0)
                setCaptureProgress(prog)

                if (prog >= 1.0) {
                    clearInterval(interval)
                }
            }, 16) // ~60fps

            return () => clearInterval(interval)
        } else {
            setCaptureProgress(0)
        }
    }, [phase])

    return (
        <div
            className="calibration-point-container"
            style={{
                left: x,
                top: y,
                transform: 'translate(-50%, -50%)'  // 포인트 중심에 정렬
            }}
        >
            {/* 펄싱 원 */}
            <motion.div
                className={`calibration-circle ${hasFace ? 'has-face' : ''}`}
                animate={{
                    width: pulseRadius * 2,
                    height: pulseRadius * 2,
                }}
                transition={{ duration: 0.1 }}
            />

            {/* 진행 상황 링 */}
            {phase === 'capturing' && (
                <svg className="progress-ring" width="100" height="100">
                    <circle
                        cx="50"
                        cy="50"
                        r="45"
                        fill="none"
                        stroke="rgba(255, 255, 255, 0.3)"
                        strokeWidth="4"
                    />
                    <motion.circle
                        cx="50"
                        cy="50"
                        r="45"
                        fill="none"
                        stroke="white"
                        strokeWidth="4"
                        strokeLinecap="round"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: captureProgress }}
                        style={{
                            transform: 'rotate(-90deg)',
                            transformOrigin: '50% 50%',
                        }}
                    />
                </svg>
            )}
        </div>
    )
}

export default CalibrationPage
