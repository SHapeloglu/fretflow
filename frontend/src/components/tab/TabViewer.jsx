import { useState, useRef, useEffect, useCallback } from 'react'
import { editTab, voteTab } from '../../utils/api'
import { initGuitar, playGuitarNote } from '../../utils/guitar'

const STR_NAMES = ['e','B','G','D','A','E']
const FINGER_NAMES = ['','İşaret','Orta','Yüzük','Serçe']
const FINGER_COLORS = ['','#7c6fff','#00d4aa','#f5a623','#ff4d6d']
const STR_THICKNESS = [1, 1.5, 2, 2.5, 3, 3.5]
const COLS = 64

function buildGrid(notes) {
  const grid = Array.from({length:6},()=>Array(COLS).fill(null))
  const rhythm = Array(COLS).fill(null)
  notes.forEach(n=>{
    const col=Math.min(COLS-1,Math.round((n.beat-1)*2))
    const s=n.string-1
    if(s>=0&&s<6){grid[s][col]=n;rhythm[col]=n.rhythm}
  })
  return {grid,rhythm}
}

function EditPanel({note,onSave,onClose}) {
  const [fret,setFret]=useState(note.fret)
  const [finger,setFinger]=useState(note.finger)
  const [string,setString]=useState(note.string)
  const [rhythm,setRhythm]=useState(note.rhythm||'↓')
  return (
    <div className="edit-panel">
      <div className="edit-title">Nota düzenle</div>
      <div className="edit-rows">
        <div className="edit-row"><span className="edit-lbl">Tel</span>
          <div className="chips">{STR_NAMES.map((n,i)=><button key={i} className={`chip ${string===i+1?'on':''}`} onClick={()=>setString(i+1)}>{n}</button>)}</div>
        </div>
        <div className="edit-row"><span className="edit-lbl">Fret</span>
          <div className="chips">{Array.from({length:13},(_,i)=><button key={i} className={`chip ${fret===i?'on':''}`} onClick={()=>setFret(i)}>{i}</button>)}</div>
        </div>
        <div className="edit-row"><span className="edit-lbl">Parmak</span>
          <div className="chips">{[0,1,2,3,4].map(f=><button key={f} className={`chip ${finger===f?'on':''}`} onClick={()=>setFinger(f)}>{f===0?'—':f}</button>)}</div>
        </div>
        <div className="edit-row"><span className="edit-lbl">Vuruş</span>
          <div className="chips">{['↓','↑'].map(r=><button key={r} className={`chip ${rhythm===r?'on':''}`} onClick={()=>setRhythm(r)}>{r}</button>)}</div>
        </div>
      </div>
      <div className="edit-actions">
        <button className="btn-save" onClick={()=>onSave({...note,fret,finger,string,rhythm,source:'user_edit'})}>Kaydet</button>
        <button className="btn-cancel" onClick={onClose}>İptal</button>
      </div>
    </div>
  )
}

function VotePanel({tabId}) {
  const [stars,setStars]=useState(0)
  const [hover,setHover]=useState(0)
  const [voted,setVoted]=useState(false)
  const [accDone,setAccDone]=useState(false)
  return (
    <div className="vote-bar">
      <span className="vote-lbl">Beğeni</span>
      <div className="stars">
        {[1,2,3,4,5].map(i=><span key={i} className={`star ${i<=(hover||stars)?'lit':''}`}
          onClick={()=>{setStars(i);voteTab(tabId,'rate',i);setVoted(true)}}
          onMouseEnter={()=>setHover(i)} onMouseLeave={()=>setHover(0)}>★</span>)}
      </div>
      {voted&&<span style={{fontSize:11,color:'var(--amber)',marginLeft:4}}>Teşekkürler</span>}
      <button className="acc-btn" disabled={accDone}
        onClick={()=>{voteTab(tabId,'accuracy',1);setAccDone(true)}}>
        {accDone?'✓ Doğrulandı':'✓ Notayla uyuşuyor'}
      </button>
    </div>
  )
}

