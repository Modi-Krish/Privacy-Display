import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Apply initial global theme and typography from localStorage before React renders
const theme = localStorage.getItem('theme') || 'light'
const typography = localStorage.getItem('typography') || 'handwritten'
document.documentElement.dataset.theme = theme
document.documentElement.dataset.typography = typography

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
