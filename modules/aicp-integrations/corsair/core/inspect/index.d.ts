import type { CorsairPlugin } from '../plugins';
/** @deprecated get_schema now returns a plain string. This type is kept for backwards compatibility. */
export type EndpointSchemaResult = {
    description?: string;
    riskLevel?: 'read' | 'write' | 'destructive';
    irreversible?: boolean;
    input?: unknown;
    output?: unknown;
    availableMethods?: Record<string, string[]>;
};
export type ListOperationsOptions = {
    /**
     * Filter to a specific plugin by its ID (e.g. 'slack', 'github').
     * - If the plugin is known but not added to the Corsair instance, a plain string message is returned.
     * - If the string is completely unrecognised, returns all API endpoints as a fallback.
     */
    plugin?: string;
    /**
     * Whether to list API endpoints, webhooks, or database entities.
     * - 'api' (default) — lists callable API endpoint paths
     * - 'webhooks' — lists receivable webhook event paths
     * - 'db' — lists searchable database entity paths (one .search per entity type)
     */
    type?: 'api' | 'webhooks' | 'db';
};
export type CorsairInspectMethods = {
    /**
     * Lists available operations (API endpoints, webhooks, or database entities) for the configured plugins.
     *
     * - No options → all API endpoint paths across every plugin, keyed by plugin ID
     * - `{ type: 'webhooks' }` → all webhook paths across every plugin, keyed by plugin ID
     * - `{ type: 'db' }` → all searchable DB entity paths across every plugin, keyed by plugin ID
     * - `{ plugin: 'slack' }` → Slack API endpoint paths as a flat array
     * - `{ plugin: 'slack', type: 'webhooks' }` → Slack webhook paths as a flat array
     * - `{ plugin: 'slack', type: 'db' }` → Slack DB entity search paths as a flat array
     * - If the plugin is known but not configured, returns a plain string message.
     * - If the plugin string is completely unrecognised, returns all API endpoints (same as no options).
     *
     * API paths use the format `plugin.api.group.method` (e.g. `slack.api.messages.post`).
     * Webhook paths use the format `plugin.webhooks.group.event` (e.g. `slack.webhooks.messages.message`).
     * DB paths use the format `plugin.db.entityType.search` (e.g. `slack.db.messages.search`).
     * All paths can be passed directly to `get_schema()`.
     *
     * @example
     * corsair.list_operations()
     * // { slack: ['slack.api.channels.list', 'slack.api.messages.post', ...], ... }
     *
     * corsair.list_operations({ plugin: 'slack' })
     * // ['slack.api.channels.list', 'slack.api.messages.post', ...]
     *
     * corsair.list_operations({ plugin: 'slack', type: 'webhooks' })
     * // ['slack.webhooks.messages.message', 'slack.webhooks.channels.created', ...]
     *
     * corsair.list_operations({ plugin: 'slack', type: 'db' })
     * // ['slack.db.messages.search', 'slack.db.channels.search', 'slack.db.users.search', ...]
     *
     * corsair.list_operations({ plugin: 'unknown' })
     * // "unknown isn't configured in the Corsair instance."
     */
    list_operations(options?: ListOperationsOptions): Record<string, string[]> | string[] | string;
    /**
     * Returns a plain-text TypeScript-style type declaration for a specific operation path.
     * The path format determines which kind of schema is returned:
     * - API path (`plugin.api.group.method`) → description, risk level, input/output types
     * - Webhook path (`plugin.webhooks.group.event`) → description, payload/response types, usage snippet
     * - DB path (`plugin.db.entityType.search`) → description, filterable fields with operators
     *
     * Casing is ignored — the path is lowercased before lookup.
     * If the path is not found, returns a list of available paths for self-correction.
     *
     * @example
     * corsair.get_schema('slack.api.messages.post')
     * // "Post a message to a channel  [write]\n\ninput {\n  channel: string\n  text?: string\n  ..."
     *
     * corsair.get_schema('slack.api.invalid')
     * // "Path not found. Available operations:\n  slack: slack.api.channels.list, ..."
     */
    get_schema(path: string): string;
};
/**
 * Creates the list_operations / get_schema functions bound to a specific plugin list.
 * Used by both single-tenant and multi-tenant client builders.
 */
export declare function buildInspectMethods(plugins: readonly CorsairPlugin[]): CorsairInspectMethods;
//# sourceMappingURL=index.d.ts.map