import { motion } from 'framer-motion'
import { useEffect, useRef } from 'react'
import './GazeCursor.css'

/**
 * 시선 커서 컴포넌트
 * - WebSocket으로부터 받은 시선 위치를 실시간으로 표시
 * - Spring 애니메이션으로 부드러운 움직임 구현
 * - 👁️ 눈깜빡임 또는 시선 인식 불가 시 포인터 마지막 위치에 고정
 * - 👁️ 0.5초+ 눈깜빡임 감지 → 시선 위치 요소 클릭
 * 
 * @param {number} x - 화면 X 좌표
 * @param {number} y - 화면 Y 좌표
 * @param {boolean} visible - 커서 표시 여부
 * @param {boolean} blink - 눈깜빡임 여부 (true = 눈 감음, 포인터 고정)
 * @param {boolean} calibrated - 시선 인식 가능 여부 (false = 인식 불가, 포인터 고정)
 */

function GazeCursor({ x, y, visible, blink = false, calibrated = true }) {
    const lastValidPosRef = useRef({
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
    })

    const prevBlinkRef = useRef(false)
    const shouldFreeze = blink || !calibrated

    // 고정되기 직전에 현재 위치를 유효 위치로 갱신
    useEffect(() => {
        if (!shouldFreeze && x >= 0 && y >= 0) {
            lastValidPosRef.current = { x, y }
        }
    }, [x, y, shouldFreeze])

    // 👁️ 깜빡임 끝남 감지 → 시선 위치 요소 클릭
    useEffect(() => {
        // blink: false → true (깜빡임 시작)는 무시
        // blink: true → false (깜빡임 끝) 감지 필요
        if (!blink && prevBlinkRef.current) {
            // 깜빡임 완료 → 시선 위치의 요소 클릭
            const element = document.elementFromPoint(lastValidPosRef.current.x, lastValidPosRef.current.y)
            if (element && element !== document.body && element !== document.documentElement) {
                console.log('[GazeCursor] 깜빡임 클릭 감지:', element.className)
                element.click()
            }
        }
        prevBlinkRef.current = blink
    }, [blink])

    if (!visible) return null

    const displayX = shouldFreeze ? lastValidPosRef.current.x : x
    const displayY = shouldFreeze ? lastValidPosRef.current.y : y

    return (
        <motion.div
            className="gaze-cursor"
            animate={{ left: displayX, top: displayY }}
            transition={{
                type: 'spring',
                stiffness: shouldFreeze ? 10000 : 150,
                damping: shouldFreeze ? 100 : 55
            }}
        >
            <div className="cursor-ring"></div>
            <div className="cursor-dot"></div>
        </motion.div>
    )
}

export default GazeCursor