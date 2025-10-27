import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
    Power, Wind, Sun, Droplets,
    Thermometer, Fan, Lightbulb, Zap
} from 'lucide-react'
import './DeviceCard.css'

/**
 * 기기 타입별 아이콘 매핑
 */
const DEVICE_ICONS = {
    'air_purifier': Fan,
    'airpurifier': Fan,
    'dryer': Zap,
    'air_conditioner': Wind,
    'aircon': Wind,
    'airconditioner': Wind
}

// 2초 시선 유지 시간
const DWELL_TIME = 2000

/**
 * 개별 기기 카드 컴포넌트 (v2 - 동적 액션 버튼)
 * - 기기 정보 표시
 * - 로컬 DB에서 모든 사용 가능한 액션 렌더링
 * - 각 액션 버튼별로 기기 제어
 * - 시선 hovering 감지 (dwell time)
 * 
 * @param {Object} device - 기기 정보 (device_id, name, device_type, actions[])
 * @param {Function} onControl - 기기 제어 콜백
 */
function DeviceCard({ device, onControl }) {
    const [isExecuting, setIsExecuting] = useState(false)
    const cardRef = useRef(null)

    /**
     * 액션 실행 핸들러
     */
    const handleActionClick = async (action) => {
        try {
            setIsExecuting(true)
            console.log(`[DeviceCard] 🎯 액션 실행: ${device.name} → ${action.action_name}`)

            // value_range가 JSON 문자열인 경우 파싱
            let valueToSend = null
            if (action.value_range) {
                try {
                    const parsedRange = JSON.parse(action.value_range)
                    // 배열이면 첫 번째 값 사용, 아니면 그대로 사용
                    valueToSend = Array.isArray(parsedRange) ? parsedRange[0] : parsedRange
                } catch (e) {
                    valueToSend = action.value_range
                }
            }

            const response = await fetch(`/api/devices/${device.device_id}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: action.action_name,
                    value: valueToSend
                })
            })

            const result = await response.json()
            console.log(`[DeviceCard] 💬 응답:`, result)

            if (result.success) {
                console.log(`[DeviceCard] ✅ 액션 완료: ${result.message}`)

                // 부모 컴포넌트에 알림 (선택사항)
                if (onControl) {
                    onControl(device.device_id, action.action_name, result)
                }
            } else {
                console.error(`[DeviceCard] ❌ 액션 실패:`, result.message)
            }
        } catch (error) {
            console.error(`[DeviceCard] ❌ 오류:`, error)
        } finally {
            setIsExecuting(false)
        }
    }

    // 기기 타입에 맞는 아이콘
    const Icon = DEVICE_ICONS[device.device_type] || Power

    // 액션 이름을 보기 좋게 포맷팅
    const formatActionName = (actionName) => {
        // "_"를 공백으로 치환하고 각 단어의 첫 글자를 대문자로
        return actionName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ')
    }

    // 액션 그룹화 (action_type별)
    const groupedActions = {}
    if (device.actions && Array.isArray(device.actions)) {
        device.actions.forEach(action => {
            const type = action.action_type || 'operation'
            if (!groupedActions[type]) {
                groupedActions[type] = []
            }
            groupedActions[type].push(action)
        })
    }

    return (
        <motion.div
            ref={cardRef}
            className="device-card"
            whileHover={{ y: -4 }}
            transition={{ duration: 0.2 }}
        >
            {/* 카드 헤더 */}
            <div className="device-header">
                <div className="device-icon">
                    <Icon size={32} />
                </div>
                <div className="device-info">
                    <h3 className="device-name">{device.name}</h3>
                    <p className="device-type">{device.device_type}</p>
                </div>
            </div>

            {/* 액션 섹션 */}
            <div className="device-actions-section">
                {Object.entries(groupedActions).length > 0 ? (
                    Object.entries(groupedActions).map(([actionType, actions]) => (
                        <div key={actionType} className="action-group">
                            <h4 className="action-group-title">{formatActionName(actionType)}</h4>
                            <div className="action-buttons">
                                {actions.map((action, idx) => (
                                    <motion.button
                                        key={idx}
                                        className="action-button"
                                        onClick={() => handleActionClick(action)}
                                        disabled={isExecuting}
                                        whileHover={{ scale: isExecuting ? 1 : 1.05 }}
                                        whileTap={{ scale: isExecuting ? 1 : 0.95 }}
                                        title={`타입: ${action.value_type || 'N/A'}\n범위: ${action.value_range || 'N/A'}`}
                                    >
                                        {formatActionName(action.action_name)}
                                    </motion.button>
                                ))}
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="no-actions">
                        <p>사용 가능한 액션이 없습니다</p>
                        <p className="hint">POST /api/devices/sync로 기기를 동기화하세요</p>
                    </div>
                )}
            </div>

            {/* 로딩 상태 */}
            {isExecuting && (
                <div className="device-loading">
                    <div className="spinner"></div>
                    <p>실행 중...</p>
                </div>
            )}
        </motion.div>
    )
}

export default DeviceCard
