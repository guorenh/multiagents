import { useState, useRef, useEffect } from 'react'
import {  Card, Input, Spin, Alert, Typography } from 'antd'
import ReactMarkdown from 'react-markdown'
import { createResearch, getResearchStatus, getResearchReport } from '../api/research'

export default function Research() {
    const [topic, setTopic] = useState('')
    const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle')
    const [report, setReport] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const intervalRef = useRef<number | null>(null)
    const pollCountRef = useRef(0)

    // 轮询上限：3 秒一次，最多 5 分钟，避免任务卡死时无限转圈
    const POLL_INTERVAL_MS = 3000
    const MAX_POLLS = 100

    const stopPolling = () => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
        }
    }

    const handleSubmit = async (value: string) => {
        if (!value.trim()) return

        stopPolling()
        pollCountRef.current = 0
        setLoading(true)
        setReport('')
        setError(null)
        setStatus('running')
        setTopic(value)

        try {
            const { task_id } = await createResearch(value)

            // 启动轮询
            intervalRef.current = window.setInterval(async () => {
                pollCountRef.current += 1
                if (pollCountRef.current > MAX_POLLS) {
                    stopPolling()
                    setStatus('failed')
                    setError('调研超时（超过 5 分钟未完成），请稍后重试')
                    setLoading(false)
                    return
                }

                try {
                    const res = await getResearchStatus(task_id)
                    setStatus(res.status)

                    if (res.status === 'completed') {
                        stopPolling()
                        const r = await getResearchReport(task_id)
                        setReport(r.report)
                        setLoading(false)
                    } else if (res.status === 'failed') {
                        stopPolling()
                        setError(res.error || '调研失败')
                        setLoading(false)
                    }
                } catch (e: any) {
                    stopPolling()
                    setError(e.message || '查询失败')
                    setLoading(false)
                }
            }, POLL_INTERVAL_MS)
        } catch (e: any) {
            setError(e.message || '提交失败')
            setLoading(false)
        }
    }

    useEffect(() => {
        return () => {
            stopPolling()
        }
    }, [])

    return (
        <div style={{ minHeight: '100vh', padding: '40px 20px' }}>
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
                    <Card title={`调研报告：${topic}`} style={{ marginBottom: 20 }}>
                        <Typography>
                            <ReactMarkdown>{report}</ReactMarkdown>
                        </Typography>
                    </Card>
                )}

            </div>
        </div>
    )
}
