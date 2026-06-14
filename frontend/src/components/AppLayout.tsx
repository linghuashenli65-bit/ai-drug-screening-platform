import React from 'react';
import { Layout, Menu, Button, Avatar, Dropdown, Badge, Space, Typography } from 'antd';
import {
  DashboardOutlined,
  PlusCircleOutlined,
  UnorderedListOutlined,
  MonitorOutlined,
  ExperimentOutlined,
  EyeOutlined,
  RobotOutlined,
  FileTextOutlined,
  MedicineBoxOutlined,
  SettingOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  FolderOutlined,
  AimOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useUIStore } from '../stores/uiStore';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path?: string;
  roles?: string[];
  children?: MenuItem[];
}

const allMenuItems: MenuItem[] = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard', path: '/dashboard' },
  { key: '/tasks/new', icon: <PlusCircleOutlined />, label: '新建任务', path: '/tasks/new' },
  { key: '/tasks', icon: <UnorderedListOutlined />, label: '任务管理', path: '/tasks' },
  { key: '/projects', icon: <FolderOutlined />, label: '项目管理', path: '/projects' },
  { key: '/receptors', icon: <AimOutlined />, label: '受体管理', path: '/receptors' },
  { key: '/monitor', icon: <MonitorOutlined />, label: 'Agent 监控', path: '/monitor', roles: ['PI', 'ADMIN'] },
  {
    key: 'results',
    icon: <ExperimentOutlined />,
    label: '结果分析',
    children: [
      { key: '/results/docking', icon: <ExperimentOutlined />, label: 'Docking 结果', path: '/results/docking' },
      { key: '/results/structure', icon: <EyeOutlined />, label: '结构可视化', path: '/results/structure' },
      { key: '/results/ai-analysis', icon: <RobotOutlined />, label: 'AI 分析', path: '/results/ai-analysis' },
    ],
  },
  { key: '/reports', icon: <FileTextOutlined />, label: '报告中心', path: '/reports' },
  {
    key: '/drug-library',
    icon: <MedicineBoxOutlined />,
    label: '药物库管理',
    path: '/drug-library',
    roles: ['ADMIN'],
  },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置', path: '/settings', roles: ['ADMIN'] },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasRole } = useAuthStore();
  const { sidebarCollapsed, toggleSidebar, notifications } = useUIStore();

  const filterByRole = (items: MenuItem[]): MenuItem[] =>
    items
      .filter((item) => {
        if (item.roles && item.roles.length > 0) {
          return hasRole(item.roles);
        }
        return true;
      })
      .map((item) => ({
        ...item,
        children: item.children ? filterByRole(item.children) : undefined,
      }));

  const menuItems = filterByRole(allMenuItems);

  const handleMenuClick = (info: { key: string }) => {
    const findItem = (items: MenuItem[]): MenuItem | undefined => {
      for (const item of items) {
        if (item.key === info.key) return item;
        if (item.children) {
          const found = findItem(item.children);
          if (found) return found;
        }
      }
      return undefined;
    };
    const item = findItem(menuItems);
    if (item?.path) navigate(item.path);
  };

  const userDropdownItems = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: '个人中心' },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
    ],
    onClick: ({ key }: { key: string }) => {
      if (key === 'logout') {
        logout();
        navigate('/login');
      }
    },
  };

  const roleLabel: Record<string, string> = {
    ADMIN: '管理员',
    PI: '项目负责人',
    RESEARCHER: '科研人员',
    VIEWER: '访客',
  };

  // Derive selected keys from current path
  const selectedKeys = [location.pathname];
  // Open submenu if current path matches a child
  const openKeys = menuItems
    .filter((item) => item.children?.some((c) => location.pathname.startsWith(c.key)))
    .map((item) => item.key);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={sidebarCollapsed}
        theme="dark"
        width={220}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Text
            strong
            style={{
              color: '#fff',
              fontSize: sidebarCollapsed ? 14 : 16,
              whiteSpace: 'nowrap',
            }}
          >
            {sidebarCollapsed ? 'AI药筛' : 'AI 药物筛选平台'}
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selectedKeys}
          defaultOpenKeys={openKeys}
          items={menuItems.map((item) => ({
            key: item.key,
            icon: item.icon,
            label: item.label,
            children: item.children?.map((c) => ({
              key: c.key,
              icon: c.icon,
              label: c.label,
            })),
          }))}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout style={{ marginLeft: sidebarCollapsed ? 80 : 220, transition: 'all 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            position: 'sticky',
            top: 0,
            zIndex: 9,
          }}
        >
          <Button
            type="text"
            icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleSidebar}
          />
          <Space size={20}>
            <Badge count={notifications.length} size="small">
              <BellOutlined style={{ fontSize: 18, cursor: 'pointer' }} />
            </Badge>
            <Dropdown menu={userDropdownItems} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar
                  size="small"
                  icon={<UserOutlined />}
                  style={{ backgroundColor: '#1890ff' }}
                />
                <span>
                  {user?.username || '用户'}
                  <Text type="secondary" style={{ fontSize: 12, marginLeft: 6 }}>
                    ({roleLabel[user?.role || 'RESEARCHER']})
                  </Text>
                </span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
