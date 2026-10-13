import { useEffect, useState } from 'react'
import { Table, Tag, Card, Spin } from 'antd'
import { getMCPServers } from '../api/mcp'

export default function MCPServers() {
    const [servers, setServers] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    useEffect(() => {
        const load = async () => {
            try {
                const data = await getMCPServers()
                setServers(data)   
            } catch (e) {
                console.error('服务加载失败', e)
            } finally {
                setLoading(false)
        }
        }
        load()
    }, [])
    const columns = [
        {
            title: '服务名',
            dataIndex: 'name',
            key: 'name',
        },
        {
            title: '描述',
            dataIndex: 'description',
            key: 'description',
        },
        {
            title: '传输方式',
            dataIndex: 'transport',
            key: 'transport',
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => {
            const colorMap: Record<string, string> = {
                running: 'green',
                stopped: 'default',
                registered: 'blue',
                error: 'red',
            }
            return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
            },
        },
        ]
    return (
        <div style={{ maxWidth: 1000, margin: '0 auto', padding: '40px 20px' }}>
            <Card title="MCP 服务列表">
            {loading ? (
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Spin size="large" />
                </div>
            ) : (
                <Table
                dataSource={servers}
                columns={columns}
                rowKey="name"
                pagination={false}
                />
            )}
            </Card>
        </div>
)
}