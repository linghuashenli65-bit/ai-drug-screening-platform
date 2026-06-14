import React from 'react';
import { Spin } from 'antd';

interface LoadingStateProps {
  tip?: string;
  fullPage?: boolean;
}

const LoadingState: React.FC<LoadingStateProps> = ({
  tip = '加载中...',
  fullPage = false,
}) => {
  if (fullPage) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <Spin size="large" />
        <span style={{ color: '#8c8c8c' }}>{tip}</span>
      </div>
    );
  }
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: 400,
        flexDirection: 'column',
        gap: 16,
      }}
    >
      <Spin size="large" />
      <span style={{ color: '#8c8c8c' }}>{tip}</span>
    </div>
  );
};

export default LoadingState;
