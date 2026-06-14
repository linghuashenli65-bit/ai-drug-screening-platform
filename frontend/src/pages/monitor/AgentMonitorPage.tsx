import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Typography,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  Select,
  FloatButton,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { Job, AgentNode, AgentNodeState } from '../../types';
import { taskService } from '../../services/taskService';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import EmptyState from '../../components/EmptyState';

const { Title, Text } = Typography;

const stateColors: Record<AgentNodeState, string> = {
  PENDING: 'default',
  RUNNING: 'processing',
  SUCCESS: 'success',
  FAILED: 'error',
  RETRYING: 'warning',
};

const stateLabels: Record<AgentNodeState, string> = {
  PENDING: '待执行',
  RUNNING: '运行中',
  SUCCESS: '成功',
  FAILED: '失败',
  RETRYING: '重试中',
};

interface AgentStats {
  totalExecutions: number;
  successCount: number;
  failureCount: number;
  retryCount: number;
  avgDurationMs: number;
  successRate: number;
}

function computeStats(jobs: Job[]): AgentStats & { nodeDetails: Record<string, AgentStats> } {
  const allNodes: AgentNode[] = jobs.flatMap((j) => j.nodes || []);

  const totalExecutions = allNodes.length;
  const successCount = allNodes.filter((n) => n.state === 'SUCCESS').length;
  const failureCount = allNodes.filter((n) => n.state === 'FAILED').length;
  const retryCount = allNodes.reduce((sum, n) => sum + (n.retry_count || 0), 0);
  const completedNodes = allNodes.filter((n) => n.duration_ms != null);
  const avgDurationMs =
    completedNodes.length > 0
      ? completedNodes.reduce((s, n) => s + (n.duration_ms || 0), 0) /
        completedNodes.length
      : 0;

  // Per-node stats
  const nodeNames = [...new Set(allNodes.map((n) => n.name || n.id))];
  const nodeDetails: Record<string, AgentStats> = {};
  nodeNames.forEach((name) => {
    const nodes = allNodes.filter((n) => (n.name || n.id) === name);
    const nSuccess = nodes.filter((n) => n.state === 'SUCCESS').length;
    const nFail = nodes.filter((n) => n.state === 'FAILED').length;
    const nRetry = nodes.reduce((s, n) => s + (n.retry_count || 0), 0);
    const completed = nodes.filter((n) => n.duration_ms != null);
    const avgDur =
      completed.length > 0
        ? completed.reduce((s, n) => s + (n.duration_ms || 0), 0) /
          completed.length
        : 0;
    nodeDetails[name] = {
      totalExecutions: nodes.length,
      successCount: nSuccess,
      failureCount: nFail,
      retryCount: nRetry,
      avgDurationMs: avgDur,
      successRate: nodes.length > 0 ? (nSuccess / nodes.length) * 100 : 0,
    };
  });

  return {
    totalExecutions,
    successCount,
    failureCount,
    retryCount,
    avgDurationMs,
    successRate: totalExecutions > 0 ? (successCount / totalExecutions) * 100 : 0,
    nodeDetails,
  };
}

const AgentMonitorPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterJobId, setFilterJobId] = useState<string>('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await taskService.listJobs({ page_size: 50 });
      setJobs(res.items || []);
    } catch {
      setError('无法加载监控数据');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) return <LoadingState tip="加载监控数据中..." />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  const stats = computeStats(jobs);

  // Build all nodes table
  const allNodes: Array<AgentNode & { job_id: number }> = jobs.flatMap((j) =>
    (j.nodes || []).map((n) => ({ ...n, job_id: j.job_id }))
  );

  const filteredNodes = filterJobId
    ? allNodes.filter((n) => String(n.job_id).includes(filterJobId))
    : allNodes;

  const nodeTableColumns = [
    { title: 'Job ID', dataIndex: 'job_id', key: 'job_id', width: 140, ellipsis: true },
    { title: '节点', dataIndex: 'label', key: 'label', width: 120,
      render: (_: unknown, r: AgentNode & { job_id: number }) => r.label || r.name || r.id,
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      width: 100,
      render: (s: AgentNodeState) => <Tag color={stateColors[s]}>{stateLabels[s]}</Tag>,
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      render: (t?: string) => (t ? new Date(t).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (d?: number) => {
        if (!d) return '-';
        return d < 1000 ? `${d}ms` : `${(d / 1000).toFixed(1)}s`;
      },
    },
    {
      title: '重试',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 60,
    },
    {
      title: '错误',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (msg?: string) =>
        msg ? (
          <Text type="danger" ellipsis style={{ maxWidth: 200 }}>
            {msg}
          </Text>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          Agent 执行监控
        </Title>
        <FloatButton icon={<ReloadOutlined />} onClick={fetchData} />
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="总执行次数"
              value={stats.totalExecutions}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="成功率"
              value={stats.successRate}
              prefix={<CheckCircleOutlined />}
              suffix="%"
              precision={1}
              valueStyle={{ color: stats.successRate > 90 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="成功"
              value={stats.successCount}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="失败"
              value={stats.failureCount}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="重试次数"
              value={stats.retryCount}
              prefix={<SyncOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="平均耗时"
              value={stats.avgDurationMs < 1000 ? `${Math.round(stats.avgDurationMs)}ms` : `${(stats.avgDurationMs / 1000).toFixed(1)}s`}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Per-Agent Stats */}
      <Card title="各 Agent 统计" style={{ marginBottom: 24 }}>
        {Object.keys(stats.nodeDetails).length > 0 ? (
          <Row gutter={[16, 16]}>
            {Object.entries(stats.nodeDetails).map(([name, s]) => (
              <Col xs={24} sm={12} md={8} lg={6} key={name}>
                <Card size="small" title={name}>
                  <Statistic
                    title="成功率"
                    value={s.successRate}
                    suffix="%"
                    precision={1}
                    valueStyle={{
                      fontSize: 20,
                      color: s.successRate > 90 ? '#52c41a' : '#faad14',
                    }}
                  />
                  <Space style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      成功 {s.successCount} / 失败 {s.failureCount}
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <EmptyState description="暂无 Agent 执行数据" />
        )}
      </Card>

      {/* Nodes Table */}
      <Card title="节点执行记录">
        <div style={{ marginBottom: 16 }}>
          <Select
            value={filterJobId || undefined}
            onChange={(v) => setFilterJobId(v || '')}
            placeholder="按任务ID筛选"
            allowClear
            showSearch
            style={{ width: 200 }}
          >
            {jobs.map((j) => (
              <Select.Option key={j.job_id} value={String(j.job_id)}>
                #{j.job_id} {j.job_name || ''}
              </Select.Option>
            ))}
          </Select>
        </div>
        {filteredNodes.length > 0 ? (
          <Table
            dataSource={filteredNodes}
            columns={nodeTableColumns}
            rowKey={(r) => `${r.job_id}-${r.id}`}
            size="small"
            scroll={{ x: 900 }}
            pagination={{ pageSize: 20, showSizeChanger: true }}
          />
        ) : (
          <EmptyState description="暂无节点执行记录" />
        )}
      </Card>
    </div>
  );
};

export default AgentMonitorPage;
