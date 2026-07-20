export default function Toasts({ toasts }) {
  return (
    <div className="toasts">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}`}>
          {t.type === 'success' && <span style={{ color: 'var(--green)' }}>✓</span>}
          {t.type === 'error' && <span style={{ color: 'var(--red)' }}>✕</span>}
          {t.message}
        </div>
      ))}
    </div>
  )
}
