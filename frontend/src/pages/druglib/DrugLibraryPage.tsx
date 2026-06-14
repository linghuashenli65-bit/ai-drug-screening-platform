import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Typography,
  Input,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Upload,
  Modal,
  Descriptions,
  message,
  Progress,
  Alert,
} from 'antd';
import {
  SearchOutlined,
  UploadOutlined,
  MedicineBoxOutlined,
  ExperimentOutlined,
  DatabaseOutlined,
  AppstoreAddOutlined,
} from '@ant-design/icons';
import { drugLibService } from '../../services/drugLibService';
import type { Drug, DrugLibStats } from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import EmptyState from '../../components/EmptyState';

const { Title, Text } = Typography;

const DrugLibraryPage: React.FC = () => {
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [sourceFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DrugLibStats | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null);
  const [importVisible, setImportVisible] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState<{
    imported: number;
    errors: string[];
  } | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [drugRes, statsRes] = await Promise.all([
        drugLibService.listDrugs({
          page,
          page_size: pageSize,
          search: search || undefined,
          source: sourceFilter || undefined,
        }),
        drugLibService.getStats(),
      ]);
      setDrugs(drugRes.items || []);
      setTotal(drugRes.total);
      setStats(statsRes);
    } catch {
      setError('加载药物库数据失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, sourceFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const showDetail = async (drugId: number) => {
    try {
      const drug = await drugLibService.getDrug(drugId);
      setSelectedDrug(drug);
      setDetailVisible(true);
    } catch {
      // handled by global interceptor
    }
  };

  const handleImport = async (file: File) => {
    setImportLoading(true);
    setImportResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const result = await drugLibService.uploadDrugCsv(formData);
      setImportResult(result);
      message.success(`成功导入 ${result.imported} 个药物`);
      fetchData();
    } catch {
      // handled by global interceptor
    } finally {
      setImportLoading(false);
    }
    return false;
  };

  const columns = [
    {
      title: '药物名称',
      dataIndex: 'drug_name',
      key: 'name',
      ellipsis: true,
      width: 200,
    },
    {
      title: 'SMILES',
      dataIndex: 'smiles',
      key: 'smiles',
      ellipsis: true,
      width: 220,
    },
    {
      title: '分子量',
      dataIndex: 'molecular_weight',
      key: 'molecular_weight',
      width: 100,
      render: (v?: number) => (v != null ? v.toFixed(2) : '-'),
    },
    {
      title: 'LogP',
      dataIndex: 'logp',
      key: 'logp',
      width: 80,
      render: (v?: number) => (v != null ? v.toFixed(2) : '-'),
    },
    {
      title: 'HBD',
      dataIndex: 'hbd',
      key: 'hbd',
      width: 60,
      render: (v?: number) => v ?? '-',
    },
    {
      title: 'HBA',
      dataIndex: 'hba',
      key: 'hba',
      width: 60,
      render: (v?: number) => v ?? '-',
    },
    {
      title: '来源',
      dataIndex: 'status',
      key: 'source',
      width: 120,
      render: (s: string) => {
        const colors: Record<string, string> = {
          fda_approved: 'green',
          drugbank: 'blue',
          custom: 'orange',
        };
        const labels: Record<string, string> = {
          fda_approved: 'FDA Approved',
          drugbank: 'DrugBank',
          custom: 'Custom',
        };
        return <Tag color={colors[s] || 'default'}>{labels[s] || s}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      width: 80,
      render: (_: unknown, record: Drug) => (
        <Button type="link" size="small" onClick={() => showDetail(record.id)}>
          详情
        </Button>
      ),
    },
  ];

  if (error) return <ErrorState message={error} onRetry={fetchData} />;

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
          药物库管理
        </Title>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={() => setImportVisible(true)}
        >
          导入 CSV
        </Button>
      </div>

      {/* Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="药物总数"
              value={stats?.total_drugs || 0}
              prefix={<MedicineBoxOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="FDA Approved"
              value={stats?.fda_approved || 0}
              prefix={<ExperimentOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="DrugBank"
              value={stats?.drugbank || 0}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Custom"
              value={stats?.custom || 0}
              prefix={<AppstoreAddOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Drug Table */}
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
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索药物名称..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onPressEnter={() => {
                setPage(1);
                fetchData();
              }}
              style={{ width: 240 }}
            />
            <Button
              onClick={() => {
                setPage(1);
                fetchData();
              }}
            >
              搜索
            </Button>
          </Space>
        </div>

        {loading ? (
          <LoadingState />
        ) : drugs.length === 0 ? (
          <EmptyState description="药物库为空" actionText="导入 CSV" onAction={() => setImportVisible(true)} />
        ) : (
          <Table
            dataSource={drugs}
            columns={columns}
            rowKey="id"
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 个药物`,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (p, ps) => {
                setPage(p);
                setPageSize(ps);
              },
            }}
            scroll={{ x: 900 }}
            size="middle"
          />
        )}
      </Card>

      {/* Drug Detail Modal */}
      <Modal
        title="药物详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={600}
      >
        {selectedDrug && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="名称">
              <Text strong>{selectedDrug.drug_name}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="SMILES">
              <Text code>{selectedDrug.smiles}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="分子量">
              {selectedDrug.molecular_weight?.toFixed(2) ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="LogP">
              {selectedDrug.logp?.toFixed(2) ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="氢键供体 (HBD)">
              {selectedDrug.hbd ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="氢键受体 (HBA)">
              {selectedDrug.hba ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="来源">
              <Tag
                color={
                  selectedDrug.status === 'fda_approved'
                    ? 'green'
                    : selectedDrug.status === 'drugbank'
                    ? 'blue'
                    : 'orange'
                }
              >
                {selectedDrug.status}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* Import Modal */}
      <Modal
        title="导入药物库 (CSV)"
        open={importVisible}
        onCancel={() => {
          setImportVisible(false);
          setImportResult(null);
        }}
        footer={null}
      >
        <div style={{ padding: '24px 0' }}>
          <Upload.Dragger
            accept=".csv"
            maxCount={1}
            beforeUpload={(file) => {
              handleImport(file);
              return false;
            }}
            showUploadList={false}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 32 }} />
            </p>
            <p className="ant-upload-text">点击或拖拽 CSV 文件到此区域</p>
            <p className="ant-upload-hint">
              CSV 应包含: name, smiles (必填), molecular_weight, logp (可选)
            </p>
          </Upload.Dragger>

          {importLoading && (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Progress percent={50} status="active" />
              <Text type="secondary">正在导入...</Text>
            </div>
          )}

          {importResult && (
            <div style={{ marginTop: 16 }}>
              <Alert
                type={importResult.errors.length > 0 ? 'warning' : 'success'}
                message={`成功导入 ${importResult.imported} 个药物`}
                description={
                  importResult.errors.length > 0 &&
                  importResult.errors.slice(0, 5).map((e, i) => (
                    <div key={i}>
                      <Text type="danger">{e}</Text>
                    </div>
                  ))
                }
              />
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default DrugLibraryPage;
