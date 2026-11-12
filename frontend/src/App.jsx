import { useState } from 'react'
import UploadZone from './components/UploadZone'
import TabList from './components/TabList'
import TabViewer from './components/tab/TabViewer'
import Toasts from './components/Toast'
import { useToast } from './hooks/useToast'
export default function App() {
  const [result,setResult]=useState(null)
  const [activeTab,setActiveTab]=useState(null)
  const {toasts,add}=useToast()
  function handleResult(r) {
    setResult(r)
    const sorted=[...r.tabs].sort((a,b)=>b.trust_score-a.trust_score)
    setActiveTab(sorted[0]||null)
  }
  return (
    <div className="shell">
      <header className="topbar">
        <div className="logo">FretFlow</div>
        <div className="live-dot"/>
        {result&&<span style={{fontSize:11,color:'var(--t3)',fontFamily:'var(--mono)'}}>{result.cache_hit?'🔁':'✨'} {result.music_hash}</span>}
        <div className="topbar-spacer"/>
        {result&&<button className="btn" onClick={()=>{setResult(null);setActiveTab(null)}}>Yeni yükle</button>}
        <a href="/docs" target="_blank" className="btn">API Docs</a>
      </header>
      <div className="layout">
        <aside className="sidebar">
          <UploadZone onResult={handleResult} addToast={add}/>
          {result&&<><div className="divider"/><TabList tabs={result.tabs} activeId={activeTab?.id} onSelect={setActiveTab}/></>}
          {!result&&(
            <div style={{marginTop:20}}>
              <div className="sect-lbl">Format rehberi</div>
              <div style={{display:'flex',flexDirection:'column',gap:8}}>
                {[{fmt:'MusicXML / MIDI',desc:'%100 doğruluk',best:true},{fmt:'PDF / PNG / JPG',desc:'OpenCV OMR',best:false}].map(f=>(
                  <div key={f.fmt} style={{display:'flex',gap:8}}>
                    <span className={`fmt-badge ${f.best?'best':''}`} style={{flexShrink:0,marginTop:2}}>{f.fmt}</span>
                    <span style={{fontSize:11,color:'var(--t3)'}}>{f.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>
        <main className="content">
          {activeTab?(
            <TabViewer key={activeTab.id??'fallback'} tabData={activeTab.tab_data} tabId={activeTab.id} addToast={add}
              onEditSave={newNotes=>setResult(prev=>({...prev,tabs:prev.tabs.map(t=>t.id===activeTab.id?{...t,tab_data:{...t.tab_data,notes:newNotes}}:t)}))}/>
          ):(
            <div className="empty">
              <div className="empty-icon">𝄞</div>
              <h3>Nota bekliyor</h3>
              <p>Sol taraftan bir nota dosyası yükle — MusicXML, MIDI, PDF veya görsel.</p>
            </div>
          )}
        </main>
      </div>
      <Toasts toasts={toasts}/>
    </div>
  )
}
