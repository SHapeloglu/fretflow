import { useState, useCallback } from 'react'
export function useToast() {
  const [toasts, setToasts] = useState([])
  const add = useCallback((message, type = 'info') => {
    const id = Date.now()
    setToasts(p => [...p, { id, message, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3000)
  }, [])
  return { toasts, add }
}
