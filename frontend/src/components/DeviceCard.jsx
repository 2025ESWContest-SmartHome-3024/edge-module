import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
    Power, PowerOff, Wind, Sun, Droplets,
    Thermometer, Fan, Lightbulb, Zap, Repeat, Leaf
} from 'lucide-react'
import {
    getDeviceActions,
    groupActionsByCategory,
    getCategoryLabel,
    getActionColor,
} from '../utils/deviceActions'
import './DeviceCard.css'

/**
 * 기기 타입별 아이콘 매핑
 */
const DEVICE_ICONS = {
    'air_purifier': Fan,
    'airpurifier': Fan,
    'air_conditioner': Wind,
    'aircon': Wind,
    'airconditioner': Wind
}

/**
 * 액션 아이콘 매핑
 */
const ACTION_ICON_MAP = {
    'Power': Power,
    'PowerOff': PowerOff,
    'Wind': Wind,
    'Thermometer': Thermometer,
    'Repeat': Repeat,
    'Leaf': Leaf,
    'Zap': Zap,
}

/**
 * 개별 기기 카드 컴포넌트 (v3 - 상태 관리 포함)
 * 
 * 기능:
 * - 기기 정보 표시
 * - 디바이스 액션 동적 렌더링
 * - 액션 클릭 시 AI-서버에 전송
 * - 기기 상태 유지 및 표시
 * - Gateway에서 실시간 상태 동기화
 * 
 * @param {Object} device - 기기 정보 (device_id, name, device_type)
 * @param {Function} onControl - 기기 제어 콜백
 */
