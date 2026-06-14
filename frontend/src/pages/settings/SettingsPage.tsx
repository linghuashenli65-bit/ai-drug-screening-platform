import React, { useState } from 'react';
import {
  Card,
  Typography,
  Switch,
  Divider,
  Space,
  Descriptions,
  Tag,
} from 'antd';
import {
  SettingOutlined,
  SafetyCertificateOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

const SettingsPage: React.FC = () => {
  const [experimentalMode, setExperimentalMode] = useState(false);

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        <SettingOutlined style={{ marginRight: 8 }} />
        系统设置
      </Title>

      <Card title="平台信息" style={{ marginBottom: 24 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="平台名称">
            AI 药物虚拟筛选平台
          </Descriptions.Item>
          <Descriptions.Item label="版本">v1.0.0</Descriptions.Item>
          <Descriptions.Item label="前端框架">
            React 19 + Vite 8 + TypeScript 6
          </Descriptions.Item>
          <Descriptions.Item label="UI 组件库">Ant Design 6</Descriptions.Item>
          <Descriptions.Item label="后端引擎">FastAPI + LangGraph</Descriptions.Item>
          <Descriptions.Item label="Docking 引擎">AutoDock Vina</Descriptions.Item>
          <Descriptions.Item label="AI 模型">DeepSeek-Chat</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color="green">运行中</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            安全设置
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Descriptions column={1}>
          <Descriptions.Item label="JWT 认证">
            <Tag color="blue">已启用</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="RBAC 权限控制">
            <Tag color="blue">已启用 (4 角色)</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Prompt 注入防护">
            <Tag color="blue">已启用</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="API 限流">
            <Tag color="orange">中等（100 req/min）</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title={
          <Space>
            <DatabaseOutlined />
            实验性功能
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Space direction="vertical">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 24,
            }}
          >
            <div>
              <Text strong>启用实验性 Docking 模式</Text>
              <br />
              <Text type="secondary">
                使用 GPU 加速和并行对接，可能影响稳定性
              </Text>
            </div>
            <Switch
              checked={experimentalMode}
              onChange={setExperimentalMode}
            />
          </div>
        </Space>
      </Card>

      <Divider />
      <Text type="secondary">
        AI 药物虚拟筛选平台 - 管理员设置面板
      </Text>
    </div>
  );
};

export default SettingsPage;
