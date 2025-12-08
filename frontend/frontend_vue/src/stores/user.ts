import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', () => {
    const participantId = ref<string | null>(localStorage.getItem('participant_id'))
    const nickname = ref<string>('')
    const theme = ref<string>('')

    function setSession(id: string, name: string, userTheme: string) {
        participantId.value = id
        nickname.value = name
        theme.value = userTheme
        localStorage.setItem('participant_id', id)
        localStorage.setItem('nickname', name)
        localStorage.setItem('theme', userTheme)
    }

    function clearSession() {
        participantId.value = null
        nickname.value = ''
        theme.value = ''
        localStorage.removeItem('participant_id')
        localStorage.removeItem('nickname')
        localStorage.removeItem('theme')
    }

    function loadFromStorage() {
        participantId.value = localStorage.getItem('participant_id')
        nickname.value = localStorage.getItem('nickname') || ''
        theme.value = localStorage.getItem('theme') || ''
    }

    // Load once immediately
    loadFromStorage()

    return { participantId, nickname, theme, setSession, clearSession, loadFromStorage }
})
