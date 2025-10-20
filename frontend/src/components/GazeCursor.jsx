import { motion } from 'framer-motion'
import { useEffect, useRef } from 'react'
import './GazeCursor.css'

/**
 * 시선 커서 컴포넌트
 * - WebSocket으로부터 받은 시선 위치를 실시간으로 표시
 * - Spring 애니메이션으로 부드러운 움직임 구현
 * - 👁️ 눈깜빡임 또는 시선 인식 불가 시 포인터 마지막 위치에 고정
 * 
 * @param {number} x - 화면 X 좌표
 * @param {number} y - 화면 Y 좌표
 * @param {boolean} visible - 커서 표시 여부
 * @param {boolean} blink - 눈깜빡임 여부 (true = 눈 감음, 포인터 고정)
 * @param {boolean} calibrated - 시선 인식 가능 여부 (false = 인식 불가, 포인터 고정)
 */
function GazeCursor({ x, y, visible, blink = false, calibrated = true }) {
    // 마지막 유효한 시선 위치 (눈깜빡임 또는 시선 인식 불가일 때 사용)
    const lastValidPosRef = useRef({ x: 0, y: 0 })

    // 유효한 시선 위치가 들어오면 기록
    useEffect(() => {
        // calibrated=true AND blink=false일 때만 유효한 위치로 취급
        if (calibrated && !blink && x > 0 && y > 0) {
            lastValidPosRef.current = { x, y }
        }
    }, [x, y, calibrated, blink])

    if (!visible) return null

    // 🔒 포인터 고정 여부: 눈깜빡임 OR 시선 인식 불가
    const shouldFreeze = blink || !calibrated

    // 표시할 포인터 위치: 고정 중이면 마지막 유효 위치, 아니면 현재 위치
    const displayX = shouldFreeze ? lastValidPosRef.current.x : x
    const displayY = shouldFreeze ? lastValidPosRef.current.y : y

    return (
        <motion.div
            className="gaze-cursor"
            animate={{ left: displayX, top: displayY }}
            // 🎚️ Spring 애니메이션: 눈깜빡임 또는 시선 불인식 중에는 이동하지 않음
            transition={{
                type: 'spring',
                stiffness: shouldFreeze ? 10000 : 300,  // 고정 중에는 stiffness 극대화
                damping: shouldFreeze ? 100 : 45        // 고정 중에는 감쇠 최대
            }}
        >
            {/* 외부 링 - 시선 위치 표시 */}
            <div className="cursor-ring"></div>
            {/* 내부 점 - 정확한 시선 중심 */}
            <div className="cursor-dot"></div>
        </motion.div>
    )
}

export default GazeCursor
