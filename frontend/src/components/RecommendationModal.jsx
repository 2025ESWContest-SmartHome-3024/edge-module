import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { X, Sparkles, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import './RecommendationModal.css'

/**
 * 우선순위별 색상 및 아이콘 정의
 * 5: 긴급 (빨강)
 * 4: 높음 (주황)
 * 3: 보통 (파랑)
 * 2: 낮음 (초록)
 * 1: 참고 (회색)
 */
const PRIORITY_COLORS = {
    5: { bg: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', icon: AlertCircle },
    4: { bg: 'rgba(245, 158, 11, 0.1)', color: 'var(--warning)', icon: TrendingUp },
    3: { bg: 'rgba(59, 130, 246, 0.1)', color: 'var(--info)', icon: Sparkles },
    2: { bg: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', icon: CheckCircle },
    1: { bg: 'rgba(156, 163, 175, 0.1)', color: 'var(--gray-500)', icon: Sparkles },
}

/**
 * AI 추천 모달 컴포넌트
 * - 최상위 추천 사항을 메인 영역에 표시
 * - 추가 추천 3개까지 리스트에 표시
 * - 사용자가 추천을 수락하거나 거절할 수 있음
 * - 🔒 버튼 클릭 후 1.5초 포인터 고정
 * - 👁️ 모달 위에서 깜빡임 감지 → 버튼 실행
 * 
 * @param {Array} recommendations - 추천 배열
 * @param {Function} onAccept - 추천 수락 콜백
 * @param {Function} onClose - 모달 닫기 콜백
 * @param {boolean} prolongedBlink - 0.5초 이상 눈깜빡임
 */
function RecommendationModal({ recommendations, onAccept, onClose, prolongedBlink }) {
    // 🔒 포인터 고정 상태
    const [isLocked, setIsLocked] = useState(false)
    const lockTimerRef = useRef(null)

    // ⏱️ 포인터 고정 시간 (ms)
    const LOCK_DURATION = 1500  // 1.5초

    // 이전 prolongedBlink 상태 추적 (상태 변화 감지용)
    const prevBlinkRef = useRef(false)

    // 최상위 추천 (우선순위 최고)
    const topRecommendation = recommendations[0]

    if (!topRecommendation) return null

    // 우선순위에 맞는 색상 스타일 가져오기
    const priorityStyle = PRIORITY_COLORS[topRecommendation.priority] || PRIORITY_COLORS[3]
    const PriorityIcon = priorityStyle.icon

    /**
     * 버튼 클릭 핸들러
     * - 포인터 고정 시작
     * - 콜백 실행
     */
    const handleButtonClick = (callback) => {
        // 🔒 1.5초 포인터 고정 시작
        console.log(`[RecommendationModal] 포인터 고정 시작 (${LOCK_DURATION}ms)`)
        setIsLocked(true)

        // 기존 타이머 정리
        if (lockTimerRef.current) {
            clearTimeout(lockTimerRef.current)
        }

        // 1.5초 후 포인터 고정 해제
        lockTimerRef.current = setTimeout(() => {
            console.log(`[RecommendationModal] 포인터 고정 해제`)
            setIsLocked(false)
        }, LOCK_DURATION)

        // 콜백 실행
        callback()
    }

    // 컴포넌트 언마운트시 타이머 정리
    const cleanup = () => {
        if (lockTimerRef.current) {
            clearTimeout(lockTimerRef.current)
        }
    }

    /**
     * 👁️ 눈깜빡임 감지 - 모달 내 버튼 클릭
     * prolongedBlink가 false → true 전환 감지 (깜빡임 완료)
     */
    useEffect(() => {
        if (isLocked) return

        // 이전 상태: false, 현재 상태: true (깜빡임 END)
        if (!prevBlinkRef.current && prolongedBlink) {
            prevBlinkRef.current = prolongedBlink

            // 시선이 모달 영역에 있는지 확인
            const modal = document.querySelector('.recommendation-modal')
            const gazeCursor = document.querySelector('.gaze-cursor')

            if (!modal || !gazeCursor) return

            const modalRect = modal.getBoundingClientRect()
            const cursorRect = gazeCursor.getBoundingClientRect()
            const cursorX = cursorRect.left + cursorRect.width / 2
            const cursorY = cursorRect.top + cursorRect.height / 2

            // 시선이 모달 내부에 있는지 확인
            const isInside =
                cursorX >= modalRect.left &&
                cursorX <= modalRect.right &&
                cursorY >= modalRect.top &&
                cursorY <= modalRect.bottom

            if (isInside) {
                // 👁️ 모달 위에서 깜빡임 감지 → "적용하기" 버튼 클릭
                console.log(`[RecommendationModal] 👁️ 1초 깜빡임 클릭 감지 - "적용하기" 실행`)
                handleButtonClick(() => onAccept(topRecommendation))
            }
        } else {
            // 상태 업데이트
            prevBlinkRef.current = prolongedBlink
        }
    }, [prolongedBlink, isLocked, topRecommendation])

    return (
        <motion.div
            className="recommendation-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
        >
            <motion.div
                className="recommendation-modal"
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 20 }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* 모달 헤더 */}
                <div className="modal-header">
                    <div className="modal-title">
                        <Sparkles size={24} className="title-icon" />
                        <h2>AI 추천</h2>
                    </div>
                    <button className="close-button" onClick={onClose}>
                        <X size={24} />
                    </button>
                </div>

                {/* 주요 추천 사항 */}
                <div className="recommendation-content">
                    {/* 우선순위 배지 */}
                    <div
                        className="priority-badge"
                        style={{
                            background: priorityStyle.bg,
                            color: priorityStyle.color
                        }}
                    >
                        <PriorityIcon size={16} />
                        <span>
                            {topRecommendation.priority === 5 ? '긴급' :
                                topRecommendation.priority === 4 ? '높음' :
                                    topRecommendation.priority === 3 ? '보통' :
                                        topRecommendation.priority === 2 ? '낮음' : '참고'}
                        </span>
                    </div>

                    {/* 추천 제목 및 설명 */}
                    <h3 className="recommendation-title">{topRecommendation.title}</h3>
                    <p className="recommendation-description">{topRecommendation.description}</p>

                    {/* 추천 상세 정보 */}
                    <div className="recommendation-details">
                        <div className="detail-row">
                            <span className="detail-label">기기</span>
                            <span className="detail-value">{topRecommendation.device_name}</span>
                        </div>
                        <div className="detail-row">
                            <span className="detail-label">이유</span>
                            <span className="detail-value">{topRecommendation.reason}</span>
                        </div>
                    </div>

                    {/* 액션 버튼 */}
                    <div className="modal-actions">
                        <button
                            className="action-button accept"
                            onClick={() => handleButtonClick(() => onAccept(topRecommendation))}
                            disabled={isLocked}
                        >
                            <CheckCircle size={20} />
                            적용하기
                        </button>
                        <button
                            className="action-button dismiss"
                            onClick={() => handleButtonClick(onClose)}
                            disabled={isLocked}
                        >
                            나중에
                        </button>
                    </div>
                </div>

                {/* 추가 추천 목록 */}
                {recommendations.length > 1 && (
                    <div className="other-recommendations">
                        <div className="other-header">
                            <span>다른 추천 {recommendations.length - 1}개</span>
                        </div>
                        <div className="other-list">
                            {/* 최대 3개의 추가 추천 표시 */}
                            {recommendations.slice(1, 4).map((rec) => {
                                const style = PRIORITY_COLORS[rec.priority] || PRIORITY_COLORS[3]
                                const Icon = style.icon

                                return (
                                    <motion.div
                                        key={rec.id}
                                        className="other-item"
                                        whileHover={{ x: 4 }}
                                        onClick={() => handleButtonClick(() => onAccept(rec))}
                                        style={{ cursor: isLocked ? 'not-allowed' : 'pointer', opacity: isLocked ? 0.6 : 1 }}
                                    >
                                        <div
                                            className="other-icon"
                                            style={{
                                                background: style.bg,
                                                color: style.color
                                            }}
                                        >
                                            <Icon size={16} />
                                        </div>
                                        <div className="other-info">
                                            <div className="other-title">{rec.title}</div>
                                            <div className="other-device">{rec.device_name}</div>
                                        </div>
                                    </motion.div>
                                )
                            })}
                        </div>
                    </div>
                )}
            </motion.div>
        </motion.div>
    )
}

export default RecommendationModal
