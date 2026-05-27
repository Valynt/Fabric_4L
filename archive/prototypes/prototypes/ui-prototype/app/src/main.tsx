import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Initialize theme from localStorage before render
const savedTheme = localStorage.getItem('vp-theme')
const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
if (savedTheme === 'dark' || (!savedTheme && systemDark)) {
  document.documentElement.classList.add('dark')
} else {
  document.documentElement.classList.remove('dark')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
