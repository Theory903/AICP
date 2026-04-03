"""Tests for the YAML Workflow DSL parser.

TDD: these tests are written BEFORE the implementation.
They define the contract for aicp_runtime.workflow.dsl.WorkflowDSLParser.
"""

from __future__ import annotations

import textwrap

import pytest

# DSL parser lives at aicp_runtime.workflow.dsl (not yet implemented)
from aicp_runtime.workflow.dsl import (
    DSLParseError,
    DSLValidationError,
    WorkflowDSLParser,
)
from aicp.interfaces.workflow_runtime import WorkflowState, WorkflowStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(yaml_text: str) -> WorkflowState:
    """Parse a dedented YAML string into a WorkflowState."""
    parser = WorkflowDSLParser()
    return parser.parse(textwrap.dedent(yaml_text))


# ---------------------------------------------------------------------------
# Happy-path: minimal workflow
# ---------------------------------------------------------------------------

class TestDSLMinimalWorkflow:
    def test_minimal_workflow_produces_workflow_state(self):
        """A YAML with name + one capability step produces a valid WorkflowState."""
        wf = parse("""
            name: Order Pizza
            steps:
              - id: place_order
                capability_name: orders.place
        """)
        assert isinstance(wf, WorkflowState)

    def test_name_is_set(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert wf.name == "My Workflow"

    def test_description_is_set_when_provided(self):
        wf = parse("""
            name: My Workflow
            description: A test workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert wf.description == "A test workflow"

    def test_description_defaults_to_empty(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert wf.description == ""

    def test_workflow_id_is_generated(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert isinstance(wf.id, str)
        assert len(wf.id) > 0

    def test_workflow_status_is_created(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert wf.status == WorkflowStatus.CREATED

    def test_initial_context_from_dsl(self):
        wf = parse("""
            name: My Workflow
            context:
              order_id: "ord_123"
              quantity: 2
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert wf.context["order_id"] == "ord_123"
        assert wf.context["quantity"] == 2

    def test_metadata_from_dsl(self):
        wf = parse("""
            name: My Workflow
            metadata:
              tenant: acme
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert wf.metadata.get("tenant") == "acme"


# ---------------------------------------------------------------------------
# Step parsing
# ---------------------------------------------------------------------------

class TestDSLStepParsing:
    def test_single_step_is_created(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: place_order
                capability_name: orders.place
        """)
        assert len(wf.steps) == 1
        assert wf.steps[0].capability_name == "orders.place"

    def test_step_id_is_preserved(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: place_order
                capability_name: orders.place
        """)
        assert wf.steps[0].id == "place_order"

    def test_multiple_steps_in_order(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step_a
                capability_name: orders.place
              - id: step_b
                capability_name: orders.confirm
              - id: step_c
                capability_name: orders.notify
        """)
        assert len(wf.steps) == 3
        ids = [s.id for s in wf.steps]
        assert ids == ["step_a", "step_b", "step_c"]

    def test_step_arguments_are_set(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: place_order
                capability_name: orders.place
                arguments:
                  restaurant_id: "r_123"
                  items: ["pizza"]
        """)
        assert wf.steps[0].arguments["restaurant_id"] == "r_123"
        assert wf.steps[0].arguments["items"] == ["pizza"]

    def test_step_without_arguments_defaults_to_empty(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        assert wf.steps[0].arguments == {}

    def test_step_type_defaults_to_capability(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        # capability_name present → step should have a capability_name
        assert wf.steps[0].capability_name == "foo.bar"

    def test_step_metadata_is_stored(self):
        """DSL-level step metadata (retry_policy, on_success, etc.) stored in step.metadata."""
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
                on_success: step2
              - id: step2
                capability_name: foo.baz
        """)
        # on_success stored in step metadata for the runtime to inspect
        assert wf.steps[0].metadata.get("on_success") == "step2"

    def test_on_failure_stored_in_metadata(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
                on_failure: error_handler
              - id: error_handler
                capability_name: foo.error
        """)
        assert wf.steps[0].metadata.get("on_failure") == "error_handler"

    def test_retry_policy_stored_in_metadata(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
                retry_policy:
                  max_attempts: 3
                  backoff: exponential
                  delay_ms: 100
        """)
        rp = wf.steps[0].metadata.get("retry_policy")
        assert rp is not None
        assert rp["max_attempts"] == 3
        assert rp["backoff"] == "exponential"
        assert rp["delay_ms"] == 100

    def test_timeout_ms_stored_in_metadata(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
                timeout_ms: 5000
        """)
        assert wf.steps[0].metadata.get("timeout_ms") == 5000

    def test_approval_policy_stored_in_metadata(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: risky.action
                approval_policy:
                  required: true
                  role: admin
        """)
        ap = wf.steps[0].metadata.get("approval_policy")
        assert ap is not None
        assert ap["required"] is True
        assert ap["role"] == "admin"

    def test_input_output_mapping_stored(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
                input_mapping:
                  order_id: context.order_id
                output_mapping:
                  result: steps.step1.result
        """)
        assert wf.steps[0].metadata.get("input_mapping") == {"order_id": "context.order_id"}
        assert wf.steps[0].metadata.get("output_mapping") == {"result": "steps.step1.result"}

    def test_compensation_stored_in_metadata(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: place_order
                capability_name: orders.place
                compensation:
                  capability_name: orders.cancel
                  arguments:
                    reason: rollback
        """)
        comp = wf.steps[0].metadata.get("compensation")
        assert comp is not None
        assert comp["capability_name"] == "orders.cancel"
        assert comp["arguments"]["reason"] == "rollback"


# ---------------------------------------------------------------------------
# Step type: parallel
# ---------------------------------------------------------------------------

class TestDSLParallelSteps:
    def test_parallel_step_stored_in_metadata(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: fan_out
                type: parallel
                parallel_steps:
                  - id: notify_email
                    capability_name: notify.email
                  - id: notify_sms
                    capability_name: notify.sms
              - id: continue
                capability_name: orders.confirm
        """)
        fan_out = wf.steps[0]
        assert fan_out.metadata.get("type") == "parallel"
        parallel = fan_out.metadata.get("parallel_steps")
        assert parallel is not None
        assert len(parallel) == 2
        assert parallel[0]["id"] == "notify_email"
        assert parallel[1]["id"] == "notify_sms"

    def test_parallel_failure_policy_defaults_to_fail_fast(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: fan_out
                type: parallel
                parallel_steps:
                  - id: a
                    capability_name: foo.a
                  - id: b
                    capability_name: foo.b
        """)
        policy = wf.steps[0].metadata.get("parallel_failure_policy", "fail_fast")
        assert policy == "fail_fast"

    def test_parallel_failure_policy_wait_all(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: fan_out
                type: parallel
                parallel_failure_policy: wait_all
                parallel_steps:
                  - id: a
                    capability_name: foo.a
                  - id: b
                    capability_name: foo.b
        """)
        assert wf.steps[0].metadata.get("parallel_failure_policy") == "wait_all"


# ---------------------------------------------------------------------------
# Step type: wait_event
# ---------------------------------------------------------------------------

class TestDSLWaitEventStep:
    def test_wait_event_step_stored(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: wait_payment
                type: wait_event
                wait_for_event: payment.confirmed
              - id: continue
                capability_name: orders.confirm
        """)
        step = wf.steps[0]
        assert step.metadata.get("type") == "wait_event"
        assert step.metadata.get("wait_for_event") == "payment.confirmed"

    def test_wait_event_with_filter(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: wait_payment
                type: wait_event
                wait_for_event: payment.confirmed
                event_filter:
                  order_id: "${context.order_id}"
        """)
        assert wf.steps[0].metadata.get("event_filter") == {"order_id": "${context.order_id}"}

    def test_wait_event_with_timeout(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: wait_payment
                type: wait_event
                wait_for_event: payment.confirmed
                timeout_ms: 300000
                on_timeout: payment_timeout_handler
              - id: payment_timeout_handler
                capability_name: orders.cancel
        """)
        assert wf.steps[0].metadata.get("timeout_ms") == 300000
        assert wf.steps[0].metadata.get("on_timeout") == "payment_timeout_handler"


# ---------------------------------------------------------------------------
# Step type: branch
# ---------------------------------------------------------------------------

class TestDSLBranchStep:
    def test_branch_conditions_stored(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: decide
                type: branch
                branch_conditions:
                  - condition: "context.total > 100"
                    then_step_id: high_value_path
                  - condition: "context.total <= 100"
                    then_step_id: normal_path
                default_branch: normal_path
              - id: high_value_path
                capability_name: orders.vip
              - id: normal_path
                capability_name: orders.standard
        """)
        step = wf.steps[0]
        assert step.metadata.get("type") == "branch"
        conditions = step.metadata.get("branch_conditions")
        assert conditions is not None
        assert len(conditions) == 2
        assert conditions[0]["condition"] == "context.total > 100"
        assert conditions[0]["then_step_id"] == "high_value_path"
        assert step.metadata.get("default_branch") == "normal_path"


# ---------------------------------------------------------------------------
# Step type: loop
# ---------------------------------------------------------------------------

class TestDSLLoopStep:
    def test_loop_step_stored(self):
        wf = parse("""
            name: My Workflow
            steps:
              - id: process_items
                type: loop
                loop_condition:
                  items_variable: context.items
                  max_iterations: 10
                loop_body:
                  - id: process_item
                    capability_name: items.process
        """)
        step = wf.steps[0]
        assert step.metadata.get("type") == "loop"
        lc = step.metadata.get("loop_condition")
        assert lc is not None
        assert lc["items_variable"] == "context.items"
        assert lc["max_iterations"] == 10
        body = step.metadata.get("loop_body")
        assert body is not None
        assert len(body) == 1
        assert body[0]["id"] == "process_item"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestDSLValidation:
    def test_missing_name_raises_validation_error(self):
        with pytest.raises(DSLValidationError, match="name"):
            parse("""
                steps:
                  - id: step1
                    capability_name: foo.bar
            """)

    def test_missing_steps_raises_validation_error(self):
        with pytest.raises(DSLValidationError, match="steps"):
            parse("""
                name: My Workflow
            """)

    def test_empty_steps_raises_validation_error(self):
        with pytest.raises(DSLValidationError):
            parse("""
                name: My Workflow
                steps: []
            """)

    def test_step_missing_id_raises_validation_error(self):
        with pytest.raises(DSLValidationError, match="id"):
            parse("""
                name: My Workflow
                steps:
                  - capability_name: foo.bar
            """)

    def test_duplicate_step_ids_raises_validation_error(self):
        with pytest.raises(DSLValidationError, match="duplicate"):
            parse("""
                name: My Workflow
                steps:
                  - id: step1
                    capability_name: foo.bar
                  - id: step1
                    capability_name: foo.baz
            """)

    def test_invalid_yaml_raises_parse_error(self):
        with pytest.raises(DSLParseError):
            WorkflowDSLParser().parse("name: [unclosed")

    def test_non_dict_yaml_raises_parse_error(self):
        with pytest.raises(DSLParseError):
            WorkflowDSLParser().parse("- just a list")

    def test_unknown_top_level_field_raises_validation_error(self):
        with pytest.raises(DSLValidationError, match="unknown_field"):
            parse("""
                name: My Workflow
                unknown_field: oops
                steps:
                  - id: step1
                    capability_name: foo.bar
            """)

    def test_invalid_retry_policy_backoff_value(self):
        with pytest.raises(DSLValidationError):
            parse("""
                name: My Workflow
                steps:
                  - id: step1
                    capability_name: foo.bar
                    retry_policy:
                      backoff: invalid_value
            """)

    def test_parallel_step_missing_parallel_steps(self):
        with pytest.raises(DSLValidationError):
            parse("""
                name: My Workflow
                steps:
                  - id: fan_out
                    type: parallel
            """)

    def test_wait_event_step_missing_event_name(self):
        with pytest.raises(DSLValidationError):
            parse("""
                name: My Workflow
                steps:
                  - id: wait_step
                    type: wait_event
            """)


# ---------------------------------------------------------------------------
# from_file / from_string factories
# ---------------------------------------------------------------------------

class TestDSLFactories:
    def test_parse_from_string(self):
        yaml_text = textwrap.dedent("""
            name: My Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """)
        parser = WorkflowDSLParser()
        wf = parser.parse(yaml_text)
        assert wf.name == "My Workflow"

    def test_parse_from_file(self, tmp_path):
        dsl_file = tmp_path / "workflow.yaml"
        dsl_file.write_text(textwrap.dedent("""
            name: File Workflow
            steps:
              - id: step1
                capability_name: foo.bar
        """))
        parser = WorkflowDSLParser()
        wf = parser.parse_file(str(dsl_file))
        assert wf.name == "File Workflow"

    def test_to_yaml_roundtrip(self):
        """parse → to_yaml → parse produces equivalent workflow."""
        yaml_text = textwrap.dedent("""
            name: Roundtrip Workflow
            description: Test roundtrip
            steps:
              - id: step1
                capability_name: foo.bar
                arguments:
                  x: 1
              - id: step2
                capability_name: foo.baz
        """)
        parser = WorkflowDSLParser()
        wf1 = parser.parse(yaml_text)
        re_yaml = parser.to_yaml(wf1)
        wf2 = parser.parse(re_yaml)
        assert wf1.name == wf2.name
        assert len(wf1.steps) == len(wf2.steps)
        assert wf1.steps[0].id == wf2.steps[0].id
        assert wf1.steps[0].capability_name == wf2.steps[0].capability_name
