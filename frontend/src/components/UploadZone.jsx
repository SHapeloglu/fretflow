import { useState, useRef, useCallback } from 'react'
import { uploadFile } from '../utils/api'

const FORMATS = [
  { ext: 'MusicXML', best: true }, { ext: 'MIDI', best: true },
  { ext: 'PDF', best: false }, { ext: 'PNG', best: false }, { ext: 'JPG', best: false },
]

export default function UploadZone({ onResult, addToast }) {
  const [loading, setLoading] = useState(false)
  const [drag, setDrag] = useState(false)
  const inputRef = useRef(null)

  const handle = useCallback(async (file) => {
    if (!file) return
    setLoading(true)
    try {
      const result = await uploadFile(file)
      const src = result.tabs?.[0]?.tab_data?.source || result.source || ''
      addToast(result.cache_hit
        ? `Cache — ${result.tabs.length} versiyon`
        : `TAB üretildi${src ? ' (' + src + ')' : ''}`, 'success')
      onResult(result)
    } catch (e) {
      addToast('Hata: ' + e.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [onResult, addToast])

  const handleClick = useCallback(() => {
    if (!loading) inputRef.current?.click()
  }, [loading])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDrag(false)
    const file = e.dataTransfer.files[0]
    if (file) handle(file)
  }, [handle])

  return (
    <div
      className={`upload-zone ${drag ? 'drag' : ''}`}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".xml,.musicxml,.mxl,.mid,.midi,.pdf,.png,.jpg,.jpeg"
        style={{ display: 'none' }}
        onChange={e => { const f = e.target.files[0]; if(f) handle(f); e.target.value='' }}
      />
      <div className="upload-icon">𝄞</div>
      <div className="upload-title">Nota yükle</div>
      <div className="upload-sub">Sürükle bırak veya butona tıkla</div>
      <div className="upload-formats" style={{ marginBottom: 12 }}>
        {FORMATS.map(f => (
          <span key={f.ext} className={`fmt-badge ${f.best ? 'best' : ''}`}>{f.ext}</span>
        ))}
      </div>
      <button
        onClick={handleClick}
        disabled={loading}
        style={{
          background: 'linear-gradient(135deg,var(--purple3),#6050e0)',
          border: 'none', color: '#fff', fontSize: 12, fontWeight: 600,
          padding: '7px 18px', borderRadius: 7, cursor: loading ? 'default' : 'pointer',
          fontFamily: 'var(--sans)', opacity: loading ? 0.6 : 1,
          display: 'inline-flex', alignItems: 'center', gap: 6,
        }}>
        {loading ? '⏳ İşleniyor...' : '📂 Dosya Seç'}
      </button>
      {loading && (
        <div className="loading-bar" style={{ marginTop: 12 }}>
          <div className="loading-bar-inner" />
        </div>
      )}
    </div>
  )
}
