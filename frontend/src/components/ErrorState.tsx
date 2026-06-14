import React from 'react';
import { Result, Button } from 'antd';

interface ErrorStateProps {
  message?: string;
  subTitle?: string;
  onRetry?: () => void;
}

const ErrorState: React.FC<ErrorStateProps> = ({
  message = '加载失败',
  subTitle = '请稍后再试，或联系管理员',
  onRetry,
}) => {
  return (
    <Result
      status="error"
      title={message}
      subTitle={subTitle}
      extra={
        onRetry && (
          <Button type="primary" onClick={onRetry}>
            重试
          </Button>
        )
      }
    />
  );
};

export default ErrorState;
