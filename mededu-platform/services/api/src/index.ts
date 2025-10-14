import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import { router as study } from './routes/study'
import { router as personalize } from './routes/personalize'

const app = express()
app.use(cors())
app.use(express.json())

app.get('/health', (_req, res) => res.json({ ok: true }))

app.use('/study', study)
app.use('/personalize', personalize)

const port = process.env.PORT || 4000
app.listen(port, () => console.log(`API at http://localhost:${port}`))
