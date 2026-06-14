import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Typography,
  Descriptions,
  Progress,
  Tag,
  Button,
  Modal,
  Space,
  Spin,
  Row,
  Col,
  Statistic,
  Empty,
  Alert,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ArrowLeftOutlined,
  StopOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { taskService } from '../../services/taskService';
import { useSSE } from '../../hooks/useSSE';
import type {
  AgentNode,
  Job,
  JobStatus,
  AgentNodeState,
} from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';

const { Title, Text } = Typography;

const AGENT_CHAIN = [
  { id: 'planner', name: 'Planner Agent', label: '任务规划', description: '分析任务，规划执行流程' },
  { id: 'prepare_ligand', name: 'Molecule Agent', label: '分子准备', description: '解析SMILES/SDF，生成3D构象' },
  { id: 'load_library', name: 'Database Agent', label: '数据库加载', description: '加载药物库，建立索引' },
  { id: 'docking', name: 'Docking Agent', label: 'Docking 执行', description: '调用AutoDock Vina' },
  { id: 'ranking', name: 'Ranking Agent', label: '结果排序', description: '按Score排序，筛选Top N' },
  { id: 'analysis', name: 'Analysis Agent', label: 'AI 分析', description: 'LLM分析候选药物' },
  { id: 'report', name: 'Report Agent', label: '报告生成', description: '生成PDF报告' },
];

// Per FE-05 spec: CREATED=灰, PREPARING=蓝, DOCKING=橙, ANALYZING=紫, REPORTING=青, COMPLETED=绿, FAILED=红
const statusConfig: Record<JobStatus, { color: string; icon: React.ReactNode }> = {
  CREATED: { color: 'default', icon: <ClockCircleOutlined /> },
  PREPARING: { color: 'blue', icon: <SyncOutlined spin /> },
  DOCKING: { color: 'orange', icon: <SyncOutlined spin /> },
  ANALYZING: { color: 'purple', icon: <SyncOutlined spin /> },
  REPORTING: { color: 'cyan', icon: <SyncOutlined spin /> },
  COMPLETED: { color: 'success', icon: <CheckCircleOutlined /> },
  FAILED: { color: 'error', icon: <CloseCircleOutlined /> },
  CANCELLED: { color: 'warning', icon: <ExclamationCircleOutlined /> },
  WAIT_HUMAN: { color: 'warning', icon: <ExclamationCircleOutlined /> },
};

const nodeStateIcons: Record<AgentNodeState, React.ReactNode> = {
  PENDING: <ClockCircleOutlined style={{ color: '#d9d9d9' }} />,
  RUNNING: <SyncOutlined spin style={{ color: '#1890ff' }} />,
  SUCCESS: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  FAILED: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
  RETRYING: <SyncOutlined spin style={{ color: '#faad14' }} />,
};

const nodeStateColors: Record<AgentNodeState, string> = {
  PENDING: '#d9d9d9',
  RUNNING: '#1890ff',
  SUCCESS: '#52c41a',
  FAILED: '#ff4d4f',
  RETRYING: '#faad14',
};

