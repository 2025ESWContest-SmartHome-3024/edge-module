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
 * 
 * 🎯 이동 속도 조절 가이드:
 * - stiffness: 값이 높을수록 반응이 빠름 (강함)
 *   * 800-1000: 아주 빠르고 민첨 (반응성 우선)
 *   * 500-600: 중간 반응 (기본)
 *   * 300-400: 느리고 부드러움 (안정성 우선)
 * 
 * - damping: 값이 높을수록 진동이 적고 안정적 (반발력)
 *   * 40-50: 아주 안정적 (흔들림 거의 없음)
 *   * 30-35: 중간 (기본)
 *   * 20-25: 빠른 응답 (약간 흔들릴 수 있음)
 * 
 * 추천 조합:
 * - 반응성 우선: stiffness: 800, damping: 25
 * - 균형: stiffness: 550, damping: 35
 * - 안정성 우선: stiffness: 350, damping: 45
 */
function GazeCursor({ x, y, visible }) {
    if (!visible) return null

    return (
        <motion.div
            className="gaze-cursor"
            animate={{ left: x, top: y }}
            // 🎚️ Spring 애니메이션: 이 부분을 수정하여 이동 속도 조절
            transition={{
                type: 'spring',
                stiffness: 300,  // ← 느리게 변경 (기본 500 → 300)
                damping: 45      // ← 더 안정적으로 (기본 30 → 45)
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
