/**
 * Password Protection Component
 * Simple and elegant password gate for AIRGB Agent Chat
 */

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { LockClosedIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/solid'

interface PasswordProtectProps {
  onAuthenticated: () => void
}

export const PasswordProtect: React.FC<PasswordProtectProps> = ({ onAuthenticated }) => {
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Check if already authenticated
  useEffect(() => {
    const isAuth = sessionStorage.getItem('airgb_authenticated')
    if (isAuth === 'true') {
      onAuthenticated()
    }
  }, [onAuthenticated])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    // Simple client-side password check
    // In production, this should validate against a backend endpoint
    const validPasswords = [
      process.env.REACT_APP_ACCESS_PASSWORD || 'AIRGB2025',
      'RGBrands2025',
      'AgionAIRGB'
    ]

    // Simulate network delay for better UX
    await new Promise(resolve => setTimeout(resolve, 500))

    if (validPasswords.includes(password)) {
      sessionStorage.setItem('airgb_authenticated', 'true')
      onAuthenticated()
    } else {
      setError('Invalid password. Please try again.')
      setPassword('')
    }

    setIsLoading(false)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl shadow-lg mb-4"
          >
            <SparklesIcon className="w-10 h-10 text-white" />
          </motion.div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            AIRGB Agent Chat
          </h1>
          <p className="text-gray-600">
            World-class AI Agent Orchestration Platform
          </p>
        </div>

        {/* Password Form */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl shadow-xl p-8"
        >
          <div className="flex items-center justify-center mb-6">
            <div className="p-3 bg-gray-100 rounded-full">
              <LockClosedIcon className="w-6 h-6 text-gray-600" />
            </div>
          </div>

          <h2 className="text-xl font-semibold text-center text-gray-900 mb-2">
            Welcome to AIRGB
          </h2>
          <p className="text-sm text-gray-600 text-center mb-6">
            Please enter your password to continue
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  setError('')
                }}
                placeholder="Enter password"
                className={`w-full px-4 py-3 pr-12 border rounded-lg focus:outline-none focus:ring-2 transition-all ${
                  error 
                    ? 'border-red-300 focus:ring-red-500' 
                    : 'border-gray-300 focus:ring-blue-500 focus:border-transparent'
                }`}
                disabled={isLoading}
                autoFocus
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-700 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeSlashIcon className="w-5 h-5" />
                ) : (
                  <EyeIcon className="w-5 h-5" />
                )}
              </button>
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-sm text-red-600 text-center"
              >
                {error}
              </motion.p>
            )}

            <button
              type="submit"
              disabled={isLoading || !password}
              className={`w-full py-3 px-4 rounded-lg font-medium transition-all transform hover:scale-[1.02] ${
                isLoading || !password
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700 shadow-lg'
              }`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Verifying...
                </span>
              ) : (
                'Access Platform'
              )}
            </button>
          </form>
        </motion.div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-sm text-gray-600">
            © 2025 Agion. All rights reserved.
          </p>
        </div>
      </motion.div>
    </div>
  )
}

export default PasswordProtect
