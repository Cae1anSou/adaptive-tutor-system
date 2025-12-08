import { useUserStore } from '@/stores/user'

class WebSocketManager {
    socket: WebSocket | null = null
    subscribers: Record<string, Function[]> = {}
    reconnectAttempts = 0
    maxReconnectAttempts = 5

    subscribe(type: string, callback: Function) {
        if (!this.subscribers[type]) this.subscribers[type] = []
        this.subscribers[type].push(callback)
    }

    unsubscribe(type: string, callback: Function) {
        if (this.subscribers[type]) {
            this.subscribers[type] = this.subscribers[type].filter(cb => cb !== callback)
        }
    }

    private dispatch(data: any) {
        const { type } = data
        if (this.subscribers[type]) {
            this.subscribers[type].forEach(cb => cb(data))
        }
    }

    connect() {
        const userStore = useUserStore()
        if (!userStore.participantId) {
            console.warn('No participant ID, skipping WS connect')
            return
        }
        if (this.socket && this.socket.readyState === WebSocket.OPEN) return

        let protocol = 'ws'
        if (window.location.protocol === 'https:') {
            protocol = 'wss'
        }
        let host = window.location.host
        // If running in dev mode (e.g. localhost:5173), point to backend port 8000
        if (host.includes('localhost:5173')) {
            host = 'localhost:8000'
        }

        // Backend config has API_V1_STR="", so no prefix is needed.
        // Nginx should be updated to match this structure.
        const wsUrl = `${protocol}://${host}/ws/user/${encodeURIComponent(userStore.participantId)}`

        this.socket = new WebSocket(wsUrl)

        this.socket.onopen = () => {
            this.reconnectAttempts = 0
            console.log('WebSocket Connected')
        }

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                this.dispatch(data)
            } catch (e) {
                console.error('WS Message Parse Error', e)
            }
        }

        this.socket.onclose = () => {
            this.tryReconnect()
        }
    }

    tryReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            console.log(`Reconnecting WS... attempt ${this.reconnectAttempts + 1}`)
            setTimeout(() => this.connect(), 1000 * Math.pow(2, this.reconnectAttempts))
            this.reconnectAttempts++
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close()
            this.socket = null
        }
    }
}

export default new WebSocketManager()
