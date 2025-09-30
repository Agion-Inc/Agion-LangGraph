/**
 * Keyword Highlighting Utility
 * Highlights agent keywords in text content
 */

import React from 'react'

export interface HighlightOptions {
  keywords: string[]
  className?: string
  caseSensitive?: boolean
}

export interface HighlightedText {
  text: string
  isHighlighted: boolean
  keyword?: string
}

/**
 * Highlights keywords in text and returns structured data for rendering
 */
export function highlightKeywords(
  text: string,
  options: HighlightOptions
): HighlightedText[] {
  const { keywords, caseSensitive = false } = options

  if (!keywords.length || !text) {
    return [{ text, isHighlighted: false }]
  }

  // Sort keywords by length (longest first) to avoid partial matches
  const sortedKeywords = [...keywords].sort((a, b) => b.length - a.length)

  // Create regex pattern for all keywords
  const pattern = sortedKeywords
    .map(keyword => escapeRegExp(keyword))
    .join('|')

  const flags = caseSensitive ? 'g' : 'gi'
  const regex = new RegExp(`(${pattern})`, flags)

  const parts = text.split(regex)
  const result: HighlightedText[] = []

  for (const part of parts) {
    if (!part) continue

    // Check if this part is a keyword
    const matchedKeyword = sortedKeywords.find(keyword =>
      caseSensitive
        ? part === keyword
        : part.toLowerCase() === keyword.toLowerCase()
    )

    if (matchedKeyword) {
      result.push({
        text: part,
        isHighlighted: true,
        keyword: matchedKeyword
      })
    } else {
      result.push({
        text: part,
        isHighlighted: false
      })
    }
  }

  return result
}

/**
 * Escapes special regex characters
 */
function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Gets agent-specific highlighting color
 */
export function getAgentColor(agentId?: string): string {
  const agentColors: Record<string, string> = {
    'bp-003-brand-analysis': 'bg-blue-100 text-blue-800 border-blue-200',
    'bp-004-som-anomaly-detection': 'bg-purple-100 text-purple-800 border-purple-200',
    default: 'bg-yellow-100 text-yellow-800 border-yellow-200'
  }

  return agentColors[agentId || ''] || agentColors.default
}

/**
 * React component for rendering highlighted text
 */
export function renderHighlightedText(
  highlightedParts: HighlightedText[],
  agentId?: string
): React.ReactNode {
  const colorClass = getAgentColor(agentId)

  return highlightedParts.map((part, index) => {
    if (part.isHighlighted) {
      return React.createElement(
        'span',
        {
          key: index,
          className: `px-1 py-0.5 rounded text-sm font-medium border ${colorClass}`,
          title: `Agent keyword: ${part.keyword}`
        },
        part.text
      )
    }
    return React.createElement('span', { key: index }, part.text)
  })
}