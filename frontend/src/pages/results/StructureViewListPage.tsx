import React from 'react';
import { AppstoreOutlined } from '@ant-design/icons';
import CompletedJobsGrid from '../../components/CompletedJobsGrid';

const StructureViewListPage: React.FC = () => {
  return (
    <CompletedJobsGrid
      title="结构可视化"
      icon={<AppstoreOutlined style={{ marginRight: 8 }} />}
      subtitle="选择一个已完成的筛选任务查看 3D 蛋白-配体结构"
      basePath="/results/structure"
      emptyText="暂无已完成的筛选任务，完成任务后可在此查看结构可视化"
    />
  );
};

export default StructureViewListPage;
