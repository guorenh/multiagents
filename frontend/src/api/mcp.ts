import axios from "axios"

const api = axios.create({
    baseURL: '/api',
    timeout: 10000,
})

export async function getMCPServers() {
    const res = await api.get('/mcp/servers')
    return res.data
}