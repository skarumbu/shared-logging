import pino from 'pino';

interface WriteTarget {
  write(msg: string): void;
}

interface RequestEntry {
  endpoint: string;
  method: string;
  status: number;
  duration_ms: number;
}

interface ErrorEntry extends RequestEntry {
  message: string;
  error_type: string;
  stack_trace?: string;
}

export function getLogger(service: string, dest?: WriteTarget) {
  const destination = dest ?? process.stdout;
  const base = pino(
    { timestamp: false, base: null, level: 'info' },
    destination as Parameters<typeof pino>[1]
  );

  return {
    request(entry: RequestEntry): void {
      base.info({
        event: 'request' as const,
        service,
        ...entry,
        timestamp: new Date().toISOString(),
      });
    },
    error(entry: ErrorEntry): void {
      base.error({
        event: 'error' as const,
        service,
        ...entry,
        timestamp: new Date().toISOString(),
      });
    },
  };
}
