/**
 * Structural guard: the dashboard's product code must never contain a
 * literal merchant id, a hardcoded-looking risk probability/exposure
 * value, or any other stand-in for a real API response. Mirrors the same
 * kind of source-literal scan used in ml/explainability's leakage tests.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const SRC_DIR = join(import.meta.dirname, '..')
const SCAN_DIRS = ['components', 'pages', 'context', 'hooks']
const EXCLUDED_SUFFIXES = ['.test.ts', '.test.tsx']

// A real benchmark merchant id looks like M0000-M0049; the only place this
// pattern is allowed to appear is in test fixtures/tests themselves.
const MERCHANT_ID_PATTERN = /['"`]M\d{4}['"`]/

function collectFiles(dir: string): string[] {
  const entries = readdirSync(dir)
  let files: string[] = []
  for (const entry of entries) {
    const fullPath = join(dir, entry)
    if (statSync(fullPath).isDirectory()) {
      files = files.concat(collectFiles(fullPath))
    } else if (/\.(ts|tsx)$/.test(entry) && !EXCLUDED_SUFFIXES.some((suffix) => entry.endsWith(suffix))) {
      files.push(fullPath)
    }
  }
  return files
}

describe('no hardcoded demo/merchant/risk data in product source', () => {
  const files = SCAN_DIRS.flatMap((dir) => collectFiles(join(SRC_DIR, dir)))

  it('scans at least the expected component/page/hook files', () => {
    expect(files.length).toBeGreaterThan(5)
  })

  it.each(files)('%s contains no literal merchant id', (file) => {
    const content = readFileSync(file, 'utf-8')
    expect(MERCHANT_ID_PATTERN.test(content)).toBe(false)
  })

  it.each(files)('%s does not import test fixtures', (file) => {
    const content = readFileSync(file, 'utf-8')
    expect(content.includes('@/test/fixtures')).toBe(false)
  })
})
