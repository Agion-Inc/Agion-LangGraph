/**
 * Agent-Chat Message Bubble Component
 * ChatGPT-inspired message display
 */

import React from 'react'
import { motion } from 'framer-motion'
import { format } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage } from '../../types/chat'
import { highlightKeywords, renderHighlightedText } from '../../utils/keywordHighlighter'
import { useAgentStore } from '../../hooks/useAgents'
import { logger } from '../../utils/logger'

interface MessageBubbleProps {
  message: ChatMessage
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user'
  const { agents } = useAgentStore()

  // Get agent keywords for highlighting
  const agentKeywords = React.useMemo(() => {
    if (!message.agentId) return []

    const agent = agents.find(a => a.agent_id === message.agentId)
    return agent?.keywords || []
  }, [agents, message.agentId])

  const containerClass = isUser
    ? 'user-message-container bg-chat-gray-50'
    : 'assistant-message-container bg-white'

  return (
    <motion.div
      className={`${containerClass} border-b border-chat-gray-200 py-6 px-4`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      <div className="max-w-chat mx-auto">
        <div className="flex items-start space-x-4">
          {/* Avatar */}
          <div className="flex-shrink-0">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                isUser
                  ? 'bg-chat-green-100 text-chat-green-700'
                  : 'bg-chat-purple-100 text-chat-purple-700'
              }`}
            >
              {isUser ? 'Y' : 'A'}
            </div>
          </div>

          {/* Message Content */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center space-x-2 mb-2">
              <span className="font-semibold text-chat-gray-900 text-sm">
                {isUser ? 'You' : message.agentName || 'Assistant'}
              </span>
              <span className="text-xs text-chat-gray-500">
                {format(message.timestamp, 'HH:mm')}
              </span>
              {message.status === 'error' && (
                <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded">
                  Error
                </span>
              )}
            </div>

            {/* Message Text */}
            <div className="message-content prose prose-sm max-w-none">
              {isUser ? (
                <UserMessageContent content={message.content} keywords={agentKeywords} />
              ) : (
                <AssistantMessageContent
                  content={message.content}
                  keywords={agentKeywords}
                  agentId={message.agentId}
                />
              )}
            </div>

            {/* Chart Visualization */}
            {!isUser && message.metadata?.agent_data?.chart_png && (
              <div className="mt-4 mb-4">
                <div className="border border-chat-gray-200 rounded-lg p-4 bg-white">
                  <img
                    src={`data:image/png;base64,${message.metadata.agent_data.chart_png}`}
                    alt="Generated Chart"
                    className="w-full h-auto rounded-lg"
                    style={{ maxHeight: '600px', objectFit: 'contain' }}
                  />
                  {message.metadata.agent_data.chart_url && (
                    <div className="mt-2 text-xs text-chat-gray-600">
                      <a
                        href={message.metadata.agent_data.chart_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-chat-blue-600 hover:underline"
                      >
                        Download Chart
                      </a>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Metadata */}
            {message.metadata && (
              <div className="mt-3 space-y-2">
                {/* Execution Time */}
                {message.metadata.executionTime && (
                  <div className="text-xs text-chat-gray-500">
                    Processed in {message.metadata.executionTime.toFixed(2)}s
                  </div>
                )}

                {/* Next Suggestions */}
                {message.metadata.nextSuggestions && message.metadata.nextSuggestions.length > 0 && (
                  <div className="mt-3">
                    <div className="text-xs text-chat-gray-600 mb-2 font-medium">
                      Suggested follow-ups:
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {message.metadata.nextSuggestions.slice(0, 3).map((suggestion: string, index: number) => (
                        <button
                          key={index}
                          className="px-3 py-1 text-xs bg-chat-gray-100 hover:bg-chat-gray-200 text-chat-gray-700 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-chat-blue-500 focus:ring-offset-2"
                          onClick={() => {
                            // Dispatch suggestion click event for parent component to handle
                            const event = new CustomEvent('suggestion-clicked', {
                              detail: { suggestion }
                            })
                            window.dispatchEvent(event)
                          }}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// Helper component for user message content with keyword highlighting
const UserMessageContent: React.FC<{ content: string; keywords: string[] }> = ({
  content,
  keywords
}) => {
  if (keywords.length === 0) {
    return <p className="text-chat-gray-800 leading-relaxed">{content}</p>
  }

  const highlightedParts = highlightKeywords(content, { keywords })

  return (
    <p className="text-chat-gray-800 leading-relaxed">
      {renderHighlightedText(highlightedParts)}
    </p>
  )
}

// Helper component for assistant message content with keyword highlighting
const AssistantMessageContent: React.FC<{
  content: string
  keywords: string[]
  agentId?: string
}> = ({ content, keywords, agentId }) => {
  // Custom markdown component that highlights keywords
  const HighlightedText: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    // Convert children to string safely
    const textContent = React.Children.toArray(children)
      .map(child => {
        if (typeof child === 'string') return child
        if (typeof child === 'number') return child.toString()
        return '' // Skip non-text content to avoid [object Object]
      })
      .join('')

    if (keywords.length === 0 || !textContent) {
      return <>{children}</>
    }

    const highlightedParts = highlightKeywords(textContent, { keywords })
    return <>{renderHighlightedText(highlightedParts, agentId)}</>
  }

  return (
    <ReactMarkdown
      className="text-chat-gray-800 leading-relaxed"
      remarkPlugins={[remarkGfm]}
      components={{
        // Customize markdown rendering with keyword highlighting
        p: ({ children }) => (
          <p className="mb-3 last:mb-0">
            <HighlightedText>{children}</HighlightedText>
          </p>
        ),
        text: ({ children }) => <HighlightedText>{children}</HighlightedText>,
        ul: ({ children }) => <ul className="mb-3 pl-6 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 pl-6 space-y-1">{children}</ol>,
        li: ({ children }) => (
          <li className="text-chat-gray-800">
            <HighlightedText>{children}</HighlightedText>
          </li>
        ),
        code: ({ children }) => (
          <code className="bg-chat-gray-100 px-2 py-1 rounded text-sm font-mono text-chat-gray-800">
            {children}
          </code>
        ),
        pre: ({ children }) => (
          <pre className="bg-chat-gray-100 p-4 rounded-lg overflow-x-auto mb-3">
            {children}
          </pre>
        ),
        img: ({ src, alt }) => {
          logger.debug('Rendering image', { src, alt });
          // Ensure the src is a string
          const imgSrc = String(src || '');

          // Check if it's a chart URL from our API
          if (imgSrc.includes('/api/v1/charts/')) {
            logger.debug('Chart URL detected, rendering image...');
          }

          return (
            <img
              src={imgSrc}
              alt={alt || 'Chart'}
              className="max-w-full h-auto rounded-lg shadow-lg my-4 block"
              style={{ maxHeight: '600px', display: 'block' }}
              crossOrigin="anonymous"  // Add CORS support
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                logger.error('Image failed to load', {
                  src: imgSrc,
                  naturalWidth: target.naturalWidth,
                  complete: target.complete
                });
              }}
              onLoad={(e) => {
                const target = e.target as HTMLImageElement;
                logger.debug('Image loaded successfully', {
                  src: imgSrc,
                  dimensions: `${target.naturalWidth}x${target.naturalHeight}`
                });
              }}
            />
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

export default MessageBubble