#[cfg(feature = "telemetry")]
pub mod telemetry_impl {
    use crate::tracing::SpanRecord;
    use prometheus::{Counter, CounterVec, Encoder, Opts, Registry, TextEncoder};
    use std::sync::Arc;

    pub struct TelemetryExporter {
        otel_endpoint: Option<String>,
        registry: Registry,
        capability_counter: CounterVec,
    }

    impl TelemetryExporter {
        pub fn new(otel_endpoint: Option<impl Into<String>>) -> Self {
            let registry = Registry::new();
            let opts = Opts::new("capability_executions_total", "Total capability executions")
                .const_label("version", env!("CARGO_PKG_VERSION"));
            let capability_counter =
                CounterVec::new(opts, &["capability", "success"]).expect("counter registration");
            registry
                .register(Box::new(capability_counter.clone()))
                .expect("register counter");
            Self {
                otel_endpoint: otel_endpoint.map(Into::into),
                registry,
                capability_counter,
            }
        }

        pub fn export_spans(&self, spans: &[SpanRecord]) {
            if self.otel_endpoint.is_none() {
                return;
            }
            for span in spans {
                eprintln!(
                    "[otel] span={} start_ms={} duration_ms={}",
                    span.name, span.start_ms, span.duration_ms
                );
            }
        }

        pub fn record_capability_execution(&self, capability_name: &str, success: bool) {
            self.capability_counter
                .with_label_values(&[capability_name, if success { "true" } else { "false" }])
                .inc();
        }

        pub fn prometheus_text(&self) -> String {
            let encoder = TextEncoder::new();
            let metric_families = self.registry.gather();
            let mut output = Vec::new();
            encoder
                .encode(&metric_families, &mut output)
                .expect("encode");
            String::from_utf8(output).expect("utf8")
        }
    }
}

#[cfg(feature = "telemetry")]
pub use telemetry_impl::TelemetryExporter;
