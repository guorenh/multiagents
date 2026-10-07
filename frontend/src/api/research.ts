import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,  // 2 分钟超时（调研任务可能很久）
})

// 提交调研任务
export async function createResearch(topic: string) {
  const res = await api.post('/research', { topic })
  return res.data
}

// 查询任务状态
export async function getResearchStatus(taskId: string) {
  const res = await api.get(`/research/${taskId}`)
  return res.data
}

// 获取报告
export async function getResearchReport(taskId: string) {
  const res = await api.get(`/research/${taskId}/report`)
  return res.data
}