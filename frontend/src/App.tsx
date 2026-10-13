import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import Research from './pages/Research'
import McpServers from './pages/MCPServers'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Settings from './pages/Settings'
import { getConfigStatus } from './api/config'

const { Header, Content } = Layout

function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    const check = async () => {
      try {
        const status = await getConfigStatus()
        // 未就绪且不在设置页 → 跳转到设置页
        if (!status.ready && location.pathname !== '/settings') {
          navigate('/settings')
        }
      } catch (e) {
        console.error('检查配置失败', e)
      }
    }
    check()
  }, [])
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={[
            { key: '/', label: <Link to="/">调研</Link> },
            { key: '/mcp', label: <Link to="/mcp">MCP 服务</Link> },
            { key: '/settings', label: <Link to="/settings">设置</Link> },
          ]}
        />
      </Header>
      <Content>
        <Routes>
          <Route path="/" element={<Research />} />
          <Route path="/mcp" element={<McpServers />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}