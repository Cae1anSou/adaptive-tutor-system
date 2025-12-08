import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatContextStore = defineStore('chatContext', () => {
    // Current context for the chat
    const mode = ref<string>('learning')
    const contentId = ref<string>('')
    const additionalContext = ref<any>({})

    // Trigger mechanism
    const pendingMessage = ref<string>('')

    function setContext(newMode: string, newContentId: string, contextData: any = {}) {
        mode.value = newMode
        contentId.value = newContentId
        additionalContext.value = contextData
    }

    function triggerAskAI(message: string) {
        pendingMessage.value = message
    }

    function clearPendingMessage() {
        pendingMessage.value = ''
    }

    return {
        mode,
        contentId,
        additionalContext,
        pendingMessage,
        setContext,
        triggerAskAI,
        clearPendingMessage
    }
})
