import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Table,
  Button,
  Typography,
  Badge,
} from 'antd';
import {
  ExperimentOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { taskService } from '../../services/taskService';
import type { DashboardStats, Job, JobStatus } from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';

const { Title } = Typography;

const statusColorMap: Record<JobStatus, string> = {
  CREATED: 'default',
  PREPARING: 'blue',
  DOCKING: 'processing',
  ANALYZING: 'purple',
  REPORTING: 'orange',
  COMPLETED: 'success',
  FAILED: 'error',
  CANCELLED: 'warning',
  WAIT_HUMAN: 'warning',
};

const statusLabelMap: Record<JobStatus, string> = {
  CREATED: '已创建',
  PREPARING: '准备中',
  DOCKING: '对接中',
  ANALYZING: '分析中',
  REPORTING: '报告生成中',
  COMPLETED: '已完成',
  FAILED: '失败',
  CANCELLED: '已取消',
  WAIT_HUMAN: '等待确认',
};

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, jobsRes] = await Promise.all([
        taskService.getStats(),
        taskService.listJobs({ page: 1, page_size: 10 }),
      ]);
      setStats(statsRes);
      setRecentJobs(jobsRes.items || []);
    } catch {
      setError('无法加载数据');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) return <LoadingState tip="加载Dashboard中..." />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  const columns = [
    {
      title: 'ID',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 60,
    },
    {
      title: '任务名称',
      dataIndex: 'job_name',
      key: 'job_name',
      ellipsis: true,
      width: 200,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: JobStatus) => (
        <Badge
          status={statusColorMap[status] as 'default' | 'processing' | 'success' | 'error' | 'warning'}
          text={statusLabelMap[status]}
        />
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 80,
      render: (p: number) => `${p}%`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t: string) => new Date(t).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: Job) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/tasks/${record.job_id}`)}
        >
          查看
        </Button>
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
          Dashboard
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/tasks/new')}
        >
          新建任务
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={stats?.total_jobs || 0}
              prefix={<ExperimentOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="运行中"
              value={stats?.running_jobs || 0}
              prefix={<SyncOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="已完成"
              value={stats?.completed_jobs || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="失败"
              value={stats?.failed_jobs || 0}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="最近任务"
        style={{ marginTop: 24 }}
        extra={
          <Button type="link" onClick={() => navigate('/tasks')}>
            查看全部
          </Button>
        }
      >
        <Table
          dataSource={recentJobs}
          columns={columns}
          rowKey="job_id"
          pagination={false}
          size="middle"
        />
      </Card>
    </div>
  );
};

export default DashboardPage;
