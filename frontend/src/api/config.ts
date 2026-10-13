import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    timeout: 10000,
})

export interface ConfigField {
  name: string
  label: string
  description: string
  required: boolean
  used_by: string[]
  url: string
  secret: boolean
  is_configured: boolean
  type?: 'select'
  options?: string[]
  placeholder?: string
}

export async function getKeysStatus(): Promise<ConfigField[]> {
  const res = await api.get('/config/keys')
  return res.data
}

// 批量保存：后端先全部写完，再统一重建一次
// （重建会重启 MCP 子进程，代价很高，不能每个字段重建一次）
export async function updateKeys(keys: Record<string, string>) {
  const res = await api.post('/config/keys', { keys })
  return res.data
}

export async function getConfigStatus() {
  const res = await api.get('/config/status')
  return res.data
}
