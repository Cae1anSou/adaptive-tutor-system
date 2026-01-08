export interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
    mode?: string
    contentId?: string
    ts: number
}

const STORAGE_KEY_PREFIX = 'chat_history_'

export default {
    load(participantId: string): ChatMessage[] {
        try {
            const key = STORAGE_KEY_PREFIX + participantId
            const data = localStorage.getItem(key)
            return data ? JSON.parse(data) : []
        } catch (e) {
            console.error('Failed to load chat history', e)
            return []
        }
    },

    append(participantId: string, message: ChatMessage) {
        const key = STORAGE_KEY_PREFIX + participantId
        try {
            const existing = localStorage.getItem(key)
            const history = existing ? JSON.parse(existing) : []
            history.push(message)
            localStorage.setItem(key, JSON.stringify(history))
        } catch (e) {
            console.error('Failed to save chat history', e)
        }
    }
}
