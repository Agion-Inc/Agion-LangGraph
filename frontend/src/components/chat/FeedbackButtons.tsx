/**
 * Feedback Buttons Component
 * Allows users to rate agent responses with thumbs up/down and star ratings
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface FeedbackButtonsProps {
  messageId: string
  onFeedbackSubmit?: (feedback: FeedbackData) => void
}

export interface FeedbackData {
  messageId: string
  feedbackType: 'thumbs_up' | 'thumbs_down'
  rating?: number
  comment?: string
}

export const FeedbackButtons: React.FC<FeedbackButtonsProps> = ({
  messageId,
  onFeedbackSubmit
}) => {
  const [submitted, setSubmitted] = useState(false)
  const [showRating, setShowRating] = useState(false)
  const [selectedRating, setSelectedRating] = useState<number | null>(null)
  const [hoveredRating, setHoveredRating] = useState<number | null>(null)
  const [showComment, setShowComment] = useState(false)
  const [comment, setComment] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const submitFeedback = async (feedbackType: 'thumbs_up' | 'thumbs_down', rating?: number) => {
    setIsSubmitting(true)

    try {
      const feedbackData: FeedbackData = {
        messageId,
        feedbackType,
        rating,
        comment: comment || undefined
      }

      // Call API
      const response = await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          feedback_type: feedbackType,
          rating,
          comment: comment || undefined,
          user_id: 'anonymous' // TODO: Replace with actual user ID from auth
        })
      })

      if (!response.ok) {
        throw new Error('Feedback submission failed')
      }

      const data = await response.json()
      console.log('Feedback submitted:', data)

      // Call callback if provided
      if (onFeedbackSubmit) {
        onFeedbackSubmit(feedbackData)
      }

      setSubmitted(true)
      setShowRating(false)
      setShowComment(false)
    } catch (error) {
      console.error('Failed to submit feedback:', error)
      alert('Failed to submit feedback. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleThumbsUp = () => {
    setShowRating(true)
  }

  const handleThumbsDown = () => {
    submitFeedback('thumbs_down', 2)
  }

  const handleRatingClick = (rating: number) => {
    setSelectedRating(rating)
    submitFeedback('thumbs_up', rating)
  }

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 text-xs text-green-600"
      >
        <svg
          className="w-4 h-4"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
        <span>Thanks for your feedback!</span>
      </motion.div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {!showRating ? (
          <>
            <button
              onClick={handleThumbsUp}
              disabled={isSubmitting}
              className="group flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white hover:bg-gray-50 border border-gray-200 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Helpful response"
            >
              <svg
                className="w-4 h-4 text-gray-400 group-hover:text-green-600 transition-colors"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                />
              </svg>
              <span className="text-gray-600 group-hover:text-gray-900">Helpful</span>
            </button>

            <button
              onClick={handleThumbsDown}
              disabled={isSubmitting}
              className="group flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white hover:bg-gray-50 border border-gray-200 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Not helpful"
            >
              <svg
                className="w-4 h-4 text-gray-400 group-hover:text-red-600 transition-colors"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"
                />
              </svg>
              <span className="text-gray-600 group-hover:text-gray-900">Not helpful</span>
            </button>
          </>
        ) : (
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              className="flex items-center gap-2"
            >
              <span className="text-xs text-gray-600">Rate this response:</span>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((rating) => (
                  <button
                    key={rating}
                    onClick={() => handleRatingClick(rating)}
                    onMouseEnter={() => setHoveredRating(rating)}
                    onMouseLeave={() => setHoveredRating(null)}
                    disabled={isSubmitting}
                    className="focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:ring-offset-1 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-transform hover:scale-110"
                    title={`${rating} star${rating > 1 ? 's' : ''}`}
                  >
                    <svg
                      className={`w-5 h-5 transition-colors ${
                        (hoveredRating !== null && rating <= hoveredRating) ||
                        (hoveredRating === null && selectedRating !== null && rating <= selectedRating)
                          ? 'text-yellow-400'
                          : 'text-gray-300'
                      }`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  </button>
                ))}
              </div>
            </motion.div>
          </AnimatePresence>
        )}

        {/* Optional: Add comment button */}
        {!showRating && (
          <button
            onClick={() => setShowComment(!showComment)}
            className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded transition-colors"
            title="Add comment"
          >
            💬
          </button>
        )}
      </div>

      {/* Comment textarea */}
      <AnimatePresence>
        {showComment && !submitted && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment (optional)..."
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={2}
              maxLength={500}
            />
            <div className="text-xs text-gray-400 mt-1">
              {comment.length}/500 characters
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {isSubmitting && (
        <div className="text-xs text-gray-500">Submitting...</div>
      )}
    </div>
  )
}

export default FeedbackButtons
