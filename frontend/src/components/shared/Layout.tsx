/**
 * Agent-Chat Layout Component
 * Main application shell with ChatGPT-inspired design
 */

import React from 'react'
import { motion } from 'framer-motion'

interface LayoutProps {
  children: React.ReactNode
  sidebar?: React.ReactNode
  header?: React.ReactNode
}

export const Layout: React.FC<LayoutProps> = ({ children, sidebar, header }) => {
  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      {sidebar && (
        <motion.aside
          initial={{ x: -300, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="w-80 bg-chat-gray-50 border-r border-chat-gray-200 flex flex-col"
        >
          {sidebar}
        </motion.aside>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        {header && (
          <motion.header
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
            className="bg-white border-b border-chat-gray-200 px-6 py-4"
          >
            {header}
          </motion.header>
        )}

        {/* Main Content */}
        <motion.main
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.2 }}
          className="flex-1 overflow-hidden"
        >
          {children}
        </motion.main>
      </div>
    </div>
  )
}

export default Layout