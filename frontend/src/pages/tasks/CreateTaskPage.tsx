import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  Button,
  Card,
  Typography,
  Slider,
  InputNumber,
  Collapse,
  message,
  Space,
  Row,
  Col,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { taskService } from '../../services/taskService';
import { receptorService } from '../../services/receptorService';
import { projectService } from '../../services/projectService';
import type { Receptor, ProjectItem } from '../../types';

const { Title, Text } = Typography;
const { Panel } = Collapse;
const { Option } = Select;

const SMILES_REGEX = /^[CHONPSFIBrClchonpsfibclr\[\]\(\)=#@+\-\\.\d\s%]+$/;

interface SMILESValidation {
  valid: boolean;
  error?: string;
}

function validateSMILES(smiles: string): SMILESValidation {
  if (!smiles.trim()) return { valid: true };
  if (!SMILES_REGEX.test(smiles)) {
    return { valid: false, error: 'SMILES 包含无效字符' };
  }
  let depth = 0;
  for (const ch of smiles) {
    if (ch === '(' || ch === '[') depth++;
    if (ch === ')' || ch === ']') depth--;
    if (depth < 0) return { valid: false, error: '括号不匹配' };
  }
  if (depth !== 0) return { valid: false, error: '括号不匹配' };
  return { valid: true };
}

const CreateTaskPage: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [smilesValidation, setSmilesValidation] = useState<SMILESValidation>({ valid: true });
  const [receptors, setReceptors] = useState<Receptor[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [receptorsLoading, setReceptorsLoading] = useState(true);
  const [projectsLoading, setProjectsLoading] = useState(true);

  useEffect(() => {
    receptorService
      .list({ page_size: 100 })
      .then(setReceptors)
      .catch(() => {})
      .finally(() => setReceptorsLoading(false));

    projectService
      .list({ page_size: 100 })
      .then(setProjects)
      .catch(() => {})
      .finally(() => setProjectsLoading(false));
  }, []);

  const onSMILESChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const result = validateSMILES(e.target.value);
    setSmilesValidation(result);
  };

  const onFinish = async (values: Record<string, unknown>) => {
    const smiles = (values.smiles as string)?.trim();
    if (!smiles) {
      message.error('请填写 SMILES');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        project_id: Number(values.project_id),
        smiles,
        receptor_id: Number(values.receptor_id),
        job_name: (values.job_name as string) || undefined,
        drug_db: (values.drug_db as 'fda_approved' | 'drugbank' | 'custom') || undefined,
        exhaustiveness: values.exhaustiveness as number | undefined,
        cpu_count: values.cpu_count as number | undefined,
        top_n: values.top_n as number | undefined,
      };

      const res = await taskService.createJob(payload);
      message.success('任务创建成功');
      navigate(`/tasks/${res.job_id}`);
    } catch {
      // handled by global interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        创建筛选任务
      </Title>

      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{
          drug_db: 'fda_approved',
          exhaustiveness: 8,
          cpu_count: 4,
          top_n: 20,
        }}
      >
        {/* Project & Job Name */}
        <Card title="基本信息" style={{ marginBottom: 16 }}>
          <Form.Item
            name="project_id"
            label="所属项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select
              placeholder="选择项目..."
              showSearch
              optionFilterProp="children"
              loading={projectsLoading}
              notFoundContent={projectsLoading ? '加载中...' : <span>暂无项目，<a href="/projects">去创建</a></span>}
            >
              {projects.map((p) => (
                <Option key={p.id} value={p.id}>
                  <Text strong>{p.project_name}</Text>
                  {p.description && (
                    <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                      — {p.description}
                    </Text>
                  )}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="job_name" label="任务名称">
            <Input placeholder="留空则自动生成任务名称" maxLength={255} />
          </Form.Item>
        </Card>

        {/* SMILES Input */}
        <Card title="分子输入" style={{ marginBottom: 16 }}>
          <Form.Item
            name="smiles"
            label="SMILES 字符串"
            rules={[{ required: true, message: '请输入配体 SMILES' }]}
            validateStatus={smilesValidation.valid ? undefined : 'error'}
            help={smilesValidation.error}
          >
            <Input.TextArea
              rows={3}
              placeholder="例如: COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4 (Gefitinib)"
              onChange={onSMILESChange}
            />
          </Form.Item>
        </Card>

        {/* Target Protein */}
        <Card title="靶点蛋白选择" style={{ marginBottom: 16 }}>
          <Form.Item
            name="receptor_id"
            label="靶点蛋白"
            rules={[{ required: true, message: '请选择靶点蛋白' }]}
          >
            <Select
              placeholder="选择靶点蛋白..."
              showSearch
              optionFilterProp="children"
              loading={receptorsLoading}
              notFoundContent={receptorsLoading ? '加载中...' : <span>暂无受体，<a href="/receptors">去创建</a></span>}
            >
              {receptors.map((r) => (
                <Option key={r.id} value={r.id}>
                  <div>
                    <Text strong>{r.receptor_name}</Text>
                    {r.pdb_code && (
                      <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                        PDB: {r.pdb_code}
                      </Text>
                    )}
                    {r.description && (
                      <>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {r.description}
                        </Text>
                      </>
                    )}
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Card>

        {/* Drug Database */}
        <Card title="药物数据库" style={{ marginBottom: 16 }}>
          <Form.Item name="drug_db" label="药物库来源">
            <Select>
              <Option value="fda_approved">
                <div>
                  <Text strong>FDA Approved</Text>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
                    FDA 已批准药物 (已导入 2,139 个分子)
                  </Text>
                </div>
              </Option>
              <Option value="drugbank">
                <Text strong>DrugBank</Text>
              </Option>
              <Option value="custom">
                <Text strong>自定义药物库</Text>
              </Option>
            </Select>
          </Form.Item>
        </Card>

        {/* Advanced Options */}
        <Collapse ghost style={{ marginBottom: 24 }}>
          <Panel header="高级选项" key="advanced">
            <Row gutter={24}>
              <Col span={12}>
                <Form.Item name="exhaustiveness" label="Exhaustiveness (搜索深度)">
                  <Slider min={1} max={32} marks={{ 1: '1', 8: '8', 16: '16', 32: '32' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="cpu_count" label="CPU 数量">
                  <InputNumber min={1} max={32} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="top_n" label="Top N (返回最高分结果数)">
              <InputNumber min={1} max={1000} style={{ width: '100%' }} />
            </Form.Item>
          </Panel>
        </Collapse>

        <div style={{ textAlign: 'center' }}>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading} icon={<PlusOutlined />} size="large">
              开始筛选
            </Button>
            <Button size="large" onClick={() => navigate(-1)}>
              取消
            </Button>
          </Space>
        </div>
      </Form>
    </div>
  );
};

export default CreateTaskPage;
