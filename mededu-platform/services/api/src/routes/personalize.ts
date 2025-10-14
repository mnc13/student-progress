import { Router } from 'express'
import { prisma } from '../db'
import { recommendSchedule } from '../services/mlClient'

export const router = Router()

router.get('/schedule', async (req, res) => {
  const userId = String(req.query.userId || '')
  const user = await prisma.user.findUnique({
    where: { id: userId },
    include: { studySessions: true, preferences: true },
  })
  if (!user) return res.status(404).json({ error: 'User not found' })

  const payload = {
    timezone: user.preferences?.timezone || 'Asia/Dhaka',
    targetDailyMinutes: user.preferences?.targetDailyMinutes || 60,
    preferredWindows: (user.preferences as any)?.preferredWindows || [],
    sessions: user.studySessions.map(s => ({
      startedAt: s.startedAt,
      endedAt: s.endedAt,
      topic: s.topic,
      focusLevel: s.focusLevel,
    })),
  }

  const plan = await recommendSchedule(payload)
  res.json(plan)
})
