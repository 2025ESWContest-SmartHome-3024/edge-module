import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import OnboardingPage from './pages/OnboardingPage'
import HomePage from './pages/HomePage'
import CalibrationPage from './pages/CalibrationPage'
import SettingsPage from './pages/SettingsPage'

/**
 * 메인 애플리케이션 컴포넌트
 * - 라우팅 관리
 * - 사용자 로그인 상태 관리
 * - 시선 보정 상태 관리
 * - localStorage를 통한 세션 영속성
 */
function App() {
    // 로그인 상태
    const [isLoggedIn, setIsLoggedIn] = useState(false)
    // 시선 보정 완료 여부
    const [isCalibrated, setIsCalibrated] = useState(false)

    /**
     * 앱 초기화: localStorage에서 로그인 상태 복원
     */
    useEffect(() => {
        // localStorage에서 로그인 정보 확인
        const loggedIn = localStorage.getItem('eyetrax_logged_in') === 'true'
        const username = localStorage.getItem('eyetrax_username')

        setIsLoggedIn(loggedIn)

        // 로그인된 사용자의 보정 데이터 확인
        if (loggedIn && username) {
            checkCalibrationStatus(username)
        }
    }, [])

    /**
     * 사용자의 시선 보정 상태 확인
     * @param {string} username - 사용자명
     */
    const checkCalibrationStatus = async (username) => {
        try {
            console.log(`[App] 사용자 보정 상태 확인: "${username}"`)
            const response = await fetch('/api/calibration/list')
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
            const data = await response.json()

            console.log(`[App] 사용 가능한 보정 파일:`, data.calibrations.map(c => c.name))

            // 사용자별 보정 파일 존재 확인
            const userCalibrationFile = `${username}.pkl`
            console.log(`[App] 찾는 파일: "${userCalibrationFile}"`)

            const hasUserCalibration = data.calibrations.some(
                cal => {
                    console.log(`[App] 비교: "${cal.name}" === "${userCalibrationFile}": ${cal.name === userCalibrationFile}`)
                    return cal.name === userCalibrationFile
                }
            )

            setIsCalibrated(hasUserCalibration)
            console.log(`[App] ${username} 보정 결과: ${hasUserCalibration ? '✅ 찾음' : '❌ 없음'}`)
        } catch (error) {
            console.error('보정 상태 확인 실패:', error)
            setIsCalibrated(false)
        }
    }

    /**
     * 사용자 로그인 처리
     * @param {string} username - 사용자명
     */
    const handleLogin = async (username) => {
        try {
            console.log(`[App] 사용자 로그인: "${username}"`)

            // 백엔드 로그인 API 호출
            const response = await fetch('/api/users/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username })
            })

            if (!response.ok) {
                throw new Error(`로그인 실패: ${response.status}`)
            }

            const data = await response.json()
            console.log('[App] 로그인 응답:', data)

            // localStorage에 저장
            localStorage.setItem('eyetrax_logged_in', 'true')
            localStorage.setItem('eyetrax_username', username)
            setIsLoggedIn(true)

            // 데이터베이스에서 보정 상태 설정
            setIsCalibrated(data.has_calibration)
            console.log(`[App] 사용자 ${username} 보정 상태: ${data.has_calibration ? '✅ 보정됨' : '❌ 미보정'}`)

        } catch (error) {
            console.error('[App] 로그인 오류:', error)
            alert(`로그인 실패: ${error.message}`)
        }
    }

    /**
     * 사용자 로그아웃 처리
     */
    const handleLogout = () => {
        localStorage.removeItem('eyetrax_logged_in')
        localStorage.removeItem('eyetrax_username')
        setIsLoggedIn(false)
        setIsCalibrated(false)
    }

    /**
     * 시선 보정 완료 처리
     */
    const handleCalibrationComplete = () => {
        // 보정 완료 시 홈으로 이동 가능하도록 상태 업데이트
        setIsCalibrated(true)
    }

    return (
        <BrowserRouter
            future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
            }}
        >
            <Routes>
                {/* 루트 경로: 로그인 여부에 따라 라우팅 */}
                <Route
                    path="/"
                    element={
                        !isLoggedIn ? (
                            // 미로그인: 온보딩 페이지
                            <OnboardingPage onLogin={handleLogin} />
                        ) : !isCalibrated ? (
                            // 로그인했으나 미보정: 보정 페이지로 리다이렉트
                            <Navigate to="/calibration" replace />
                        ) : (
                            // 로그인하고 보정 완료: 홈 페이지로 리다이렉트
                            <Navigate to="/home" replace />
                        )
                    }
                />
                {/* 보정 페이지: 로그인한 사용자만 접근 가능 */}
                <Route
                    path="/calibration"
                    element={
                        isLoggedIn ? (
                            <CalibrationPage onComplete={handleCalibrationComplete} />
                        ) : (
                            <Navigate to="/" replace />
                        )
                    }
                />
                {/* 홈 페이지: 로그인 및 보정 완료한 사용자만 접근 가능 */}
                <Route
                    path="/home"
                    element={
                        isLoggedIn && isCalibrated ? (
                            <HomePage onLogout={handleLogout} />
                        ) : (
                            <Navigate to="/" replace />
                        )
                    }
                />
                {/* 설정 페이지: 로그인한 사용자만 접근 가능 */}
                <Route
                    path="/settings"
                    element={
                        isLoggedIn ? (
                            <SettingsPage />
                        ) : (
                            <Navigate to="/" replace />
                        )
                    }
                />
            </Routes>
        </BrowserRouter>
    )
}

export default App
