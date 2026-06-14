import React from 'react';
import { ExperimentOutlined } from '@ant-design/icons';
import CompletedJobsGrid from '../../components/CompletedJobsGrid';

const DockingResultsPage: React.FC = () => {
  return (
    <CompletedJobsGrid
      title="Docking 结果"
      icon={<ExperimentOutlined style={{ marginRight: 8 }} />}
      subtitle="选择一个已完成的筛选任务查看对接结果"
      basePath="/results/docking"
      emptyText="暂无已完成的筛选任务，完成任务后可在此查看对接结果"
    />
  );
};

export default DockingResultsPage;
