/**
 * Agent-Chat Typing Indicator Component
 * Elegant typing animation for assistant responses
 */

import React from 'react'
import { motion } from 'framer-motion'

interface TypingIndicatorProps {
  agentName?: string
  className?: string
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  agentName = 'Assistant',
  className = '',
}) => {
  return (
    <div className={`assistant-message-container bg-white border-b border-chat-gray-200 py-6 px-4 ${className}`}>
      <div className="max-w-chat mx-auto">
        <div className="flex items-start space-x-4">
          {/* Avatar */}
          <div className="flex-shrink-0">
            <div className="w-8 h-8 rounded-full bg-chat-purple-100 text-chat-purple-700 flex items-center justify-center text-sm font-medium">
              A
            </div>
          </div>

          {/* Typing Content */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center space-x-2 mb-2">
              <span className="font-semibold text-chat-gray-900 text-sm">{agentName}</span>
              <span className="text-xs text-chat-gray-500">thinking...</span>
            </div>

            {/* Typing Animation */}
            <div className="flex items-center space-x-1">
              <div className="flex space-x-1">
                <motion.div
                  className="w-2 h-2 bg-chat-gray-400 rounded-full"
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{
                    duration: 1.4,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                />
                <motion.div
                  className="w-2 h-2 bg-chat-gray-400 rounded-full"
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{
                    duration: 1.4,
                    repeat: Infinity,
                    ease: 'easeInOut',
                    delay: 0.2,
                  }}
                />
                <motion.div
                  className="w-2 h-2 bg-chat-gray-400 rounded-full"
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{
                    duration: 1.4,
                    repeat: Infinity,
                    ease: 'easeInOut',
                    delay: 0.4,
                  }}
                />
              </div>
              <span className="text-sm text-chat-gray-500 ml-3">AI is processing your request</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TypingIndicator