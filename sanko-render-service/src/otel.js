// OpenTelemetry tracing for the render service.
//
// Enable via:
// - OTEL_ENABLED=true
// - OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
// - OTEL_SERVICE_NAME=sanko-render-service
// Optional logs via:
// - OTEL_LOGS_ENABLED=true
// - OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://localhost:4318
//
// This file must be required before other app imports for best coverage.

function envTruthy(name, defaultValue = "false") {
  const v = process.env[name] ?? defaultValue;
  return String(v).trim().toLowerCase() === "true" || String(v).trim() === "1";
}

const enabled = envTruthy("OTEL_ENABLED", "false");
const endpoint = (process.env.OTEL_EXPORTER_OTLP_ENDPOINT || "").trim();

if (!enabled || !endpoint) {
  module.exports = { enabled: false };
  return;
}

const { diag, DiagConsoleLogger, DiagLogLevel } = require("@opentelemetry/api");
const { logs } = require("@opentelemetry/api-logs");
const { NodeSDK } = require("@opentelemetry/sdk-node");
const { OTLPTraceExporter } = require("@opentelemetry/exporter-trace-otlp-grpc");
const { getNodeAutoInstrumentations } = require("@opentelemetry/auto-instrumentations-node");
const { Resource } = require("@opentelemetry/resources");
const { SemanticResourceAttributes } = require("@opentelemetry/semantic-conventions");
const { LoggerProvider, BatchLogRecordProcessor } = require("@opentelemetry/sdk-logs");
const { OTLPLogExporter } = require("@opentelemetry/exporter-logs-otlp-http");

const diagLevel = (process.env.OTEL_DIAG_LOG_LEVEL || "").toLowerCase();
if (diagLevel === "debug") {
  diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
} else if (diagLevel === "info") {
  diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.INFO);
}

const serviceName = process.env.OTEL_SERVICE_NAME || "sanko-render-service";
const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: serviceName,
});

let exporterUrl = endpoint;
if (exporterUrl && !/^https?:\/\//i.test(exporterUrl)) {
  exporterUrl = `http://${exporterUrl}`;
}

const sdk = new NodeSDK({
  resource: Resource.default().merge(resource),
  traceExporter: new OTLPTraceExporter({
    url: exporterUrl,
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start().catch((err) => {
  // Avoid crashing startup; tracing is best-effort.
  // eslint-disable-next-line no-console
  console.error("[otel] failed to start", err);
});

// Best-effort OTLP logs to the collector.
// Note: we don't monkeypatch console.*. Instead, `src/utils/logger.js` will emit OTel logs
// when a global LoggerProvider is configured.
const logsEnabled = envTruthy("OTEL_LOGS_ENABLED", "true");
if (logsEnabled) {
  try {
    let logsEndpoint = (process.env.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT || "").trim();
    if (!logsEndpoint) {
      // Common dev setup: traces use gRPC :4317, logs use HTTP :4318.
      logsEndpoint = exporterUrl.replace(/:4317\b/, ":4318");
    }
    if (logsEndpoint && !/^https?:\/\//i.test(logsEndpoint)) {
      logsEndpoint = `http://${logsEndpoint}`;
    }
    const logsUrl = `${logsEndpoint.replace(/\/$/, "")}/v1/logs`;

    const loggerProvider = new LoggerProvider({
      resource: Resource.default().merge(resource),
    });
    loggerProvider.addLogRecordProcessor(
      new BatchLogRecordProcessor(new OTLPLogExporter({ url: logsUrl }))
    );
    logs.setGlobalLoggerProvider(loggerProvider);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[otel] failed to setup logs", err);
  }
}

async function shutdown() {
  try {
    await sdk.shutdown();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[otel] failed to shutdown", err);
  }
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

module.exports = { enabled: true };
