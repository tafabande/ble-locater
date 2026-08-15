import React, { Component, type ReactNode } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Unhandled React Error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="grid min-h-screen place-items-center bg-[#f4f6f6] p-6 text-[#121619]">
          <div className="max-w-md rounded-xl border border-[#e3e7e6] bg-white p-8 shadow-sm text-center">
            <div className="mx-auto mb-4 grid size-12 place-items-center rounded-full bg-[#fdecec] text-[#d03b3b] font-mono text-xl font-bold">
              !
            </div>
            <h1 className="font-serif text-xl font-semibold">Application Error</h1>
            <p className="mt-2 text-sm text-[#6b7472]">
              The web app encountered an unexpected error during rendering.
            </p>
            {this.state.error && (
              <pre className="mt-4 overflow-x-auto rounded bg-[#eef1f1] p-3 text-left font-mono text-xs text-[#d03b3b]">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              className="mt-6 rounded-md bg-[#0f766e] px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)

