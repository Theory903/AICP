# AICP Vision

## Title

**AICP: The Capability Layer for Safe, Multi-Step AI Execution**

## Vision Statement

AICP exists to give AI systems operational awareness.

Today, most AI systems can speak beautifully and reason impressively, yet fail the moment the world asks them to act with precision. They can summarize, suggest, and explain, but when asked to complete a real task such as ordering food, filling a complex form, booking a ticket, or making a payment, they often collapse into one of three failures: they do not know what tools truly mean, they do not know what step they are in, or they do not know what they are allowed to do.

AICP is designed to solve that gap.

It is a standard for making AI systems aware of their capabilities, aware of their process state, and aware of execution constraints, so they can safely understand, plan, and complete real-world multi-step tasks.

Where previous systems treated actions as isolated tools, AICP treats them as meaningful capabilities inside governed workflows. Where older integrations exposed endpoints, AICP exposes intent-aligned actions. Where most tool systems stop at invocation, AICP continues into policy, workflow state, error normalization, rendering, and safe continuation.

The long-term vision is to make AICP the standard execution contract for the agentic web: a world where AI systems do not merely call tools, but operate with clarity, control, accountability, and step-by-step awareness across platforms.

## The World AICP Wants to Create

In the world AICP is built for, an AI system can do more than trigger APIs.

It can understand:

- what actions exist,
- what those actions mean,
- what information is missing,
- what the next valid step is,
- what requires approval,
- what failed and why,
- and how to present outcomes clearly to users.

That means the same standard can support:

- personal assistants ordering meals,
- finance agents preparing and confirming payments,
- travel agents booking tickets,
- enterprise agents completing approvals,
- support systems handling workflows,
- and form-filling systems managing validation-heavy submissions.

AICP is not just about making actions callable. It is about making them understandable.

## Why Now

The world is moving from chat-based AI to action-based AI.

Large language models have already become capable enough to parse intent, reason over ambiguity, and generate structured outputs. At the same time, businesses and developers increasingly want these systems to do real work rather than simply generate text. Yet the infrastructure for safe action remains immature. Existing approaches tend to be fragmented across tool calling, raw API exposure, wrappers, prompt conventions, and proprietary orchestration logic.

This creates a structural gap:

- APIs were designed for developers, not for AI systems.
- Tool registries expose functions, but not workflow awareness.
- Most systems do not standardize policy, pagination, rendering, or multi-step state.
- Real-world execution is still brittle, unsafe, and inconsistent.

AICP arrives at the moment when AI systems are capable enough to act, but the world still lacks a standard that teaches them how.

## Core Belief

A capability is not merely a function.
A capability is an action with meaning, constraints, state, and consequences.

AICP is built on the belief that if AI is to operate safely in the real world, it must understand actions at that richer level.

## Strategic Positioning

AICP is not a replacement for REST, GraphQL, OpenAPI, or MCP.

Instead, it sits above them as a semantic and execution-aware layer.

- REST and OpenAPI describe APIs.
- GraphQL structures data querying.
- MCP helps expose and call tools.
- AICP defines how AI understands, evaluates, sequences, and safely executes those actions.

That is its place in the stack.

## North Star

AICP becomes the standard way AI systems know:

- what they can do,
- what they are doing,
- what is allowed,
- what is missing,
- what comes next,
- and how to complete the task safely.

## Agentic Experience Principle

**AICP is designed for AI agents, not just prompt engineers.**

Every AICP response is designed so that even a mini-LLM (1B parameters) can process it without complex reasoning:

- **Explicit next steps** — never wonder "what now?"
- **Built-in fix hints** — errors tell the AI how to recover
- **State is always current** — workflow progress is in every response
- **Policy is explicit** — autonomous execution allowed/denied is clear
- **One canonical way** — no ambiguity, no inference needed

See `docs/AGENTIC_EXPERIENCE.md` for the full design specification.

## Non-Negotiable Principles

1. **AI-ease over human-ease**
   Every response tells the AI exactly what to do next. Minimal reasoning required.

2. **Capability over endpoint**
   AICP standardizes meaningful business actions, not raw transport details.

3. **Workflow awareness over isolated calls**
   Real-world tasks are multi-step; the protocol must understand step, state, and transition.

4. **Policy first, not patched later**
   Permissions, risk, confirmation, and execution boundaries are first-class concerns.

5. **Structured failure over chaos**
   AI systems need normalized, reason-friendly failure models with fix hints.

6. **Render-aware outcomes**
   The output should be understandable to both agents and human-facing clients.

7. **Adapter-friendly adoption**
   Existing systems should be able to adopt AICP without large rewrites.

## Long-Term Expansion

Over time, AICP can become the execution plane beneath:

- agent marketplaces,
- personal AI operating systems,
- enterprise agent platforms,
- agent identity systems,
- consent and approval hubs,
- and unified multi-client AI experiences.

It begins with capabilities and workflows. It can grow into the standard operating grammar for AI action.
