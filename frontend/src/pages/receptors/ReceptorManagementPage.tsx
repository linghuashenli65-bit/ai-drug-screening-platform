import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Typography,
  Button,
  Modal,
  Form,
  Input,
  message,
  Tag,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { receptorService } from '../../services/receptorService';
import type { Receptor } from '../../types';
import LoadingState from '../../components/LoadingState';

const { Title } = Typography;

const ReceptorManagementPage: React.FC = () => {
  const [receptors, setReceptors] = useState<Receptor[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  const fetchReceptors = async () => {
    setLoading(true);
    try {
      const data = await receptorService.list({ page_size: 100 });
      setReceptors(data);
    } catch {
      // handled by global interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReceptors();
  }, []);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);
      await receptorService.create(values);
      message.success('受体创建成功');
      setModalVisible(false);
      form.resetFields();
      fetchReceptors();
    } catch {
      // validation or API error
    } finally {
      setCreating(false);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '受体名称',
      dataIndex: 'receptor_name',
      key: 'receptor_name',
      width: 200,
    },
    {
      title: 'PDB Code',
      dataIndex: 'pdb_code',
      key: 'pdb_code',
      width: 120,
      render: (v?: string) => (v ? <Tag color="blue">{v}</Tag> : '-'),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'PDBQT',
      dataIndex: 'pdbqt_uri',
      key: 'pdbqt_uri',
      width: 100,
      render: (v?: string) =>
        v ? <Tag color="green">已上传</Tag> : <Tag color="orange">未上传</Tag>,
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
          受体管理
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
        >
          新建受体
        </Button>
      </div>

      <Card>
        {loading ? (
          <LoadingState />
        ) : (
          <Table
            dataSource={receptors}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 个受体` }}
          />
        )}
      </Card>

      <Modal
        title="新建受体"
        open={modalVisible}
        onOk={handleCreate}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="receptor_name"
            label="受体名称"
            rules={[{ required: true, message: '请输入受体名称' }]}
          >
            <Input placeholder="例如：EGFR (Epidermal Growth Factor Receptor)" maxLength={100} />
          </Form.Item>
          <Form.Item name="pdb_code" label="PDB Code">
            <Input placeholder="例如：1M17（可选，从 PDB 数据库获取）" maxLength={10} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea
              rows={3}
              placeholder="描述靶点蛋白的功能和结合位点信息（可选）"
              maxLength={500}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReceptorManagementPage;