export default function TabViewer({tabData,tabId,addToast,onEditSave}) {
  const isSample=tabId==null
  const [notes,setNotes]=useState(tabData?.notes||[])
  const [editing,setEditing]=useState(null)
  const [playing,setPlaying]=useState(false)
  const [activeIdx,setActiveIdx]=useState(-1)
  const [tempo,setTempo]=useState(tabData?.tempo||120)
  const [loading,setLoading]=useState(false)
  const scrollRef=useRef(null)
  const timerRef=useRef(null)
  const drag=useRef({on:false,sx:0,sl:0})
  const activeIdxRef=useRef(-1)

  const {grid,rhythm}=buildGrid(notes)

  // Gitar sesini önceden yükle
  useEffect(()=>{
    initGuitar().catch(()=>{})
  },[])

  const startPlay=useCallback(async()=>{
    setLoading(true)
    try {
      await initGuitar()
    } catch(e) {}
    setLoading(false)
    setPlaying(true)
    activeIdxRef.current=0
    setActiveIdx(0)

    const interval=(60/tempo)*1000
    const step=()=>{
      const idx=activeIdxRef.current
      if(idx>=notes.length){
        setPlaying(false)
        setActiveIdx(-1)
        activeIdxRef.current=-1
        return
      }
      setActiveIdx(idx)
      const n=notes[idx]
      playGuitarNote(n.pitch, (interval/1000)*0.9)

      if(scrollRef.current){
        const col=Math.round((n.beat-1)*2)
        scrollRef.current.scrollLeft=Math.max(0,col*44-200)
      }
      activeIdxRef.current=idx+1
      timerRef.current=setTimeout(step,interval)
    }
    step()
  },[notes,tempo])

  const stopPlay=useCallback(()=>{
    clearTimeout(timerRef.current)
    setPlaying(false)
    setActiveIdx(-1)
    activeIdxRef.current=-1
  },[])

  useEffect(()=>()=>clearTimeout(timerRef.current),[])

  const onMD=e=>{drag.current={on:true,sx:e.pageX-scrollRef.current.offsetLeft,sl:scrollRef.current.scrollLeft}}
  const onMM=e=>{if(!drag.current.on)return;scrollRef.current.scrollLeft=drag.current.sl-(e.pageX-scrollRef.current.offsetLeft-drag.current.sx)}
  const onMU=()=>{drag.current.on=false}

  async function handleSave(updated){
    const filtered=notes.filter(n=>!(n.beat===updated.beat&&n.string===editing.string))
    const final=[...filtered,updated].sort((a,b)=>a.beat-b.beat||a.string-b.string)
    setNotes(final);setEditing(null)
    try{await editTab(tabId,{...tabData,notes:final});addToast('Kaydedildi','success');if(onEditSave)onEditSave(final)}
    catch{addToast('Kaydetme başarısız','error')}
  }

  const activeNote=activeIdx>=0&&activeIdx<notes.length?notes[activeIdx]:null

  return (
    <div className="tab-viewer">
      {/* Header */}
      <div className="tab-viewer-header">
        <div className="tab-viewer-title">
          Smart TAB
          <div className="tempo-pill">♩ {tempo} BPM</div>
          {tabData?.source&&<span className="source-pill">{tabData.source}</span>}
        </div>
        <div style={{display:'flex',alignItems:'center',gap:10}}>
          <div style={{display:'flex',alignItems:'center',gap:6}}>
            <span style={{fontSize:10,color:'var(--t3)'}}>Hız</span>
            <input type="range" min="40" max="200" value={tempo}
              onChange={e=>setTempo(Number(e.target.value))}
              style={{width:80,accentColor:'var(--purple)'}}/>
            <span style={{fontSize:10,color:'var(--amber)',fontFamily:'var(--mono)',minWidth:28}}>{tempo}</span>
          </div>
          <button onClick={playing?stopPlay:startPlay} disabled={loading}
            style={{
              background:playing?'rgba(255,77,109,0.15)':'linear-gradient(135deg,var(--purple3),#6050e0)',
              border:playing?'1px solid var(--red)':'none',
              color:playing?'var(--red)':'#fff',
              padding:'6px 16px',borderRadius:8,cursor:'pointer',
              fontFamily:'var(--sans)',fontSize:13,fontWeight:600,
              display:'flex',alignItems:'center',gap:6,opacity:loading?0.6:1,
            }}>
            {loading?'⏳ Yükleniyor...':playing?'⏹ Durdur':'▶ Çal'}
          </button>
        </div>
      </div>

      {/* Parmak göstergesi */}
      {activeNote&&(
        <div style={{
          padding:'10px 20px',background:'var(--bg2)',
          borderBottom:'1px solid var(--border)',
          display:'flex',alignItems:'center',gap:16,
        }}>
          <div style={{
            width:42,height:42,borderRadius:'50%',flexShrink:0,
            background:FINGER_COLORS[activeNote.finger]||'var(--t3)',
            display:'flex',alignItems:'center',justifyContent:'center',
            fontSize:activeNote.finger?20:18,fontWeight:700,color:'#fff',
            boxShadow:`0 0 20px ${FINGER_COLORS[activeNote.finger]||'#666'}60`,
            transition:'all .1s',
          }}>
            {activeNote.finger||'○'}
          </div>
          <div>
            <div style={{fontSize:14,fontWeight:600,color:'var(--t1)'}}>
              {activeNote.finger?FINGER_NAMES[activeNote.finger]+' parmak':'Açık tel'}
            </div>
            <div style={{fontSize:11,color:'var(--t3)',fontFamily:'var(--mono)',marginTop:2}}>
              {STR_NAMES[activeNote.string-1]} teli
              {activeNote.fret>0?` · ${activeNote.fret}. perde`:''}
              {' · '}{activeNote.pitch}
            </div>
          </div>
          <div style={{marginLeft:'auto',display:'flex',flexDirection:'column',alignItems:'flex-end',gap:2}}>
            <span style={{fontSize:11,color:'var(--t3)',fontFamily:'var(--mono)'}}>
              {activeIdx+1} / {notes.length}
            </span>
            <div style={{
              width:120,height:3,background:'var(--border)',borderRadius:2,overflow:'hidden'
            }}>
              <div style={{
                width:`${((activeIdx+1)/notes.length)*100}%`,
                height:'100%',background:'linear-gradient(90deg,var(--purple),var(--teal))',
                transition:'width .1s',borderRadius:2,
              }}/>
            </div>
          </div>
        </div>
      )}

      {/* TAB Grid */}
      <div className="tab-display">
        <div className="tab-scroll" ref={scrollRef}
          onMouseDown={onMD} onMouseMove={onMM} onMouseUp={onMU} onMouseLeave={onMU}>
          <div className="tab-grid">
            {/* Ritim satırı */}
            <div className="rhythm-row">
              <div style={{width:28,flexShrink:0}}/>
              {Array.from({length:COLS},(_,c)=>{
                const r=rhythm[c]
                return <div key={c} className={`r-cell ${r==='↓'?'r-down':r==='↑'?'r-up':''}`}>{r||''}</div>
              })}
            </div>

            {/* Tel satırları */}
            {STR_NAMES.map((name,si)=>(
              <div key={name} className="str-row" style={{height:38}}>
                <div className="str-name" style={{
                  width:28,fontFamily:'var(--mono)',fontSize:12,fontWeight:700,
                  color:'var(--purple2)',textAlign:'center',flexShrink:0,
                }}>{name}</div>
                <div style={{flex:1,display:'flex',position:'relative',alignItems:'center'}}>
                  {/* Tel çizgisi - kalınlık farklı */}
                  <div style={{
                    position:'absolute',left:0,right:0,top:'50%',
                    height:STR_THICKNESS[si]+'px',
                    background:`rgba(165,148,255,${0.15+si*0.05})`,
                    transform:'translateY(-50%)',pointerEvents:'none',
                  }}/>
                  {Array.from({length:COLS},(_,c)=>{
                    const note=grid[si][c]
                    const noteIdx=note?notes.findIndex(n=>n.beat===note.beat&&n.string===note.string):-1
                    const isActive=noteIdx===activeIdx
                    const isEditing=editing&&note&&editing.beat===note.beat&&editing.string===note.string
                    const fc=note?FINGER_COLORS[note.finger]:null

                    // Ölçü çizgisi
                    const isBarLine=c>0&&c%8===0

                    return (
                      <div key={c} style={{
                        width:44,height:38,flexShrink:0,
                        display:'flex',alignItems:'center',justifyContent:'center',
                        position:'relative',cursor:note&&!playing?'pointer':'default',
                        borderLeft:isBarLine?'1px solid rgba(165,148,255,0.2)':'none',
                      }}>
                        {note&&(
                          <span
                            onClick={()=>!playing&&!isSample&&setEditing(note===editing?null:note)}
                            style={{
                              position:'relative',zIndex:2,
                              fontFamily:'var(--mono)',fontSize:12,fontWeight:700,
                              padding:'2px 5px',borderRadius:5,
                              display:'flex',alignItems:'center',gap:1,
                              minWidth:26,justifyContent:'center',lineHeight:1,
                              transition:'all .1s',
                              ...(isActive?{
                                background:fc?fc+'25':'rgba(124,111,255,0.3)',
                                border:`2px solid ${fc||'var(--purple2)'}`,
                                color:fc||'var(--purple2)',
                                transform:'scale(1.2)',
                                boxShadow:`0 0 14px ${fc||'var(--purple)'}60`,
                              }:isEditing?{
                                background:'rgba(245,166,35,0.2)',
                                border:'1px solid var(--amber)',
                                color:'var(--amber2)',
                              }:note.fret===0?{
                                background:'rgba(0,212,170,0.1)',
                                border:'1px solid rgba(0,212,170,0.35)',
                                color:'var(--teal)',
                              }:{
                                background:'var(--bg3)',
                                border:'1px solid var(--border2)',
                                color:'var(--t1)',
                              })
                            }}>
                            {note.fret}
                            {note.finger>0&&(
                              <span style={{fontSize:9,color:'inherit',opacity:0.6,fontWeight:400}}>
                                ({note.finger})
                              </span>
                            )}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
        {editing&&!playing&&!isSample&&<EditPanel note={editing} onSave={handleSave} onClose={()=>setEditing(null)}/>}
      </div>

      {isSample
        ?<div className="vote-bar"><span style={{fontSize:12,color:'var(--t3)'}}>Örnek veri: bu dosya tanınmadı, sonuç kaydedilmez, oy verilemez.</span></div>
        :<VotePanel tabId={tabId}/>}
    </div>
  )
}
