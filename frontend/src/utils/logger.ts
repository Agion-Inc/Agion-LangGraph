/**
 * Production-ready logging utility
 * Provides environment-aware logging with different levels
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

class Logger {
  private isDevelopment = process.env.NODE_ENV === 'development'
  private logLevel: LogLevel = (process.env.REACT_APP_LOG_LEVEL as LogLevel) || 'info'

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error']
    const currentLevelIndex = levels.indexOf(this.logLevel)
    const requestedLevelIndex = levels.indexOf(level)
    return requestedLevelIndex >= currentLevelIndex && this.isDevelopment
  }

  debug(...args: any[]): void {
    if (this.shouldLog('debug')) {
      console.debug('[DEBUG]', ...args)
    }
  }

  info(...args: any[]): void {
    if (this.shouldLog('info')) {
      console.info('[INFO]', ...args)
    }
  }

  warn(...args: any[]): void {
    if (this.shouldLog('warn')) {
      console.warn('[WARN]', ...args)
    }
  }

  error(...args: any[]): void {
    if (this.shouldLog('error')) {
      console.error('[ERROR]', ...args)
    }

    // In production, send errors to monitoring service
    if (!this.isDevelopment) {
      this.sendToMonitoring('error', args)
    }
  }

  private sendToMonitoring(level: string, args: any[]): void {
    // Integrate with error tracking service (e.g., Sentry, LogRocket)
    // This is a placeholder for production error tracking
    try {
      // Example: window.Sentry?.captureMessage(args.join(' '), level)
    } catch (e) {
      // Fail silently in production
    }
  }
}

export const logger = new Logger()
export default logger