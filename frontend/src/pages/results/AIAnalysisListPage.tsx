import React from 'react';
import { RobotOutlined } from '@ant-design/icons';
import CompletedJobsGrid from '../../components/CompletedJobsGrid';

const AIAnalysisListPage: React.FC = () => {
  return (
    <CompletedJobsGrid
      title="AI 分析报告"
      icon={<RobotOutlined style={{ marginRight: 8 }} />}
      subtitle="选择一个已完成的筛选任务查看 AI 分析结果"
      basePath="/results/ai-analysis"
      emptyText="暂无已完成的筛选任务，完成任务后可在此查看 AI 分析报告"
    />
  );
};

export default AIAnalysisListPage;
