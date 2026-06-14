import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import ForbiddenPage from './pages/auth/ForbiddenPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import CreateTaskPage from './pages/tasks/CreateTaskPage';
import TaskListPage from './pages/tasks/TaskListPage';
import TaskDetailPage from './pages/tasks/TaskDetailPage';
import AgentMonitorPage from './pages/monitor/AgentMonitorPage';
import DockingResultsPage from './pages/results/DockingResultsPage';
import DockingResultsDetailPage from './pages/results/DockingResultsDetailPage';
import StructureViewListPage from './pages/results/StructureViewListPage';
import StructureViewPage from './pages/results/StructureViewPage';
import AIAnalysisListPage from './pages/results/AIAnalysisListPage';
import AIAnalysisDetailPage from './pages/results/AIAnalysisDetailPage';
import ReportCenterPage from './pages/reports/ReportCenterPage';
import DrugLibraryPage from './pages/druglib/DrugLibraryPage';
import ProjectManagementPage from './pages/projects/ProjectManagementPage';
import ReceptorManagementPage from './pages/receptors/ReceptorManagementPage';
import SettingsPage from './pages/settings/SettingsPage';

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/403" element={<ForbiddenPage />} />

          {/* Protected routes with AppLayout wrapper */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="tasks/new" element={<CreateTaskPage />} />
            <Route path="tasks" element={<TaskListPage />} />
            <Route path="tasks/:jobId" element={<TaskDetailPage />} />
            <Route
              path="monitor"
              element={
                <ProtectedRoute roles={['PI', 'ADMIN']}>
                  <AgentMonitorPage />
                </ProtectedRoute>
              }
            />
            <Route path="results/docking" element={<DockingResultsPage />} />
            <Route path="results/docking/:jobId" element={<DockingResultsDetailPage />} />
            <Route path="results/structure" element={<StructureViewListPage />} />
            <Route path="results/structure/:jobId" element={<StructureViewPage />} />
            <Route path="results/ai-analysis" element={<AIAnalysisListPage />} />
            <Route path="results/ai-analysis/:jobId" element={<AIAnalysisDetailPage />} />
            <Route path="reports" element={<ReportCenterPage />} />
            <Route path="projects" element={<ProjectManagementPage />} />
            <Route path="receptors" element={<ReceptorManagementPage />} />
            <Route
              path="drug-library"
              element={
                <ProtectedRoute roles={['ADMIN']}>
                  <DrugLibraryPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="settings"
              element={
                <ProtectedRoute roles={['ADMIN']}>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
