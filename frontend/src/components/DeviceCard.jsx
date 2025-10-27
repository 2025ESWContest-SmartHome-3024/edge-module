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

            const response = await fetch(`/api/devices/${device.device_id}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: action.action_name,
                    value: action.value_range
                })
            })

            const result = await response.json()
            console.log(`[DeviceCard] 💬 응답:`, result)

            if (result.success) {
                console.log(`[DeviceCard] ✅ 액션 완료: ${result.message}`)
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
                            <h4 className="action-group-title">{actionType}</h4>
                            <div className="action-buttons">
                                {actions.map((action, idx) => (
                                    <motion.button
                                        key={idx}
                                        className="action-button"
                                        onClick={() => handleActionClick(action)}
                                        disabled={isExecuting}
                                        whileHover={{ scale: isExecuting ? 1 : 1.05 }}
                                        whileTap={{ scale: isExecuting ? 1 : 0.95 }}
                                        title={`${action.action_name}\n타입: ${action.value_type}\n범위: ${action.value_range}`}
                                    >
                                        {action.action_name}
                                    </motion.button>
                                ))}
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="no-actions">
                        <p>사용 가능한 액션이 없습니다</p>
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
