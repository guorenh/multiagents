import { useState, useRef, useEffect } from 'react'
import { Layout, Card, Input, Spin, Alert } from 'antd'
import { createResearch, getResearchStatus, getResearchReport } from '../api/research'

export default function Research() {
    const [topic, setTopic] = useState('')
    const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle')
    const [report, setReport] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const intervalRef = useRef<number | null>(null)
    const handleSubmit = async (value: string) => {
    if (!value.trim()) return
    
    setLoading(true)
    setReport('')
    setError(null)
    setTopic(value)
    
    try {
        const { task_id } = await createResearch(value)
        setStatus('running')
        
        // 启动轮询
        intervalRef.current = window.setInterval(async () => {
        try {
            const res = await getResearchStatus(task_id)
            setStatus(res.status)
            
            if (res.status === 'completed') {
            if (intervalRef.current) clearInterval(intervalRef.current)
            const r = await getResearchReport(task_id)
            setReport(r.report)
            setLoading(false)
            } else if (res.status === 'failed') {
            if (intervalRef.current) clearInterval(intervalRef.current)
            setError(res.error || '调研失败')
            setLoading(false)
            }
        } catch (e: any) {
            if (intervalRef.current) clearInterval(intervalRef.current)
            setError(e.message || '查询失败')
            setLoading(false)
        }
        }, 3000)
        
    } catch (e: any) {
        setError(e.message || '提交失败')
        setLoading(false)
    }
    }
    useEffect(() => {
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current)
        }
    }, [])
  return (
    <Layout style={{ minHeight: '100vh', padding: '40px 20px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', width: '100%' }}>
        
        <Card title="市场调研助手" style={{ marginBottom: 20 }}>
            <Input.Search
            placeholder="输入调研主题，如：新能源汽车市场"
            enterButton="开始调研"
            size="large"
            loading={loading}
            onSearch={handleSubmit}
            />
        </Card>
        
        {status === 'running' && (
            <Card style={{ marginBottom: 20, textAlign: 'center' }}>
            <Spin size="large" />
            <p style={{ marginTop: 16 }}>正在调研「{topic}」，请稍候...</p>
            </Card>
        )}
        
        {error && (
            <Alert
            type="error"
            message="出错了"
            description={error}
            style={{ marginBottom: 20 }}
            showIcon
            />
        )}
        
        {report && (
            <Card title={`调研报告：${topic}`}>
            <pre style={{
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                fontFamily: 'inherit',
                margin: 0,
            }}>
                {report}
            </pre>
            </Card>
        )}
        
        </div>
    </Layout>
)
}