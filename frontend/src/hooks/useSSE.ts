import { useEffect, useRef, useCallback, useMemo } from 'react';
import { useTaskStore } from '../stores/taskStore';

const MAX_RECONNECT_COUNT = 5;
const RECONNECT_DELAY_MS = 2000;

interface SSEMessage {
  type: string;
  data: Record<string, unknown>;
}

export function useSSE(jobId: string | null) {
  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const updateJobFromSSE = useTaskStore((s) => s.updateJobFromSSE);
  const onMessageRef = useRef<(msg: SSEMessage) => void>(() => {});

  const subscribe = useCallback(
    (handler: (msg: SSEMessage) => void) => {
      onMessageRef.current = handler;
    },
    []
  );

  const close = useCallback(() => {
    abortControllerRef.current?.abort();
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    reconnectCountRef.current = MAX_RECONNECT_COUNT; // prevent reconnect
  }, []);

  // Build base URL once
  const baseUrl = useMemo(
    () => import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
    []
  );

  useEffect(() => {
    if (!jobId) return;

    let active = true;
    reconnectCountRef.current = 0;

    const connect = () => {
      if (!active) return;
      if (reconnectCountRef.current >= MAX_RECONNECT_COUNT) return;

      // Always use fetch to initiate connection, setting Authorization header for what follows
      // EventSource cannot set headers, so we use fetch as a carrier for the JWT token
      // The server must accept the token via header on the SSE endpoint
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const token = localStorage.getItem('access_token');

      fetch(`${baseUrl}/screenings/${jobId}/events`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
          Accept: 'text/event-stream',
        },
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok || !response.body) {
            throw new Error(`SSE connection failed: ${response.status}`);
          }

          // Reset reconnect count on successful connection
          reconnectCountRef.current = 0;

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const processLines = () => {
            const parts = buffer.split('\n');
            // Keep the last (potentially incomplete) part in the buffer
            buffer = parts.pop() || '';

            let eventType = '';
            let dataStr = '';

            for (const line of parts) {
              if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                dataStr = line.slice(6);
              } else if (line === '' && eventType && dataStr) {
                // Empty line = end of event
                try {
                  const data = JSON.parse(dataStr);
                  if (eventType === 'progress' && data.job) {
                    updateJobFromSSE(data.job);
                  } else if (eventType === 'node_update') {
                    updateJobFromSSE(data);
                  } else if (eventType === 'complete') {
                    if (data.job) updateJobFromSSE(data.job);
                    // Don't reconnect on complete
                    reconnectCountRef.current = MAX_RECONNECT_COUNT;
                  }
                  onMessageRef.current({ type: eventType, data });
                } catch {
                  // Ignore parse errors
                }
                eventType = '';
                dataStr = '';
              }
            }
          };

          const pump = async () => {
            try {
              while (active) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                processLines();
              }
            } catch {
              // Reader was cancelled or errored
            }
          };

          await pump();
        })
        .catch(() => {
          // Connection error — will retry below
        })
        .finally(() => {
          if (!active) return;
          if (reconnectCountRef.current < MAX_RECONNECT_COUNT) {
            reconnectCountRef.current++;
            reconnectTimerRef.current = setTimeout(() => {
              connect();
            }, RECONNECT_DELAY_MS * reconnectCountRef.current); // exponential backoff
          }
        });
    };

    connect();

    return () => {
      active = false;
      close();
    };
  }, [jobId, baseUrl, updateJobFromSSE, close]);

  return { subscribe, close };
}
