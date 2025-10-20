import { motion } from 'framer-motion'
import './GazeCursor.css'

/**
 * 시선 커서 컴포넌트
 * - WebSocket으로부터 받은 시선 위치를 실시간으로 표시
 * - Spring 애니메이션으로 부드러운 움직임 구현
 * 
 * @param {number} x - 화면 X 좌표
 * @param {number} y - 화면 Y 좌표
 * @param {boolean} visible - 커서 표시 여부
 */
function GazeCursor({ x, y, visible }) {
    if (!visible) return null

    return (
        <motion.div
            className="gaze-cursor"
            animate={{ left: x, top: y }}
            // Spring 애니메이션: stiffness가 높을수록 반응이 빠름
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        >
            {/* 외부 링 - 시선 위치 표시 */}
            <div className="cursor-ring"></div>
            {/* 내부 점 - 정확한 시선 중심 */}
            <div className="cursor-dot"></div>
        </motion.div>
    )
}

export default GazeCursor
