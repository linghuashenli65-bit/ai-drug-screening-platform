import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Badge,
  Button,
  Typography,
  Select,
  Input,
  Space,
  Card,
} from 'antd';
import { EyeOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { taskService } from '../../services/taskService';
import type { Job, JobStatus, JobListParams } from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import EmptyState from '../../components/EmptyState';

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

const TaskListPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<JobStatus | ''>('');
  const [search, setSearch] = useState('');
  const [committedSearch, setCommittedSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: JobListParams = { page, page_size: pageSize };
      if (statusFilter) params.status = statusFilter as JobStatus;
      if (committedSearch) params.search = committedSearch;
      const res = await taskService.listJobs(params);
      setJobs(res.items || []);
      setTotal(res.total);
    } catch {
      setError('加载任务列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter, committedSearch]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 80,
    },
    {
      title: '任务名称',
      dataIndex: 'job_name',
      key: 'job_name',
      ellipsis: true,
      width: 220,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: JobStatus) => (
        <Badge
          status={
            statusColorMap[status] as
              | 'default'
              | 'processing'
              | 'success'
              | 'error'
              | 'warning'
          }
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
      fixed: 'right' as const,
      width: 100,
      render: (_: unknown, record: Job) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/tasks/${record.job_id}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  if (error) return <ErrorState message={error} onRetry={fetchJobs} />;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        任务管理
      </Title>
      <Card>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: 16,
            gap: 16,
            flexWrap: 'wrap',
          }}
        >
          <Space>
            <Select
              value={statusFilter}
              onChange={(v) => {
                setStatusFilter(v);
                setPage(1);
              }}
              placeholder="按状态筛选"
              allowClear
              style={{ width: 160 }}
            >
              {Object.entries(statusLabelMap).map(([key, label]) => (
                <Select.Option key={key} value={key}>
                  {label}
                </Select.Option>
              ))}
            </Select>
            <Input
              placeholder="搜索任务名称..."
              prefix={<SearchOutlined />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onPressEnter={() => { setCommittedSearch(search.trim()); setPage(1); }}
              allowClear
              onClear={() => { setSearch(''); setCommittedSearch(''); setPage(1); }}
              style={{ width: 200 }}
            />
          </Space>
          <Button type="primary" onClick={() => navigate('/tasks/new')}>
            新建任务
          </Button>
        </div>

        {loading ? (
          <LoadingState />
        ) : jobs.length === 0 ? (
          <EmptyState
            description="暂无任务"
            actionText="创建第一个任务"
            onAction={() => navigate('/tasks/new')}
          />
        ) : (
          <Table
            dataSource={jobs}
            columns={columns}
            rowKey="job_id"
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 条`,
              onChange: (p, ps) => {
                setPage(p);
                setPageSize(ps);
              },
            }}
            scroll={{ x: 900 }}
          />
        )}
      </Card>
    </div>
  );
};

export default TaskListPage;
