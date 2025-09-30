/**
 * Optimized App Component with Code Splitting
 * Reduces initial bundle size through lazy loading
 */

import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/shared/Layout';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

// Lazy load pages for code splitting
const ChatContainer = lazy(() => import('./components/chat/ChatContainer'));
const AgentsPage = lazy(() => import('./pages/AgentsPage'));
const FileManagerPage = lazy(() => import('./pages/FileManagerPage'));

// Loading component
const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-screen">
    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
  </div>
);

// Error boundary component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-screen">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h2>
          <p className="text-gray-600 mb-4">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Optimized query client configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (was cacheTime in v4)
    },
    mutations: {
      retry: 1,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <div className="h-screen flex flex-col bg-gray-50">
          <Layout>
            <Suspense fallback={<LoadingSpinner />}>
              <Routes>
                <Route path="/" element={<ChatContainer />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/files" element={<FileManagerPage />} />
                <Route
                  path="*"
                  element={
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <h2 className="text-2xl font-bold text-gray-800 mb-2">404 - Page Not Found</h2>
                        <p className="text-gray-600">The page you're looking for doesn't exist.</p>
                      </div>
                    </div>
                  }
                />
              </Routes>
            </Suspense>
          </Layout>
          <Toaster
            position="bottom-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                style: {
                  background: '#10b981',
                },
              },
              error: {
                style: {
                  background: '#ef4444',
                },
              },
            }}
          />
        </div>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
