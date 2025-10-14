import axios from 'axios'
const base = process.env.ML_BASE_URL || 'http://localhost:8000'

export async function recommendSchedule(payload: any) {
  const { data } = await axios.post(`${base}/recommend/schedule`, payload)
  return data
}
