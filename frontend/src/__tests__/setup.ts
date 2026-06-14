/**
 * 前端 Test Setup - Vitest + React Testing Library
 *
 * 配置:
 * - jsdom 环境
 * - @testing-library/jest-dom 扩展匹配器
 * - 全局 Mock (fetch, localStorage, router)
 * - 测试数据工厂
 */

import '@testing-library/jest-dom/vitest';
import { vi, beforeAll, afterAll, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

// ============================================================
// MSW Mock Server (Mock Service Worker)
// ============================================================

const API_BASE = '/api/v1';

export const handlers = [
  // Auth
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const body = await request.json() as any;
    if (body.username === 'testuser' && body.password === 'password') {
      return HttpResponse.json({
        access_token: 'mock_token_xxx',
        refresh_token: 'mock_refresh_yyy',
        user: { id: 1, username: 'testuser', role: 'RESEARCHER' },
      });
    }
    return HttpResponse.json(
      { code: 401, message: '用户名或密码错误' },
      { status: 401 }
    );
  }),

  http.post(`${API_BASE}/auth/register`, async () => {
    return HttpResponse.json(
      { id: 1, username: 'newuser', email: 'new@test.com', role: 'RESEARCHER' },
      { status: 201 }
    );
  }),

  // Jobs
  http.get(`${API_BASE}/jobs`, () => {
    return HttpResponse.json({
      items: [
        { id: 1, job_name: 'Test Job', status: 'COMPLETED', progress: 100 },
        { id: 2, job_name: 'Running Job', status: 'DOCKING', progress: 65 },
      ],
      total: 2,
    });
  }),

  http.get(`${API_BASE}/jobs/:jobId`, ({ params }) => {
    const { jobId } = params;
    return HttpResponse.json({
      id: Number(jobId),
      job_name: 'Test Screening',
      status: 'DOCKING',
      progress: 72,
      total_drugs: 5000,
      finished_drugs: 3600,
    });
  }),

  http.post(`${API_BASE}/jobs`, async () => {
    return HttpResponse.json({ job_id: 1, status: 'CREATED' }, { status: 201 });
  }),

  http.get(`${API_BASE}/jobs/:jobId/results`, () => {
    return HttpResponse.json({
      items: [
        { rank: 1, drug_name: 'Drug A', affinity_score: -12.5 },
        { rank: 2, drug_name: 'Drug B', affinity_score: -11.8 },
      ],
      total: 2,
    });
  }),

  // Projects
  http.get(`${API_BASE}/projects`, () => {
    return HttpResponse.json([
      { id: 1, project_name: 'COVID-19 Screening', owner_id: 1 },
      { id: 2, project_name: 'Cancer Research', owner_id: 1 },
    ]);
  }),

  // Receptors
  http.get(`${API_BASE}/receptors`, () => {
    return HttpResponse.json([
      { id: 1, receptor_name: 'EGFR', pdb_code: '1M17' },
      { id: 2, receptor_name: 'SARS-CoV-2 Mpro', pdb_code: '6LU7' },
      { id: 3, receptor_name: 'VEGFR2', pdb_code: '3VHE' },
    ]);
  }),

  // Reports
  http.get(`${API_BASE}/jobs/:jobId/report`, () => {
    return HttpResponse.json([
      { id: 1, report_type: 'PDF', report_uri: '/reports/j1.pdf' },
    ]);
  }),
];

export const server = setupServer(...handlers);

// ============================================================
// Global Setup
// ============================================================

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.clearAllMocks();
  localStorage.clear();
});
afterAll(() => server.close());

// ============================================================
// Global Mocks
// ============================================================

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  observe() { return null; }
  unobserve() { return null; }
  disconnect() { return null; }
} as any;

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// ============================================================
// Test Helpers
// ============================================================

/**
 * 设置已登录用户的认证状态
 */
export function setLoggedInUser(role: 'RESEARCHER' | 'ADMIN' = 'RESEARCHER') {
  localStorage.setItem('access_token', 'mock_token_xxx');
  localStorage.setItem('user', JSON.stringify({
    id: 1,
    username: 'testuser',
    role,
  }));
}

/**
 * 清除认证状态(模拟未登录)
 */
export function clearAuthState() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
}

/**
 * 等待异步渲染完成
 */
export function waitForAsyncRender(timeout = 0) {
  return new Promise((resolve) => setTimeout(resolve, timeout));
}
