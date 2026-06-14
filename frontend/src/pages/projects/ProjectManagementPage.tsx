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
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { projectService } from '../../services/projectService';
import type { ProjectItem } from '../../types';
import LoadingState from '../../components/LoadingState';

const { Title } = Typography;

const ProjectManagementPage: React.FC = () => {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const data = await projectService.list({ page_size: 100 });
      setProjects(data);
    } catch {
      // handled by global interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);
      await projectService.create(values);
      message.success('项目创建成功');
      setModalVisible(false);
      form.resetFields();
      fetchProjects();
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
      title: '项目名称',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 250,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
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
          项目管理
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
        >
          新建项目
        </Button>
      </div>

      <Card>
        {loading ? (
          <LoadingState />
        ) : (
          <Table
            dataSource={projects}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 个项目` }}
          />
        )}
      </Card>

      <Modal
        title="新建项目"
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
            name="project_name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="例如：EGFR 抑制剂筛选" maxLength={100} />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea
              rows={3}
              placeholder="描述项目目标和背景（可选）"
              maxLength={500}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProjectManagementPage;
