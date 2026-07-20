const LABELS = { verified: '✅ Doğrulanmış', high_rated: '⭐ Yüksek Rate', new: '🔄 Yeni' }
export default function TabList({ tabs, activeId, onSelect }) {
  if (!tabs?.length) return null
  const sorted = [...tabs].sort((a,b) => {
    const o = { verified:0, high_rated:1, new:2 }
    return (o[a.category]??3)-(o[b.category]??3)
  })
  return (
    <div>
      <div className="sect-lbl">Versiyonlar</div>
      {sorted.map(tab => {
        const pct = Math.min(100, Math.round(tab.trust_score*100))
        const color = tab.trust_score>0.7?'var(--green)':tab.trust_score>0.4?'var(--amber)':'var(--purple2)'
        return (
          <div key={tab.id} className={`ver-card ${activeId===tab.id?'active':''}`} onClick={()=>onSelect(tab)}>
            <div className="ver-top">
              <span className={`badge badge-${tab.category}`}>{LABELS[tab.category]}</span>
            </div>
            <div className="trust-wrap">
              <div className="trust-track">
                <div className="trust-fill" style={{width:pct+'%',background:color}}/>
              </div>
              <span style={{fontSize:10,color:'var(--t3)',minWidth:28,textAlign:'right'}}>{pct>0?pct+'%':'—'}</span>
            </div>
            <div className="ver-meta">
              <span>{tab.accuracy_count} doğrulama</span><span>·</span>
              <span>{tab.vote_count} oy</span>
              {tab.rate_score>0&&<><span>·</span><span>★ {tab.rate_score.toFixed(1)}</span></>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
