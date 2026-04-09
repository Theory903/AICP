/**
 * AICP Integration Database - Database types and utilities for AICP integrations
 *
 * This module exports all database-related types including:
 * - Table row types (CorsairAccount, CorsairEntity, etc.)
 * - Insert and update types
 * - Database connection types
 * - Kysely database types
 *
 * @example
 * ```ts
 * import type { CorsairAccountInsert, CorsairTableName } from '@aicp/integration-core/db';
 * ```
 */

export { sql } from 'kysely';
export * from './db/index';
export type {
	CorsairDatabase,
	CorsairDatabaseInput,
	CorsairKyselyDatabase,
} from './db/kysely/database';
export { createCorsairDatabase } from './db/kysely/database';
