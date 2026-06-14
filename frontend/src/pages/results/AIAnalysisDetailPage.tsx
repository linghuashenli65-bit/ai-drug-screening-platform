import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Card,
  Typography,
  Input,
  Button,
  Space,
  Spin,
  Tag,
  Row,
  Col,
  Avatar,
  Collapse,
  Empty,
} from 'antd';
import {
  ArrowLeftOutlined,
  RobotOutlined,
  UserOutlined,
  SendOutlined,
  BulbOutlined,
  WarningOutlined,
  ExperimentOutlined,
  MedicineBoxOutlined,
  DatabaseOutlined,
  ClockCircleOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { taskService } from '../../services/taskService';
import type { AIAnalysis, ChatMessage, DockingResult, Job } from '../../types';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';

const { Title, Text } = Typography;

// Simple Markdown renderer for LLM output
const MarkdownContent: React.FC<{ content: string }> = ({ content }) => {
  const renderMarkdown = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let listItems: string[] = [];

    const flushList = () => {
      if (listItems.length > 0) {
        elements.push(
          <ul key={`list-${elements.length}`} style={{ paddingLeft: 20, margin: '8px 0' }}>
            {listItems.map((item, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                <span dangerouslySetInnerHTML={{ __html: inlineFormat(item) }} />
              </li>
            ))}
          </ul>
        );
        listItems = [];
      }
    };

    const inlineFormat = (s: string): string => {
      return s
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code style="background:#f5f5f5;padding:1px 4px;border-radius:3px;font-size:0.9em">$1</code>');
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
        const itemText = trimmed.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '');
        listItems.push(itemText);
        continue;
      }

      flushList();

      if (trimmed === '') {
        elements.push(<div key={`br-${i}`} style={{ height: 8 }} />);
      } else if (trimmed.startsWith('###')) {
        elements.push(
          <h4 key={`h-${i}`} style={{ margin: '12px 0 4px', fontSize: 14, fontWeight: 600 }}>
            <span dangerouslySetInnerHTML={{ __html: inlineFormat(trimmed.replace(/^#+\s*/, '')) }} />
          </h4>
        );
      } else if (trimmed.startsWith('##')) {
        elements.push(
          <h3 key={`h-${i}`} style={{ margin: '16px 0 6px', fontSize: 15, fontWeight: 600 }}>
            <span dangerouslySetInnerHTML={{ __html: inlineFormat(trimmed.replace(/^#+\s*/, '')) }} />
          </h3>
        );
      } else if (trimmed.startsWith('#')) {
        elements.push(
          <h2 key={`h-${i}`} style={{ margin: '16px 0 8px', fontSize: 16, fontWeight: 600 }}>
            <span dangerouslySetInnerHTML={{ __html: inlineFormat(trimmed.replace(/^#+\s*/, '')) }} />
          </h2>
        );
      } else {
        elements.push(
          <p key={`p-${i}`} style={{ margin: '4px 0', lineHeight: 1.8 }}>
            <span dangerouslySetInnerHTML={{ __html: inlineFormat(trimmed) }} />
          </p>
        );
      }
    }
    flushList();
    return elements;
  };

  return <div style={{ fontSize: 14, color: '#333' }}>{renderMarkdown(content)}</div>;
};

// Analysis section card config
const SECTIONS = [
  {
    key: 'candidate_analysis',
    title: '候选药物分析',
    icon: <BulbOutlined />,
    color: '#1677ff',
    gradient: 'linear-gradient(135deg, #e8f4fd 0%, #f0f7ff 100%)',
  },
  {
    key: 'drug_repurposing',
    title: '药物重定位分析',
    icon: <MedicineBoxOutlined />,
    color: '#52c41a',
    gradient: 'linear-gradient(135deg, #e8fce8 0%, #f0fff0 100%)',
  },
  {
    key: 'risk_analysis',
    title: '风险分析',
    icon: <WarningOutlined />,
    color: '#fa8c16',
    gradient: 'linear-gradient(135deg, #fff7e6 0%, #fffbe8 100%)',
  },
  {
    key: 'experiment_suggestions',
    title: '实验建议',
    icon: <ExperimentOutlined />,
    color: '#722ed1',
    gradient: 'linear-gradient(135deg, #f3e8ff 0%, #f9f0ff 100%)',
  },
];

const AIAnalysisDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);
  const [topDrugs, setTopDrugs] = useState<DockingResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: '您好，我是 AI 分析助手。您可以针对当前筛选结果提问，例如："排名第一的药物为什么得分最高？"、"哪些药物有重定位潜力？"',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const [jobRes, analysisRes, topRes] = await Promise.all([
        taskService.getJob(jobId),
        api.get<AIAnalysis>(`/screenings/${jobId}/analysis`, { _silent: true } as Record<string, unknown>),
        api.get<{ top_hits?: DockingResult[] }>(`/screenings/${jobId}/results`, {
          params: { n: 10 },
          _silent: true,
        } as Record<string, unknown>),
      ]);
      setJob(jobRes);
      setAnalysis(analysisRes.data);
      const hits = Array.isArray(topRes.data) ? topRes.data : (topRes.data?.top_hits || []);
      setTopDrugs(hits);
    } catch {
      setError('加载分析数据失败');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const sendMessage = async () => {
    const trimmed = chatInput.trim();
    if (!trimmed || !jobId) return;

    const userMsg: ChatMessage = { role: 'user', content: trimmed, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await api.post<{ answer: string }>(`/screenings/${jobId}/analysis/chat`, {
        question: trimmed,
        history: messages.map((m) => ({ role: m.role, content: m.content })),
      });
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.data.answer, timestamp: new Date().toISOString() },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '抱歉，AI 服务暂时不可用，请稍后再试。', timestamp: new Date().toISOString() },
      ]);
    } finally {
      setChatLoading(false);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  };

  if (loading) return <LoadingState tip="加载 AI 分析报告..." />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  const rankColors = ['#faad14', '#a0a0a0', '#cd7f32'];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/results/ai-analysis')}
          type="text"
          style={{ fontSize: 16 }}
        />
        <div style={{ flex: 1 }}>
          <Title level={4} style={{ margin: 0 }}>
            {job?.job_name || `任务 #${jobId}`}
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            AI 智能分析报告
          </Text>
        </div>
        <Tag color="purple" icon={<RobotOutlined />} style={{ fontSize: 13, padding: '2px 10px' }}>
          AI 生成
        </Tag>
      </div>

      {/* Main Content */}
      <Row gutter={20}>
        {/* Left: Report */}
        <Col xs={24} lg={16}>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {SECTIONS.map((section) => {
              const content = analysis?.[section.key as keyof AIAnalysis] as string | undefined;
              return (
                <Card
                  key={section.key}
                  style={{
                    borderRadius: 12,
                    borderTop: `3px solid ${section.color}`,
                    overflow: 'hidden',
                  }}
                  styles={{ body: { padding: '20px 24px' } }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: 8,
                        background: section.gradient,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: section.color,
                        fontSize: 16,
                      }}
                    >
                      {section.icon}
                    </div>
                    <Text strong style={{ fontSize: 15 }}>
                      {section.title}
                    </Text>
                  </div>
                  {content ? (
                    <MarkdownContent content={content} />
                  ) : (
                    <Empty description="暂无分析结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </Card>
              );
            })}
          </Space>
        </Col>

        {/* Right: Sidebar */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" size={16} style={{ width: '100%', position: 'sticky', top: 16 }}>
            {/* Job Summary */}
            <Card
              style={{ borderRadius: 12 }}
              styles={{ body: { padding: '16px 20px' } }}
            >
              <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 12 }}>
                任务概要
              </Text>
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text type="secondary"><DatabaseOutlined /> 药物库</Text>
                  <Text>{job?.total_drugs?.toLocaleString() || '-'} 个分子</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text type="secondary"><ExperimentOutlined /> 完成对接</Text>
                  <Text>{job?.finished_drugs?.toLocaleString() || '-'} 个</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text type="secondary"><ClockCircleOutlined /> 创建时间</Text>
                  <Text>
                    {job?.created_at
                      ? new Date(job.created_at).toLocaleDateString('zh-CN')
                      : '-'}
                  </Text>
                </div>
              </Space>
            </Card>

            {/* Top Hits */}
            <Card
              style={{ borderRadius: 12 }}
              styles={{ body: { padding: '16px 20px' } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <TrophyOutlined style={{ color: '#faad14' }} />
                <Text strong style={{ fontSize: 14 }}>Top Hits</Text>
              </div>
              {topDrugs.length > 0 ? (
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {topDrugs.slice(0, 8).map((drug, idx) => (
                    <div
                      key={drug.id || idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '8px 10px',
                        background: idx < 3 ? '#fafafa' : 'transparent',
                        borderRadius: 8,
                      }}
                    >
                      <div
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: 12,
                          background: idx < 3 ? rankColors[idx] : '#e8e8e8',
                          color: idx < 3 ? '#fff' : '#666',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 12,
                          fontWeight: 600,
                          flexShrink: 0,
                        }}
                      >
                        {idx + 1}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text ellipsis style={{ fontSize: 13, display: 'block' }}>
                          {drug.drug_name}
                        </Text>
                      </div>
                      <Text
                        style={{
                          fontSize: 12,
                          color: (drug.docking_score ?? 0) < -9 ? '#52c41a' : '#1677ff',
                          fontWeight: 500,
                          flexShrink: 0,
                        }}
                      >
                        {drug.docking_score != null ? `${drug.docking_score.toFixed(1)}` : '-'}
                      </Text>
                    </div>
                  ))}
                </Space>
              ) : (
                <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Space>
        </Col>
      </Row>

      {/* AI Chat Section */}
      <div style={{ marginTop: 32 }}>
        <Collapse
          activeKey={chatExpanded ? ['chat'] : []}
          onChange={(keys) => setChatExpanded(keys.includes('chat'))}
          style={{ borderRadius: 12, overflow: 'hidden' }}
          items={[
            {
              key: 'chat',
              label: (
                <Space>
                  <RobotOutlined style={{ color: '#722ed1' }} />
                  <Text strong>追问 AI 助手</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    基于当前筛选结果进行深入探讨
                  </Text>
                </Space>
              ),
              children: (
                <div>
                  <div
                    style={{
                      height: 360,
                      overflow: 'auto',
                      marginBottom: 12,
                      padding: 16,
                      background: '#fafafa',
                      borderRadius: 8,
                    }}
                  >
                    {messages.map((msg, i) => (
                      <div
                        key={i}
                        style={{
                          display: 'flex',
                          justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                          marginBottom: 12,
                        }}
                      >
                        <div style={{ display: 'flex', gap: 8, maxWidth: '80%' }}>
                          {msg.role === 'assistant' && (
                            <Avatar size={28} icon={<RobotOutlined />} style={{ backgroundColor: '#722ed1', flexShrink: 0 }} />
                          )}
                          <div
                            style={{
                              padding: '10px 14px',
                              borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                              background: msg.role === 'user' ? '#1677ff' : '#fff',
                              color: msg.role === 'user' ? '#fff' : '#333',
                              boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                              fontSize: 13,
                              lineHeight: 1.7,
                              whiteSpace: 'pre-wrap',
                            }}
                          >
                            {msg.content}
                          </div>
                          {msg.role === 'user' && (
                            <Avatar size={28} icon={<UserOutlined />} style={{ backgroundColor: '#1677ff', flexShrink: 0 }} />
                          )}
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div style={{ textAlign: 'center', padding: 8 }}>
                        <Spin size="small" />
                        <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                          AI 思考中...
                        </Text>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Input.TextArea
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="输入问题，如：为什么排名第一的药物得分最高？"
                      autoSize={{ minRows: 1, maxRows: 3 }}
                      onPressEnter={(e) => {
                        if (!e.shiftKey) {
                          e.preventDefault();
                          sendMessage();
                        }
                      }}
                    />
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      onClick={sendMessage}
                      loading={chatLoading}
                    >
                      发送
                    </Button>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};

export default AIAnalysisDetailPage;
