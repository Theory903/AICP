use mammoth_runtime::{
    nl_workflow::NlWorkflowParser,
    security::{SsrfCheckResult, SsrfGuard},
    tracing::PerformanceTracer,
    usage::{CostEstimator, TokenUsage},
    workflow_compiler::WorkflowCompiler,
    workflow_simulator::WorkflowSimulator,
};

#[test]
fn nl_parse_compile_simulate_pipeline() {
    let text = "Fetch customer records, then validate them, then send welcome email";
    let parser = NlWorkflowParser::new();
    let spec = parser.parse(text).expect("parse");

    let compile = WorkflowCompiler::new().compile(&spec);
    assert!(compile.valid, "compile errors: {:?}", compile.errors);

    let sim = WorkflowSimulator::new().dry_run(&spec);
    assert_eq!(sim.steps_would_execute.len(), 3);
    assert!(!sim.has_parallel_steps);
}

#[test]
fn nl_parse_detects_parallel() {
    let text = "Send email and update database in parallel";
    let parser = NlWorkflowParser::new();
    let spec = parser.parse(text).expect("parse");

    let sim = WorkflowSimulator::new().dry_run(&spec);
    assert!(sim.has_parallel_steps);
}

#[test]
fn cost_estimator_compares_models() {
    let estimator = CostEstimator::default();
    let usage = TokenUsage {
        input_tokens: 100_000,
        output_tokens: 50_000,
        cache_creation_input_tokens: 0,
        cache_read_input_tokens: 0,
    };
    let comparison = estimator.compare_models(usage, &["claude-haiku-4-5", "claude-opus-4-6"]);
    assert_eq!(comparison[0].model, "claude-haiku-4-5");
    assert!(comparison[0].cost_usd < comparison[1].cost_usd);
}

#[test]
fn ssrf_guard_allows_safe_url() {
    let guard = SsrfGuard;
    let result = guard.check_url("https://api.example.com/data");
    assert!(matches!(result, SsrfCheckResult::Allowed));
}

#[test]
fn ssrf_guard_blocks_internal() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://192.168.1.1/admin");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn performance_tracer_records_spans() {
    let tracer = PerformanceTracer::new();
    let _s1 = tracer.start_span("step1");
    let _s2 = tracer.start_span("step2");
    drop(_s1);
    drop(_s2);
    let report = tracer.report();
    assert_eq!(report.len(), 2);
}

#[test]
fn workflow_compiler_rejects_empty_id() {
    let spec = NlWorkflowParser::new()
        .parse("do something")
        .expect("parse");
    let compile = WorkflowCompiler::new().compile(&spec);
    assert!(compile.valid);
}

#[test]
fn workflow_compiler_rejects_subflow_without_id() {
    use mammoth_runtime::nl_workflow::{WorkflowSpec, WorkflowStep};

    let spec = WorkflowSpec {
        id: "wf_test".to_string(),
        name: "test".to_string(),
        description: None,
        steps: vec![WorkflowStep {
            id: "step_00".to_string(),
            step_type: "subflow".to_string(),
            capability_name: None,
            parallel_steps: None,
            branch_conditions: None,
            subflow_id: None,
            status: "pending".to_string(),
        }],
        status: "created".to_string(),
        created_at: "2026-04-05T00:00:00Z".to_string(),
        updated_at: "2026-04-05T00:00:00Z".to_string(),
        compensation_policy: "none".to_string(),
    };

    let result = WorkflowCompiler::new().compile(&spec);
    assert!(!result.valid);
    assert!(result.errors.iter().any(|e| e.field.contains("subflow_id")));
}
