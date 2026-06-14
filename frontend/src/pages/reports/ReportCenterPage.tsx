import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Typography,
  Button,
  Space,
  Modal,
  message,
  Tooltip,
  Badge,
} from 'antd';
import {
  FileTextOutlined,
  DownloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { taskService } from '../../services/taskService';
import { reportService } from '../../services/reportService';
import type { Job, JobStatus } from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import EmptyState from '../../components/EmptyState';

const { Title } = Typography;

const statusLabel: Record<string, string> = {
  COMPLETED: '已完成',
  FAILED: '失败',
  CANCELLED: '已取消',
};

const ReportCenterPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await taskService.listJobs({ page_size: 50, status: 'COMPLETED' as JobStatus });
      setJobs(res.items || []);
    } catch {
      setError('加载任务列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handlePreview = async (jobId: number) => {
    setPreviewVisible(true);
    setPreviewLoading(true);
    setPreviewHtml('');
    try {
      const res = await reportService.getReportPreview(String(jobId));
      setPreviewHtml(res);
    } catch {
      setPreviewHtml('<div style="text-align:center;padding:40px;color:#999">加载报告失败</div>');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleDownload = async (jobId: number, format: 'html' | 'markdown') => {
    try {
      const blob = await reportService.downloadReport(String(jobId), format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${jobId}.${format === 'html' ? 'html' : 'md'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success('下载成功');
    } catch {
      // handled by global interceptor
    }
  };

  const columns = [
    {
      title: '任务 ID',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 80,
    },
    {
      title: '任务名称',
      dataIndex: 'job_name',
      key: 'job_name',
      ellipsis: true,
      width: 280,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => (
        <Badge status="success" text={statusLabel[s] || s} />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t?: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      width: 220,
      render: (_: unknown, record: Job) => (
        <Space>
          <Tooltip title="预览报告">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handlePreview(record.job_id)}
            >
              预览
            </Button>
          </Tooltip>
          <Tooltip title="下载 HTML 报告">
            <Button
              type="link"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record.job_id, 'html')}
            >
              HTML
            </Button>
          </Tooltip>
          <Tooltip title="导出 Markdown">
            <Button
              type="link"
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => handleDownload(record.job_id, 'markdown')}
            >
              MD
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  if (error) return <ErrorState message={error} onRetry={fetchJobs} />;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        报告中心
      </Title>

      <Card>
        {loading ? (
          <LoadingState />
        ) : jobs.length === 0 ? (
          <EmptyState description="暂无已完成的任务，任务完成后可在此下载报告" />
        ) : (
          <Table
            dataSource={jobs}
            columns={columns}
            rowKey="job_id"
            pagination={{
              pageSize: 20,
              showTotal: (t) => `共 ${t} 个已完成任务`,
            }}
            scroll={{ x: 800 }}
          />
        )}
      </Card>

      {/* Report Preview Modal */}
      <Modal
        title="报告预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        width={900}
        footer={null}
        styles={{ body: { height: 600, padding: 0 } }}
      >
        {previewLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <LoadingState tip="加载报告中..." />
          </div>
        ) : (
          <iframe
            srcDoc={previewHtml}
            style={{ width: '100%', height: 580, border: 'none' }}
            title="Report Preview"
            sandbox="allow-same-origin allow-scripts"
          />
        )}
      </Modal>
    </div>
  );
};

export default ReportCenterPage;
