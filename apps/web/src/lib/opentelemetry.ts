// Sprint 3: OpenTelemetry Web SDK for Real User Monitoring
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { UserInteractionInstrumentation } from '@opentelemetry/instrumentation-user-interaction';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { trace } from '@opentelemetry/api';
import { logDebug } from '@/lib/telemetry';

const JAEGER_ENDPOINT = import.meta.env.VITE_JAEGER_ENDPOINT || 'http://localhost:4318/v1/traces';
const SERVICE_NAME = 'fabric-4l-frontend';
const SERVICE_VERSION = import.meta.env.VITE_APP_VERSION || 'unknown';
const ENVIRONMENT = import.meta.env.VITE_ENVIRONMENT || 'development';

// Only enable in production and staging
const shouldEnable = ['production', 'staging'].includes(ENVIRONMENT);

if (shouldEnable) {
  const provider = new WebTracerProvider({
    resource: resourceFromAttributes({
      [SemanticResourceAttributes.SERVICE_NAME]: SERVICE_NAME,
      [SemanticResourceAttributes.SERVICE_VERSION]: SERVICE_VERSION,
      [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: ENVIRONMENT,
    }),
    spanProcessors: [
      new BatchSpanProcessor(
        new OTLPTraceExporter({
          url: JAEGER_ENDPOINT,
          headers: {},
        }),
        {
          maxQueueSize: 2048,
          maxExportBatchSize: 512,
          scheduledDelayMillis: 5000,
        },
      ),
    ],
  });

  provider.register();

  registerInstrumentations({
    instrumentations: [
      new DocumentLoadInstrumentation(),
      new UserInteractionInstrumentation({
        eventNames: ['click', 'submit', 'keydown'],
      }),
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [
          new RegExp('https://api\.fabric4l\.io/.*'),
        ],
        clearTimingResources: true,
      }),
      new XMLHttpRequestInstrumentation({
        propagateTraceHeaderCorsUrls: [
          new RegExp('https://api\.fabric4l\.io/.*'),
        ],
      }),
    ],
  });

  logDebug('[OTel Web] Real User Monitoring initialized');
} else {
  logDebug('[OTel Web] RUM disabled for environment', { environment: ENVIRONMENT });
}

export function getTracer() {
  return trace.getTracer(SERVICE_NAME, SERVICE_VERSION);
}

export default {};
