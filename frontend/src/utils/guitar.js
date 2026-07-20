// MIDI.js Soundfonts - Acoustic Guitar Nylon
const BASE = 'https://raw.githubusercontent.com/gleitz/midi-js-soundfonts/gh-pages/FluidR3_GM/acoustic_guitar_nylon-mp3'

const SAMPLES = ['A2','A3','A4','C3','C4','C5','E3','E4','E5','G3','G4']
const buffers = {}
let ctx = null
let loaded = false
let loading = false

async function getCtx() {
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)()
  if (ctx.state === 'suspended') await ctx.resume()
  return ctx
}

export async function initGuitar() {
  if (loaded || loading) return
  loading = true
  ctx = await getCtx()
  await Promise.all(SAMPLES.map(async note => {
    try {
      const res = await fetch(`${BASE}/${note}.mp3`)
      const arr = await res.arrayBuffer()
      buffers[note] = await ctx.decodeAudioData(arr)
    } catch(e) {}
  }))
  loaded = true
  loading = false
}

export async function playGuitarNote(pitch, duration = 0.8) {
  ctx = await getCtx()
  const midi = pitchToMidi(pitch)
  
  // En yakın sample'ı bul
  const nearest = findNearest(midi)
  if (nearest && buffers[nearest]) {
    const buf = buffers[nearest]
    const src = ctx.createBufferSource()
    const g = ctx.createGain()
    const nearMidi = pitchToMidi(nearest)
    src.buffer = buf
    src.playbackRate.value = Math.pow(2, (midi - nearMidi) / 12)
    g.gain.setValueAtTime(0.7, ctx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration + 0.3)
    src.connect(g)
    g.connect(ctx.destination)
    src.start(ctx.currentTime)
    src.stop(ctx.currentTime + duration + 0.3)
    return
  }
  // Fallback
  fallbackGuitar(midi, duration)
}

function findNearest(midi) {
  let best = null, bestDist = 999
  SAMPLES.forEach(s => {
    const d = Math.abs(pitchToMidi(s) - midi)
    if (d < bestDist) { bestDist = d; best = s }
  })
  return best
}

function pitchToMidi(pitch) {
  const N = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
  const m = pitch.match(/^([A-G]#?)(\d)$/)
  if (!m) return 60
  return (parseInt(m[2])+1)*12 + (N[m[1]]||0)
}

function fallbackGuitar(midi, duration) {
  if (!ctx) return
  const freq = 440 * Math.pow(2, (midi-69)/12)
  const now = ctx.currentTime
  const g = ctx.createGain()
  const f = ctx.createBiquadFilter()
  f.type='lowpass'; f.frequency.value=2200; f.Q.value=1.5
  g.connect(f); f.connect(ctx.destination)
  [[1,0.4,'sawtooth'],[2,0.15,'sine'],[3,0.08,'sine']].forEach(([m,v,t])=>{
    const o = ctx.createOscillator()
    const og = ctx.createGain()
    o.type=t; o.frequency.value=freq*m
    og.gain.setValueAtTime(0,now)
    og.gain.linearRampToValueAtTime(v,now+0.01)
    og.gain.exponentialRampToValueAtTime(0.001,now+duration)
    o.connect(og); og.connect(g)
    o.start(now); o.stop(now+duration+0.05)
  })
}
