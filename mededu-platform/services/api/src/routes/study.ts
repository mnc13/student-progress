import { Router } from 'express'
import { prisma } from '../db'

export const router = Router()

router.post('/start', async (req, res) => {
  const { userId, topic } = req.body
  const session = await prisma.studySession.create({
    data: { userId, topic, startedAt: new Date() },
  })
  res.json({ id: session.id })
})

router.post('/stop', async (req, res) => {
  const { sessionId, focusLevel } = req.body
  const session = await prisma.studySession.update({
    where: { id: sessionId },
    data: { endedAt: new Date(), focusLevel },
  })
  res.json({ ok: true, session })
})