function formatDuration(ms?: number): string {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}min`;
}

const TaskDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [nodes, setNodes] = useState<AgentNode[]>([]);
  const [nodeLogs, setNodeLogs] = useState<string[]>([]);
  const [logsVisible, setLogsVisible] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);

  const { subscribe } = useSSE(jobId || null);

  const fetchJob = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const [data, nodeData] = await Promise.all([
        taskService.getJob(jobId),
        taskService.getJobNodes(jobId),
      ]);
      setJob(data);
      setNodes(nodeData);
    } catch {
      setError('加载任务详情失败');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  // Listen for SSE updates
  useEffect(() => {
    subscribe((msg) => {
      if (msg.type === 'progress' && msg.data.job) {
        setJob((prev) => (prev ? { ...prev, ...(msg.data.job as Partial<Job>) } : prev));
        // Refresh nodes to reflect new status
        if (jobId) taskService.getJobNodes(jobId).then(setNodes).catch(() => {});
      }
      if (msg.type === 'node_update') {
        if (jobId) taskService.getJobNodes(jobId).then(setNodes).catch(() => {});
      }
      if (msg.type === 'complete') {
        fetchJob();
      }
    });
  }, [subscribe, fetchJob]);

  const handleNodeClick = async (nodeId: string) => {
    if (!jobId) return;
    setSelectedNodeId(nodeId);
    setLogsVisible(true);
    setLogsLoading(true);
    try {
      const logs = await taskService.getNodeLogs(jobId, nodeId);
      setNodeLogs(logs);
    } catch {
      setNodeLogs(['无法加载日志']);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!jobId) return;
    Modal.confirm({
      title: '确认取消任务？',
      content: '取消后任务将无法恢复',
      okText: '确认取消',
      cancelText: '返回',
      okType: 'danger',
      onOk: async () => {
        await taskService.cancelJob(jobId);
        fetchJob();
      },
    });
  };

  if (loading) return <LoadingState tip="加载任务详情中..." />;
  if (error) return <ErrorState message={error} onRetry={fetchJob} />;
  if (!job) return <ErrorState message="任务不存在" />;

  const sc = statusConfig[job.status] || statusConfig.CREATED;
  const isTerminal = ['COMPLETED', 'FAILED', 'CANCELLED'].includes(job.status);

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/tasks')}
          />
          <Title level={4} style={{ margin: 0 }}>
            {job.job_name || `任务 #${job.job_id}`}
          </Title>
          <Tag color={sc.color}>{job.status}</Tag>
        </Space>
        <Space>
          {!isTerminal && (
            <Button danger icon={<StopOutlined />} onClick={handleCancel}>
              取消任务
            </Button>
          )}
        </Space>
      </div>

      {/* Error Alert */}
      {job.status === 'FAILED' && job.error_message && (
        <Alert
          type="error"
          message="任务执行失败"
          description={job.error_message}
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Status & Progress */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="进度" value={job.progress} suffix="%" />
            <Progress
              percent={job.progress}
              status={job.status === 'FAILED' ? 'exception' : job.status === 'COMPLETED' ? 'success' : 'active'}
              showInfo={false}
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="创建时间"
              value={job.created_at ? new Date(job.created_at).toLocaleString('zh-CN') : '-'}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="总药物数" value={job.total_drugs || 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="已完成" value={job.finished_drugs || 0} suffix={`/ ${job.total_drugs || 0}`} />
          </Card>
        </Col>
      </Row>

      {/* Job Info */}
      <Card title="任务信息" style={{ marginBottom: 24 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="任务 ID">{job.job_id}</Descriptions.Item>
          <Descriptions.Item label="任务名称">{job.job_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="项目 ID">{job.project_id}</Descriptions.Item>
          <Descriptions.Item label="受体 ID">{job.receptor_id}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {job.created_at ? new Date(job.created_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          {job.smiles && (
            <Descriptions.Item label="SMILES">{job.smiles}</Descriptions.Item>
          )}
          {job.drug_db && (
            <Descriptions.Item label="药物数据库">{job.drug_db}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* Agent Execution Chain */}
      <Card title="Agent 执行链路" style={{ marginBottom: 24 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'flex-start',
            gap: 16,
            flexWrap: 'wrap',
            padding: '24px 0',
          }}
        >
          {AGENT_CHAIN.map((agent, index) => {
            const node = nodes.find((n) => n.id === agent.id) || {
              id: agent.id,
              name: agent.name,
              label: agent.label,
              state: 'PENDING' as AgentNodeState,
              retry_count: 0,
            };

            return (
              <React.Fragment key={agent.id}>
                {/* Connector Arrow */}
                {index > 0 && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      fontSize: 20,
                      color: '#bbb',
                      marginTop: 24,
                    }}
                  >
                    →
                  </div>
                )}

                {/* Node Card */}
                <div
                  onClick={() => handleNodeClick(agent.id)}
                  style={{
                    cursor: 'pointer',
                    border: `2px solid ${nodeStateColors[node.state]}`,
                    borderRadius: 12,
                    padding: '16px 20px',
                    minWidth: 140,
                    textAlign: 'center',
                    background:
                      node.state === 'RUNNING' ? '#e6f7ff' : '#fff',
                    transition: 'all 0.3s',
                    boxShadow:
                      node.state === 'RUNNING'
                        ? '0 0 12px rgba(24,144,255,0.3)'
                        : '0 1px 4px rgba(0,0,0,0.08)',
                  }}
                >
                  <div style={{ fontSize: 24, marginBottom: 8 }}>
                    {nodeStateIcons[node.state]}
                  </div>
                  <Text strong style={{ display: 'block', fontSize: 14 }}>
                    {agent.label}
                  </Text>
                  <Text
                    type="secondary"
                    style={{ display: 'block', fontSize: 11, marginTop: 4 }}
                  >
                    {agent.description}
                  </Text>
                  {node.duration_ms !== undefined && (
                    <Text
                      type="secondary"
                      style={{ display: 'block', fontSize: 11, marginTop: 4 }}
                    >
                      耗时: {formatDuration(node.duration_ms)}
                    </Text>
                  )}
                  {node.retry_count > 0 && (
                    <Tag color="orange" style={{ marginTop: 4, fontSize: 10 }}>
                      重试 {node.retry_count}次
                    </Tag>
                  )}
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </Card>

      {/* Results quick link */}
      {job.status === 'COMPLETED' && (
        <Card>
          <Space>
            <Button type="primary" onClick={() => navigate(`/results/docking?job=${jobId}`)}>
              查看 Docking 结果
            </Button>
            <Button onClick={() => navigate(`/results/ai-analysis?job=${jobId}`)}>
              查看 AI 分析
            </Button>
            <Button onClick={() => navigate(`/reports?job=${jobId}`)}>
              下载报告
            </Button>
          </Space>
        </Card>
      )}

      {/* Node Logs Modal */}
      <Modal
        title={`节点日志 - ${AGENT_CHAIN.find((n) => n.id === selectedNodeId)?.label || ''}`}
        open={logsVisible}
        onCancel={() => setLogsVisible(false)}
        footer={null}
        width={700}
      >
        {logsLoading ? (
          <Spin />
        ) : nodeLogs.length === 0 ? (
          <Empty description="暂无日志" />
        ) : (
          <div
            style={{
              background: '#1e1e1e',
              color: '#d4d4d4',
              padding: 16,
              borderRadius: 8,
              fontFamily: 'Consolas, monospace',
              fontSize: 13,
              maxHeight: 400,
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {nodeLogs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TaskDetailPage;
