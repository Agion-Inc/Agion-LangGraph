/**
 * App Initializer Component
 * Ensures files are loaded from backend when app starts
 */

import { useEffect } from 'react'
import { useFileStore } from '../hooks/useFiles'

interface AppInitializerProps {
  children: React.ReactNode
}

export function AppInitializer({ children }: AppInitializerProps) {
  // Use the store directly without destructuring to avoid TypeScript issues
  const fileStore = useFileStore()
  
  useEffect(() => {
    console.log('[AppInitializer] Loading files from backend on mount...')
    
    // Load files from backend when component mounts
    const loadFiles = (fileStore as any).loadFiles
    if (typeof loadFiles === 'function') {
      loadFiles().then(() => {
        console.log('[AppInitializer] Files loaded successfully')
      }).catch((error: any) => {
        console.error('[AppInitializer] Failed to load files:', error)
      })
    } else {
      console.error('[AppInitializer] loadFiles is not available')
    }
  }, []) // Empty dependency array - run only once on mount
  
  return <>{children}</>
}
