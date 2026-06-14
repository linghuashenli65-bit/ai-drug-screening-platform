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
} from 'antd';
import {
  ArrowLeftOutlined,
  SearchOutlined,
  TrophyOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { resultService } from '../../services/resultService';
import { taskService } from '../../services/taskService';
import type { DockingResult, Job } from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';

const { Title, Text } = Typography;

const DockingResultsDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [results, setResults] = useState<DockingResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>('ascend');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedDrug, setSelectedDrug] = useState<DockingResult | null>(null);

  useEffect(() => {
    if (jobId) {
      taskService.getJob(jobId).then(setJob).catch(() => {});
    }
  }, [jobId]);

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

  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 70,
      render: (rank: number) =>
        rank <= 3 ? (
          <Tag color={rank === 1 ? 'gold' : rank === 2 ? 'silver' : '#cd7f32'}>
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
            style={{ color: score < -9 ? '#52c41a' : score < -7 ? '#1890ff' : '#faad14' }}
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
        <Button type="link" size="small" onClick={() => { setSelectedDrug(record); setDetailVisible(true); }}>
          详情
        </Button>
      ),
    },
  ];

  if (loading && results.length === 0) return <LoadingState tip="加载 Docking 结果..." />;
  if (error) return <ErrorState message={error} onRetry={fetchResults} />;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/results/docking')}
          type="text"
          style={{ fontSize: 16 }}
        />
        <div style={{ flex: 1 }}>
          <Title level={4} style={{ margin: 0 }}>
            {job?.job_name || `任务 #${jobId}`}
          </Title>
          <Text type="secondary">Docking 对接结果</Text>
        </div>
        <Tag color="blue">共 {total} 条结果</Tag>
      </div>

      {/* Toolbar + Table */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space>
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索药物名称..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onPressEnter={() => { setPage(1); fetchResults(); }}
              style={{ width: 240 }}
            />
            <Button onClick={() => { setPage(1); fetchResults(); }}>搜索</Button>
          </Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => {
              const csv = [
                'Rank,Drug Name,Docking Score (kcal/mol),SMILES',
                ...results.map(
                  (r) => `${r.rank},"${r.drug_name}",${r.docking_score ?? ''},"${r.smiles || ''}"`
                ),
              ].join('\n');
              const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
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
        </div>

        <Table
          dataSource={results}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            pageSizeOptions: ['10', '20', '50', '100'],
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
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
                    color: selectedDrug.docking_score < -9 ? '#52c41a'
                      : selectedDrug.docking_score < -7 ? '#1890ff' : '#faad14',
                  }}
                >
                  {selectedDrug.docking_score.toFixed(2)} kcal/mol
                </Text>
              ) : (
                <Text type="secondary">-</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="排名">{selectedDrug.rank}</Descriptions.Item>
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
                    {ix.type === 'hydrogen_bond' ? '氢键' : ix.type === 'salt_bridge' ? '盐桥' : '疏水接触'}
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

export default DockingResultsDetailPage;
