/**
 * Shared Chat Input State Hook
 * Preserves input state between different views (chat, files)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface FileMention {
  id: string
  name: string
  position: number
}

interface ChatInputState {
  message: string
  mentionedFiles: FileMention[]
  isComposing: boolean
  
  // Actions
  setMessage: (message: string) => void
  setMentionedFiles: (files: FileMention[]) => void
  setIsComposing: (composing: boolean) => void
  addMentionedFile: (file: FileMention) => void
  removeMentionedFile: (fileId: string) => void
  clearInput: () => void
}

export const useChatInputState = create<ChatInputState>()(
  persist(
    (set, get) => ({
      message: '',
      mentionedFiles: [],
      isComposing: false,

      setMessage: (message: string) => set({ message }),
      
      setMentionedFiles: (mentionedFiles: FileMention[]) => set({ mentionedFiles }),
      
      setIsComposing: (isComposing: boolean) => set({ isComposing }),
      
      addMentionedFile: (file: FileMention) => {
        const { mentionedFiles } = get()
        if (!mentionedFiles.some(m => m.id === file.id)) {
          set({ mentionedFiles: [...mentionedFiles, file] })
        }
      },
      
      removeMentionedFile: (fileId: string) => {
        const { mentionedFiles, message } = get()
        const fileToRemove = mentionedFiles.find(m => m.id === fileId)
        const updatedFiles = mentionedFiles.filter(m => m.id !== fileId)
        
        // Also remove the @mention from the message
        let updatedMessage = message
        if (fileToRemove) {
          updatedMessage = message.replace(`@${fileToRemove.name}`, '').trim()
        }
        
        set({ 
          mentionedFiles: updatedFiles,
          message: updatedMessage
        })
      },
      
      clearInput: () => set({ 
        message: '', 
        mentionedFiles: [], 
        isComposing: false 
      })
    }),
    {
      name: 'chat-input-state',
      // Only persist the message and mentioned files, not composition state
      partialize: (state) => ({
        message: state.message,
        mentionedFiles: state.mentionedFiles
      })
    }
  )
)
