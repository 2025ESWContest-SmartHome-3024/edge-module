import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite 설정
// - React 플러그인 활성화
// - 개발 서버를 포트 3000에서 실행
// - /api와 /ws 경로를 백엔드로 프록시 설정
export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/api': {
                // REST API 요청을 백엔드 서버로 프록시
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/ws': {
                // WebSocket 연결을 백엔드 서버로 프록시
                target: 'ws://127.0.0.1:8000',
                ws: true,
            },
        },
    },
})