function DeviceCard({ device, onControl }) {
    const [isExecuting, setIsExecuting] = useState(false)
    const [actions, setActions] = useState({})
    const [deviceState, setDeviceState] = useState({})
    const [lastAction, setLastAction] = useState(null)
    const [loading, setLoading] = useState(true)
    const cardRef = useRef(null)
    const statePollingRef = useRef(null)

    // ============================================================================
    // 초기화: 액션 정보 로드
    // ============================================================================
    useEffect(() => {
        loadActionsForDevice()
        pollDeviceState()

        return () => {
            if (statePollingRef.current) {
                clearInterval(statePollingRef.current)
            }
        }
    }, [device.device_id, device.device_type])

    /**
     * 디바이스 액션 정보 로드
     */
    const loadActionsForDevice = async () => {
        try {
            setLoading(true)
            const deviceType = device.device_type.toLowerCase()
            const actionsData = await getDeviceActions(deviceType)

            if (Object.keys(actionsData).length > 0) {
                setActions(actionsData)
                console.log(`[DeviceCard] ✅ 액션 로드: ${device.name}`)
            } else {
                console.warn(`[DeviceCard] ⚠️  액션 없음: ${device.name}`)
            }
        } catch (error) {
            console.error(`[DeviceCard] ❌ 액션 로드 실패:`, error)
        } finally {
            setLoading(false)
        }
    }

    /**
     * 기기 상태 폴링 (5초마다)
     */
    const pollDeviceState = async () => {
        try {
            const response = await fetch(`/api/devices/${device.device_id}/state`)
            const data = await response.json()

            if (data.success && data.state) {
                setDeviceState(data.state)
                console.log(`[DeviceCard] 📊 상태 업데이트:`, data.state)
            }
        } catch (error) {
            console.warn(`[DeviceCard] ⚠️  상태 조회 실패:`, error)
        }
    }

    // 상태 폴링 시작
    useEffect(() => {
        statePollingRef.current = setInterval(pollDeviceState, 5000)
        return () => {
            if (statePollingRef.current) {
                clearInterval(statePollingRef.current)
            }
        }
    }, [device.device_id])

    /**
     * 액션 실행 핸들러
     */
    const handleActionClick = async (actionName, actionInfo) => {
        try {
            setIsExecuting(true)
            console.log(`[DeviceCard] 🎯 액션 실행: ${device.name} → ${actionName}`)

            // AI-서버로 제어 요청
            const response = await fetch(`/api/devices/${device.device_id}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: actionName,
                    value: actionInfo?.value
                })
            })

            const result = await response.json()
            console.log(`[DeviceCard] 💬 응답:`, result)

            if (result.success) {
                console.log(`[DeviceCard] ✅ 액션 완료: ${result.message}`)

                // 마지막 액션 기록
                setLastAction({
                    name: actionName,
                    time: new Date(),
                    status: 'success'
                })

                // 즉시 상태 업데이트
                await pollDeviceState()

                // 부모 컴포넌트에 알림
                if (onControl) {
                    onControl(device.device_id, actionName, result)
                }
            } else {
                console.error(`[DeviceCard] ❌ 액션 실패:`, result.message)
                setLastAction({
                    name: actionName,
                    time: new Date(),
                    status: 'error'
                })
            }
        } catch (error) {
            console.error(`[DeviceCard] ❌ 오류:`, error)
            setLastAction({
                name: actionName,
                time: new Date(),
                status: 'error'
            })
        } finally {
            setIsExecuting(false)
        }
    }

    // 기기 타입에 맞는 아이콘
    const Icon = DEVICE_ICONS[device.device_type] || Power

    // 액션을 카테고리별로 그룹화
    const groupedActions = groupActionsByCategory(actions)

    // 현재 상태 표시 텍스트
    const getStateDisplay = () => {
        if (!deviceState || Object.keys(deviceState).length === 0) {
            return '상태 조회 중...'
        }

        const type = device.device_type.toLowerCase()

        if (type.includes('purifier')) {
            // 공기청정기: 전원 + 바람 + 모드
            const power = deviceState.power || 'OFF'
            const wind = deviceState.wind_strength || '-'
            return `${power} | 바람: ${wind}`
        } else if (type.includes('aircon') || type.includes('air_con')) {
            // 에어컨: 전원 + 온도 + 바람
            const power = deviceState.power || 'OFF'
            const temp = deviceState.target_temp || '-'
            const wind = deviceState.wind_strength || '-'
            return `${power} | ${temp}°C | 바람: ${wind}`
        }

        return '상태 미지원'
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
                    <p className="device-state">{getStateDisplay()}</p>
                </div>
            </div>

            {/* 액션 섹션 */}
            <div className="device-actions-section">
                {loading ? (
                    <div className="loading-actions">
                        <p>액션 로드 중...</p>
                    </div>
                ) : Object.keys(groupedActions).length > 0 ? (
                    Object.entries(groupedActions).map(([category, categoryActions]) => (
                        <div key={category} className="action-group">
                            <h4 className="action-group-title">{getCategoryLabel(category)}</h4>
                            <div className="action-buttons">
                                {categoryActions.map((action) => {
                                    const ActionIcon = ACTION_ICON_MAP[action.icon] || Zap
                                    const actionColor = getActionColor(action.type)
                                    const isActive = lastAction?.name === action.name && lastAction?.status === 'success'

                                    return (
                                        <motion.button
                                            key={action.name}
                                            className={`action-button ${isActive ? 'active' : ''}`}
                                            onClick={() => handleActionClick(action.name, action)}
                                            disabled={isExecuting}
                                            whileHover={{ scale: isExecuting ? 1 : 1.05 }}
                                            whileTap={{ scale: isExecuting ? 1 : 0.95 }}
                                            style={{
                                                borderColor: actionColor,
                                                backgroundColor: isActive ? actionColor + '20' : 'transparent',
                                            }}
                                            title={action.description}
                                        >
                                            <ActionIcon size={16} />
                                            <span>{action.name}</span>
                                        </motion.button>
                                    )
                                })}
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="no-actions">
                        <p>사용 가능한 액션이 없습니다</p>
                        <p className="hint">기기를 동기화하세요</p>
                    </div>
                )}
            </div>

            {/* 마지막 액션 표시 */}
            {lastAction && (
                <div className={`last-action ${lastAction.status}`}>
                    <span>
                        {lastAction.status === 'success' ? '✅' : '❌'}
                        {lastAction.name}
                    </span>
                </div>
            )}

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
