import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatContextStore = defineStore('chatContext', () => {
    // Current context for the chat
    const mode = ref<string>('learning')
    const contentId = ref<string>('')
    const additionalContext = ref<any>({})

    // Trigger mechanism
    const pendingMessage = ref<string>('')

    // structured context
    const codeContext = ref({ html: '', css: '', js: '' })
    const taskContext = ref({ description: '', error: '', status: '' }) // For TestPage
    const selectionContext = ref<{ code: string, meta: any }>({ code: '', meta: null }) // For LearningPage

    function setContext(newMode: string, newContentId: string, contextData: any = {}) {
        mode.value = newMode
        contentId.value = newContentId
        additionalContext.value = contextData
        // Reset specific contexts on main context switch
        taskContext.value = { description: '', error: '', status: '' }
        selectionContext.value = { code: '', meta: null }
        // Note: codeContext might be preserved or reset depending on needs, easier to let pages manage it
    }

    function updateCodeContext(html: string, css: string, js: string) {
        codeContext.value = { html, css, js }
    }

    function updateTaskContext(info: { description?: string, error?: string, status?: string }) {
        taskContext.value = { ...taskContext.value, ...info }
    }

    function updateSelectionContext(code: string, meta: any) {
        selectionContext.value = { code, meta }
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
        codeContext,
        taskContext,
        selectionContext,
        setContext,
        triggerAskAI,
        clearPendingMessage,
        updateCodeContext,
        updateTaskContext,
        updateSelectionContext
    }
})
