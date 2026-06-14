import React, { useEffect, useState } from 'react';
import {
  Typography,
  Card,
  Row,
  Col,
  Tag,
  Space,
  Spin,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { taskService } from '../services/taskService';
import type { Job } from '../types';
import EmptyState from './EmptyState';

const { Title, Text } = Typography;

interface Props {
  title: string;
  icon: React.ReactNode;
  subtitle: string;
  basePath: string;
  emptyText?: string;
}

const CompletedJobsGrid: React.FC<Props> = ({ title, icon, subtitle, basePath, emptyText }) => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    taskService
      .listJobs({ status: 'COMPLETED', page_size: 50, sort_by: 'created_at_desc' })
      .then((res) => setJobs(res.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">加载已完成任务...</Text>
        </div>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div>
        <Title level={4} style={{ marginBottom: 24 }}>
          {icon} {title}
        </Title>
        <EmptyState description={emptyText || '暂无已完成的筛选任务'} />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          {icon} {title}
        </Title>
        <Text type="secondary" style={{ marginTop: 4, display: 'block' }}>
          {subtitle}
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        {jobs.map((job) => (
          <Col xs={24} sm={12} lg={8} key={job.id}>
            <Card
              hoverable
              onClick={() => navigate(`${basePath}/${job.id}`)}
              style={{ height: '100%', borderRadius: 12 }}
              styles={{ body: { padding: '20px 24px' } }}
            >
              <div style={{ marginBottom: 12 }}>
                <Tag color="green" icon={<CheckCircleOutlined />}>
                  已完成
                </Tag>
              </div>

              <Title level={5} style={{ margin: '0 0 12px 0' }} ellipsis={{ rows: 2 }}>
                {job.job_name || `任务 #${job.id}`}
              </Title>

              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <DatabaseOutlined style={{ color: '#8c8c8c' }} />
                  <Text type="secondary">
                    药物库: {job.total_drugs?.toLocaleString() || '-'} 个分子
                  </Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ExperimentOutlined style={{ color: '#8c8c8c' }} />
                  <Text type="secondary">
                    完成对接: {job.finished_drugs?.toLocaleString() || '-'} 个
                  </Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
                  <Text type="secondary">
                    {job.created_at
                      ? new Date(job.created_at).toLocaleDateString('zh-CN', {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '-'}
                  </Text>
                </div>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default CompletedJobsGrid;
