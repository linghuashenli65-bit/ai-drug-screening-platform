import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Typography,
  Input,
  Button,
  Space,
  Tag,
  Modal,
  Descriptions,
  Tooltip,
  Select,
} from 'antd';
import {
  SearchOutlined,
  TrophyOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { resultService } from '../../services/resultService';
import { taskService } from '../../services/taskService';
import type { DockingResult, Job } from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import EmptyState from '../../components/EmptyState';

const { Title, Text } = Typography;

const DockingResultsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const defaultJobId = searchParams.get('job') || '';

  const [results, setResults] = useState<DockingResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(
    'ascend'
  ); // lower score = better
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState(defaultJobId);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedDrug, setSelectedDrug] = useState<DockingResult | null>(null);
  const [availableJobs, setAvailableJobs] = useState<Job[]>([]);

  useEffect(() => {
    taskService.listJobs({ page_size: 50 }).then((res) => {
      setAvailableJobs(res.items || []);
    }).catch(() => {});
  }, []);

  const fetchResults = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await resultService.getJobResults(jobId, {
        page,
        page_size: pageSize,
        search: search || undefined,
        sort_by: sortOrder === 'ascend' ? 'score_asc' : 'score_desc',
      });
      setResults(res.items || []);
      setTotal(res.total);
    } catch {
      setError('加载结果失败');
    } finally {
      setLoading(false);
    }
  }, [jobId, page, pageSize, search, sortOrder]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  const showDetail = (drug: DockingResult) => {
    setSelectedDrug(drug);
    setDetailVisible(true);
  };

  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 70,
      render: (rank: number) =>
        rank <= 3 ? (
          <Tag
            color={rank === 1 ? 'gold' : rank === 2 ? 'silver' : '#cd7f32'}
          >
            <TrophyOutlined /> {rank}
          </Tag>
        ) : (
          rank
        ),
    },
    {
      title: '药物名称',
      dataIndex: 'drug_name',
      key: 'drug_name',
      ellipsis: true,
      width: 200,
    },
    {
      title: 'Docking Score',
      dataIndex: 'docking_score',
      key: 'docking_score',
      width: 140,
      sorter: true,
      sortOrder,
      render: (score: number) =>
        score != null ? (
          <Text
            strong
            style={{
              color: score < -9 ? '#52c41a' : score < -7 ? '#1890ff' : '#faad14',
            }}
          >
            {score.toFixed(2)} kcal/mol
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: '结合能',
      dataIndex: 'binding_energy',
      key: 'binding_energy',
      width: 120,
      render: (v?: number) => (v != null ? `${v.toFixed(2)} kcal/mol` : '-'),
    },
    {
      title: 'SMILES',
      dataIndex: 'smiles',
      key: 'smiles',
      ellipsis: true,
      width: 200,
      render: (s?: string) => (
        <Tooltip title={s}>
          <Text ellipsis style={{ maxWidth: 200 }}>
            {s || '-'}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right' as const,
      render: (_: unknown, record: DockingResult) => (
        <Button type="link" size="small" onClick={() => showDetail(record)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        Docking 结果
      </Title>

      {/* Job Selector */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Text strong>选择任务:</Text>
          <Select
            showSearch
            placeholder="选择一个筛选任务"
            value={jobId || undefined}
            onChange={(v) => { setJobId(v); setPage(1); }}
            style={{ width: 360 }}
            optionFilterProp="label"
            options={availableJobs.map((j) => ({
              value: String(j.job_id),
              label: `#${j.job_id} ${j.job_name || ''} (${j.status})`,
            }))}
          />
          <Button type="primary" onClick={() => { setPage(1); fetchResults(); }}>
            查询
          </Button>
        </Space>
      </Card>

      {!jobId ? (
        <EmptyState description="请输入任务 ID 查看 Docking 结果" />
      ) : loading ? (
        <LoadingState tip="加载 Docking 结果中..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchResults} />
      ) : (
        <Card>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: 16,
            }}
          >
            <Space>
              <Input
                prefix={<SearchOutlined />}
                placeholder="搜索药物名称..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onPressEnter={() => { setPage(1); fetchResults(); }}
                style={{ width: 240 }}
              />
              <Button onClick={() => { setPage(1); fetchResults(); }}>
                搜索
              </Button>
            </Space>
            <Space>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => {
                  const csv = [
                    'Rank,Drug Name,Docking Score (kcal/mol),SMILES',
                    ...results.map(
                      (r) =>
                        `${r.rank},"${r.drug_name}",${r.docking_score ?? ''},"${r.smiles || ''}"`
                    ),
                  ].join('\n');
                  const blob = new Blob(['\uFEFF' + csv], {
                    type: 'text/csv;charset=utf-8',
                  });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `docking_results_${jobId}.csv`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                导出 CSV
              </Button>
              <Text type="secondary">共 {total} 条结果</Text>
            </Space>
          </div>

          <Table
            dataSource={results}
            columns={columns}
            rowKey="id"
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 条`,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (p, ps) => {
                setPage(p);
                setPageSize(ps);
              },
            }}
            onChange={(_p, _f, sorter) => {
              if (!Array.isArray(sorter) && sorter.order) {
                setSortOrder(sorter.order as 'ascend' | 'descend');
              } else {
                setSortOrder(null);
              }
            }}
            scroll={{ x: 900 }}
            size="middle"
          />
        </Card>
      )}

      {/* Drug Detail Modal */}
      <Modal
        title="药物详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        {selectedDrug && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="药物名称">
              <Text strong>{selectedDrug.drug_name}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Docking Score">
              {selectedDrug.docking_score != null ? (
                <Text
                  strong
                  style={{
                    color:
                      selectedDrug.docking_score < -9
                        ? '#52c41a'
                        : selectedDrug.docking_score < -7
                        ? '#1890ff'
                        : '#faad14',
                  }}
                >
                  {selectedDrug.docking_score.toFixed(2)} kcal/mol
                </Text>
              ) : (
                <Text type="secondary">-</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="排名">
              {selectedDrug.rank}
            </Descriptions.Item>
            <Descriptions.Item label="SMILES">
              <Text code>{selectedDrug.smiles || '-'}</Text>
            </Descriptions.Item>
            {selectedDrug.binding_energy != null && (
              <Descriptions.Item label="结合能">
                {selectedDrug.binding_energy.toFixed(2)} kcal/mol
              </Descriptions.Item>
            )}
            {selectedDrug.interactions && selectedDrug.interactions.length > 0 && (
              <Descriptions.Item label="相互作用">
                {selectedDrug.interactions.map((ix, i) => (
                  <Tag key={i} color="blue">
                    {ix.type === 'hydrogen_bond'
                      ? '氢键'
                      : ix.type === 'salt_bridge'
                      ? '盐桥'
                      : '疏水接触'}
                    : {ix.residues?.join(', ')}
                  </Tag>
                ))}
              </Descriptions.Item>
            )}
            {selectedDrug.ai_analysis && (
              <Descriptions.Item label="AI 分析">
                <Text>{selectedDrug.ai_analysis}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default DockingResultsPage;
