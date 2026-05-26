import { describe, it, expect } from 'vitest';
import { getLogger } from '../src/logger.js';

describe('getLogger', () => {
  it('emits a request log with all required fields', () => {
    const lines: string[] = [];
    const logger = getLogger('test-svc', { write: (msg: string) => lines.push(msg) });

    logger.request({ endpoint: '/items', method: 'GET', status: 200, duration_ms: 45 });

    expect(lines).toHaveLength(1);
    const entry = JSON.parse(lines[0]);
    expect(entry.event).toBe('request');
    expect(entry.service).toBe('test-svc');
    expect(entry.endpoint).toBe('/items');
    expect(entry.method).toBe('GET');
    expect(entry.status).toBe(200);
    expect(entry.duration_ms).toBe(45);
    expect(entry.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it('emits an error log with error_type and optional stack_trace', () => {
    const lines: string[] = [];
    const logger = getLogger('test-svc', { write: (msg: string) => lines.push(msg) });

    logger.error({
      endpoint: '/items',
      method: 'POST',
      status: 500,
      message: 'boom',
      error_type: 'TypeError',
      stack_trace: 'at line 1',
      duration_ms: 12,
    });

    const entry = JSON.parse(lines[0]);
    expect(entry.event).toBe('error');
    expect(entry.service).toBe('test-svc');
    expect(entry.error_type).toBe('TypeError');
    expect(entry.stack_trace).toBe('at line 1');
    expect(entry.message).toBe('boom');
  });

  it('uses process.stdout when no dest provided', () => {
    // Just verifies it does not throw
    const logger = getLogger('stdout-test');
    expect(() => logger.request({ endpoint: '/ping', method: 'GET', status: 200, duration_ms: 1 })).not.toThrow();
  });
});
