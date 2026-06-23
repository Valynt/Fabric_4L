import { describe, expect, it } from 'vitest';
import { ApiError } from '@/api/client';
import { BaseApiError, withApiError } from './useApiShared';

describe('withApiError', () => {
  it('preserves ApiError trace and code metadata', async () => {
    const promise = Promise.reject(new ApiError('forbidden', 403, 'TENANT_MISMATCH', 'trace-123'));

    await expect(withApiError(promise, BaseApiError)).rejects.toMatchObject({
      message: 'forbidden',
      statusCode: 403,
      errorCode: 'TENANT_MISMATCH',
      traceId: 'trace-123',
    });
  });

  it('extracts code and trace metadata from axios-style error payloads', async () => {
    const error = Object.assign(new Error('request failed'), {
      response: {
        status: 409,
        data: {
          error: {
            code: 'CONFLICT',
            message: 'Conflict',
            request_id: 'trace-409',
          },
        },
      },
    });

    await expect(withApiError(Promise.reject(error), BaseApiError)).rejects.toMatchObject({
      message: 'request failed',
      statusCode: 409,
      errorCode: 'CONFLICT',
      traceId: 'trace-409',
    });
  });
});
