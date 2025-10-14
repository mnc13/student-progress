'use client'
import { useState } from 'react'
import { startSession, stopSession, getPersonalizedPlan } from '@/lib/api'

export default function StudyPage() {
  const userId = 'demo-user-1'
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [plan, setPlan] = useState<any>(null)

  return (
    <main className="space-y-4">
      <h2 className="text-2xl font-semibold">Study</h2>
      <div className="flex gap-2">
        <button
          className="px-4 py-2 rounded-xl bg-black text-white"
          onClick={async () => {
            const s = await startSession(userId, 'Anatomy')
            setSessionId(s.id)
          }}
          disabled={!!sessionId}
        >
          Start session
        </button>
        <button
          className="px-4 py-2 rounded-xl border"
          onClick={async () => {
            if (!sessionId) return
            await stopSession(sessionId, 4)
            setSessionId(null)
          }}
          disabled={!sessionId}
        >
          Stop session
        </button>
      </div>

      <button
        className="px-4 py-2 rounded-xl border"
        onClick={async () => setPlan(await getPersonalizedPlan(userId))}
      >
        Get personalized plan
      </button>

      {plan && <pre className="text-sm bg-gray-50 p-3 rounded-xl overflow-auto">{JSON.stringify(plan, null, 2)}</pre>}
    </main>
  )
}
