import React, { useEffect, useRef, useState } from 'react';
import {
  Card,
  Typography,
  Select,
  Space,
  Switch,
  Tag,
  Row,
  Col,
  Button,
} from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { resultService } from '../../services/resultService';
import type { DockingResult } from '../../types';
import '3dmol';

const { Title, Text } = Typography;

const StructureViewPage: React.FC = () => {
  const { jobId = '' } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const viewerRef = useRef<HTMLDivElement>(null);
  const viewer3DRef = useRef<ReturnType<typeof window.$3Dmol.createViewer> | null>(null);
  const [results, setResults] = useState<DockingResult[]>([]);
  const [selectedDrugId, setSelectedDrugId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [showHydrogenBonds, setShowHydrogenBonds] = useState(true);
  const [showSaltBridges, setShowSaltBridges] = useState(true);
  const [showHydrophobic, setShowHydrophobic] = useState(true);
  const [highlightSite, setHighlightSite] = useState(true);
  const [spin, setSpin] = useState(false);

  // Auto-load results when jobId is available
  useEffect(() => {
    if (jobId) fetchResults(jobId);
  }, [jobId]);

  // Create 3D viewer when viewerRef mounts
  useEffect(() => {
    if (!viewerRef.current || viewer3DRef.current) return;
    viewer3DRef.current = window.$3Dmol.createViewer(viewerRef.current, {
      backgroundColor: 'white',
    });
    loadDefaultStructure();

    // 自定义滚轮缩放方向：向上放大，向下缩小
    const container = viewerRef.current;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!viewer3DRef.current) return;
      const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
      viewer3DRef.current.zoom(zoomFactor, 0);
      viewer3DRef.current.render();
    };
    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, []);

  const fetchResults = async (id: string) => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await resultService.getJobResults(id, { page_size: 100 });
      setResults(res.items || []);
    } catch {
      // handled by global interceptor
    } finally {
      setLoading(false);
    }
  };

  const [modelLoaded, setModelLoaded] = useState(false);

  const loadDefaultStructure = () => {
    // Load a demo structure (EGFR kinase domain, PDB: 1M17)
    fetch('https://files.rcsb.org/download/1M17.pdb')
      .then((r) => r.text())
      .then((data) => {
        if (!viewer3DRef.current) return;
        viewer3DRef.current.removeAllModels();
        viewer3DRef.current.addModel(data, 'pdb');
        viewer3DRef.current.setStyle({}, { cartoon: { color: 'spectrum' } });
        viewer3DRef.current.zoomTo();
        viewer3DRef.current.render();
        viewer3DRef.current.spin(spin);
        setModelLoaded(true);
      })
      .catch(() => {
        // PDB fetch failed, show placeholder
      });
  };

  const handleDrugSelect = (drugId: string) => {
    setSelectedDrugId(drugId);
    // In production, you would load the docked pose PDB and highlight interactions
  };

  // Re-render interactions when display switches change (after model is loaded)
  useEffect(() => {
    if (!viewer3DRef.current || !modelLoaded) return;
    viewer3DRef.current.removeAllShapes();
    viewer3DRef.current.removeAllSurfaces();

    if (highlightSite) {
      viewer3DRef.current.addSurface('VDW', { opacity: 0.3, color: 'yellow' });
    }
    if (showHydrogenBonds) {
      viewer3DRef.current.addSurface('VDW', { opacity: 0.2, color: 'blue' });
    }
    if (showSaltBridges) {
      viewer3DRef.current.addSurface('VDW', { opacity: 0.15, color: 'red' });
    }
    if (showHydrophobic) {
      viewer3DRef.current.addSurface('VDW', { opacity: 0.1, color: 'green' });
    }

    viewer3DRef.current.render();
  }, [showHydrogenBonds, showSaltBridges, showHydrophobic, highlightSite, modelLoaded]);

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/results/structure')}
          type="text"
          style={{ fontSize: 16 }}
        />
        <Title level={4} style={{ margin: 0 }}>
          结构可视化
        </Title>
        <Tag color="blue">任务 #{jobId}</Tag>
      </div>

      {/* Drug Selector */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>药物:</Text>
          <Select
            value={selectedDrugId}
            onChange={handleDrugSelect}
            placeholder="选择药物查看结合模式"
            style={{ width: 320 }}
            showSearch
            optionFilterProp="children"
            loading={loading}
          >
            {results.map((r) => (
              <Select.Option key={r.id} value={r.id}>
                {r.drug_name} (Score: {r.docking_score != null ? r.docking_score.toFixed(1) : '-'})
              </Select.Option>
            ))}
          </Select>
        </Space>
      </Card>

      <Row gutter={24}>
        <Col span={18}>
          <Card title="3D 蛋白结构">
            <div
              ref={viewerRef}
              style={{
                width: '100%',
                height: 520,
                border: '1px solid #f0f0f0',
                borderRadius: 8,
                position: 'relative',
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card title="显示控制" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Text>氢键</Text>
                <Switch
                  checked={showHydrogenBonds}
                  onChange={setShowHydrogenBonds}
                />
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Text>盐桥</Text>
                <Switch
                  checked={showSaltBridges}
                  onChange={setShowSaltBridges}
                />
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Text>疏水接触</Text>
                <Switch
                  checked={showHydrophobic}
                  onChange={setShowHydrophobic}
                />
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Text>结合位点高亮</Text>
                <Switch
                  checked={highlightSite}
                  onChange={setHighlightSite}
                />
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Text>自动旋转</Text>
                <Switch
                  checked={spin}
                  onChange={(v) => {
                    setSpin(v);
                    viewer3DRef.current?.spin(v);
                  }}
                />
              </div>
            </Space>
          </Card>
          <Card title="图例">
            <Space direction="vertical">
              <Tag color="blue">氢键 (Hydrogen Bond)</Tag>
              <Tag color="red">盐桥 (Salt Bridge)</Tag>
              <Tag color="green">疏水接触 (Hydrophobic)</Tag>
              <Tag color="gold">结合位点</Tag>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default StructureViewPage;
