import { useState } from 'react'
import { motion } from 'framer-motion'
import { Eye, Sparkles } from 'lucide-react'
import './OnboardingPage.css'

/**
 * 온보딩/로그인 페이지
 * - 초기 사용자 입장점
 * - 데모 모드: 로그인 버튼 클릭으로 시작 (사용자명 입력 없음)
 */
function OnboardingPage({ onLogin }) {
    // 로그인 진행 중 여부
    const [isLoading, setIsLoading] = useState(false)

    /**
     * 로그인 버튼 클릭 핸들러
     */
    const handleLogin = async () => {
        setIsLoading(true)

        try {
            // 부모 로그인 핸들러 호출 (백엔드 API 호출)
            // 데모 모드: 백엔드에서 고정된 demo_user 사용
            await onLogin()
        } catch (error) {
            console.error('로그인 오류:', error)
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="onboarding-page">
            <div className="onboarding-background">
                {/* 배경 애니메이션 효과 */}
                <div className="gradient-orb orb-1"></div>
                <div className="gradient-orb orb-2"></div>
                <div className="gradient-orb orb-3"></div>
            </div>

            <div className="onboarding-content">
                <motion.div
                    className="onboarding-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    {/* 로고 */}
                    <motion.div
                        className="logo-container"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                    >
                        <div className="logo-icon">
                            <Eye size={48} strokeWidth={2} />
                        </div>
                    </motion.div>

                    {/* 제목 */}
                    <motion.h1
                        className="onboarding-title"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                    >
                        GazeHome
                    </motion.h1>

                    {/* 부제목 */}
                    <motion.p
                        className="onboarding-subtitle"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                    >
                        <Sparkles size={16} className="inline-icon" />
                        시선으로 제어하는 스마트한 공간
                    </motion.p>

                    {/* 로그인 폼 */}
                    <motion.div
                        className="login-form"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                    >
                        <button
                            type="button"
                            className="login-button"
                            onClick={handleLogin}
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <span className="loading-spinner"></span>
                                    로그인 중...
                                </>
                            ) : (
                                <>
                                    <Eye size={20} />
                                    시작하기
                                </>
                            )}
                        </button>
                    </motion.div>

                    {/* 기능 목록 */}
                    <motion.div
                        className="features-list"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                    >
                        <div className="feature-item">
                            <span className="feature-icon">👁️</span>
                            <span>시선 추적 기반 제어</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🏠</span>
                            <span>스마트홈 기기 관리</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🤖</span>
                            <span>AI 추천 시스템</span>
                        </div>
                    </motion.div>
                </motion.div>

                {/* 푸터 */}
                <motion.div
                    className="onboarding-footer"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1 }}
                >
                    <p>Powered by AIRIS</p>
                </motion.div>
            </div>
        </div>
    )
}

export default OnboardingPage
