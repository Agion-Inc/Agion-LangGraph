/**
 * Agent-Chat Main Application
 * World-class AI Agent Orchestration Platform with Routing
 */

import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { Layout } from './components/shared/Layout'
import { ChatContainer } from './components/chat/ChatContainer'
import { Sidebar } from './components/shared/Sidebar'
import { PasswordProtect } from './components/auth/PasswordProtect'
import FileManagerPage from './pages/FileManagerPage'
import AgentsPage from './pages/AgentsPage'
import { AppInitializer } from './components/AppInitializer'
import './index.css'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10, // 10 minutes (was cacheTime in v4)
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error instanceof Error && error.message.includes('4')) {
          return false
        }
        return failureCount < 3
      },
    },
  },
})

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    sessionStorage.getItem('airgb_authenticated') === 'true'
  )

  if (!isAuthenticated) {
    return (
      <BrowserRouter>
        <PasswordProtect onAuthenticated={() => setIsAuthenticated(true)} />
      </BrowserRouter>
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppInitializer>
          <div className="App">
            <Routes>
            {/* Chat Page - With Sidebar */}
            <Route path="/chat" element={
              <Layout sidebar={<Sidebar />}>
                <ChatContainer />
              </Layout>
            } />

            {/* Files Page - With Sidebar and Chat */}
            <Route path="/files" element={
              <Layout sidebar={<Sidebar />}>
                <FileManagerPage />
              </Layout>
            } />

            {/* Agents Page - With Sidebar and Chat */}
            <Route path="/agents" element={
              <Layout sidebar={<Sidebar />}>
                <AgentsPage />
              </Layout>
            } />

            {/* Default Route */}
            <Route path="/" element={<Navigate to="/chat" replace />} />

            {/* 404 Fallback */}
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>

            {/* Toast notifications */}
            <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#ffffff',
                color: '#374151',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '14px',
                fontFamily: 'var(--font-system)',
              },
              success: {
                style: {
                  borderColor: '#10b981',
                },
              },
              error: {
                style: {
                  borderColor: '#ef4444',
                },
              },
            }}
          />
          </div>
        </AppInitializer>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
