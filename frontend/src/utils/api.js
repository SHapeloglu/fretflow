const BASE = '/api'
export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Yükleme başarısız')
  return res.json()
}
export async function editTab(tabId, tabData) {
  const res = await fetch(`${BASE}/tab/${tabId}/edit`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tab_data: tabData }),
  })
  if (!res.ok) throw new Error('Kaydetme başarısız')
  return res.json()
}
export async function voteTab(tabId, type, value, userLevel = 'intermediate') {
  const res = await fetch(`${BASE}/tab/${tabId}/vote`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, value, user_level: userLevel }),
  })
  if (!res.ok) throw new Error('Oy kaydedilemedi')
  return res.json()
}
