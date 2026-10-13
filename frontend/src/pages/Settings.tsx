import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Tag, message, Space, Alert, AutoComplete, Typography } from 'antd'
import { getKeysStatus, updateKeys, getConfigStatus, type ConfigField } from '../api/config'

export default function Settings() {
  const [keys, setKeys] = useState<ConfigField[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [effectiveModel, setEffectiveModel] = useState<string | null>(null)
  const [form] = Form.useForm()

  const reload = async () => {
    const [fields, status] = await Promise.all([getKeysStatus(), getConfigStatus()])
    setKeys(fields)
    setEffectiveModel(status.model ?? null)
  }

  useEffect(() => {
    const load = async () => {
      try {
        await reload()
      } catch (e) {
        message.error('加载配置失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      // values 形如 { OPENAI_API_KEY: "...", LLM_MODEL: "...", ... }
      // undefined = 用户没动这个字段 → 保持原值
      // ""        = 用户主动清空 → 后端删掉它并回落到 config.yaml 默认值
      const changed: Record<string, string> = {}
      for (const [name, value] of Object.entries(values)) {
        if (value === undefined || value === null) continue
        changed[name] = String(value)
      }

      if (Object.keys(changed).length === 0) {
        message.info('没有需要保存的变更')
        return
      }

      await updateKeys(changed)
      message.success('保存成功，配置已生效')

      await reload()
      form.resetFields()
    } catch (e: any) {
      if (e.errorFields) {
        // 表单校验失败，忽略
      } else {
        message.error('保存失败：' + (e.message || '未知错误'))
      }
    } finally {
      setSaving(false)
    }
  }

  // 按字段元数据选择控件：
  //   type=select → 可搜索、且允许自由输入的下拉（模型名这类）
  //   secret      → 密码框
  //   其余        → 普通输入框（base_url / 模型名不该显示成小圆点）
  const renderControl = (key: ConfigField) => {
    const placeholder =
      key.placeholder ??
      (key.secret
        ? key.is_configured
          ? '已配置（留空则不修改）'
          : '请输入'
        : key.is_configured
          ? '已配置（清空则恢复默认）'
          : '请输入')

    if (key.type === 'select') {
      return (
        <AutoComplete
          options={(key.options ?? []).map((v) => ({ value: v }))}
          placeholder={placeholder}
          filterOption={(input, option) =>
            String(option?.value ?? '').toLowerCase().includes(input.toLowerCase())
          }
        />
      )
    }

    if (key.secret) {
      return <Input.Password placeholder={placeholder} />
    }

    return <Input placeholder={placeholder} />
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '40px 20px' }}>
      <Card title="API Key 配置" loading={loading}>
        <Alert
          type="info"
          message="配置说明"
          description="所有配置都保存在本地 data/credentials.json，不会上传到任何服务器。保存后自动生效，无需重启。留空并保存可清空该项，回落到 config.yaml 的默认值。"
          style={{ marginBottom: 16 }}
          showIcon
        />

        {effectiveModel && (
          <Typography.Paragraph style={{ marginBottom: 24 }}>
            当前生效模型：<Typography.Text code>{effectiveModel}</Typography.Text>
          </Typography.Paragraph>
        )}

        <Form form={form} layout="vertical">
          {keys.map((key) => (
            <Form.Item
              key={key.name}
              label={
                <Space>
                  <span>{key.label}</span>
                  {key.is_configured ? (
                    <Tag color="green">已配置</Tag>
                  ) : (
                    <Tag color={key.required ? 'orange' : 'default'}>
                      {key.required ? '未配置' : '用默认值'}
                    </Tag>
                  )}
                </Space>
              }
              name={key.name}
              extra={
                <span style={{ fontSize: 12, color: '#888' }}>
                  {key.description}
                  {key.url && (
                    <>
                      {' '}
                      <a href={key.url} target="_blank" rel="noreferrer">
                        申请地址
                      </a>
                    </>
                  )}
                </span>
              }
            >
              {renderControl(key)}
            </Form.Item>
          ))}

          <Form.Item>
            <Button type="primary" onClick={handleSave} loading={saving}>
              保存并生效
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
