export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000'

export async function getPersonalizedPlan(userId: string) {
  const res = await fetch(`${API_URL}/personalize/schedule?userId=${userId}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch plan')
  return res.json()
}

export async function startSession(userId: string, topic?: string) {
  const res = await fetch(`${API_URL}/study/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId, topic }),
  })
  return res.json()
}

export async function stopSession(sessionId: string, focusLevel?: number) {
  const res = await fetch(`${API_URL}/study/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, focusLevel }),
  })
  return res.json()
}
