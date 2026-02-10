import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ChatApp } from './components/chat-app'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ChatApp />
  </StrictMode>,
)
