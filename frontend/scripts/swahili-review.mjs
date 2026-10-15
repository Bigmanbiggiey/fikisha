#!/usr/bin/env node
/**
 * Swahili review list (founder decision 20, 2026-10-14): every Swahili string
 * with its English source and the screen(s) that show it, as one CSV a
 * reviewer can open in a spreadsheet.
 *
 *   node scripts/swahili-review.mjs [--ref <git-ref> ...] [--out <file.csv>]
 *
 * Strings come from this working tree's `src/i18n/locales`, plus each `--ref`
 * (e.g. an open PR's branch), so strings not merged yet are included too;
 * a key found only on a ref says so in the `source` column. Screens are
 * found by searching the source for the key; a key built at run time
 * (`t(\`jobs:status.${s}\`)`) matches by its prefix and is marked "(dynamic)".
 *
 * Flags: `same as English` (likely untranslated), `missing Swahili`,
 * `placeholders differ` (a `{{var}}` in one language but not the other).
 * Run before launch; reviewers fill the last three columns.
 */
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const FRONTEND = join(fileURLToPath(new URL('.', import.meta.url)), '..');
const LOCALES = join(FRONTEND, 'src', 'i18n', 'locales');
const REPO_LOCALES = 'frontend/src/i18n/locales';

const args = process.argv.slice(2);
const refs = [];
let out = join(FRONTEND, '..', 'docs', 'swahili-review', 'swahili-review.csv');
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--ref') refs.push(args[++i]);
  else if (args[i] === '--out') out = args[++i];
}

// paths below are repo-root relative, so git runs from the repo root
const git = (...a) =>
  execFileSync('git', a, {
    cwd: join(FRONTEND, '..'),
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  });

function flatten(obj, prefix = '') {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === 'object' ? flatten(v, `${prefix}${k}.`) : [[`${prefix}${k}`, String(v)]],
  );
}

// ─── Strings: { "ns:key": { en, sw, source } } ───────────────────────────
const strings = new Map();
function addLocale(lang, ns, json, source) {
  for (const [key, value] of flatten(json)) {
    const id = `${ns}:${key}`; // flat or nested input both end up dotted
    const row = strings.get(id) ?? { ns, key, en: '', sw: '', source };
    if (!row[lang]) row[lang] = value;
    strings.set(id, row);
  }
}
for (const lang of ['en', 'sw']) {
  for (const file of readdirSync(join(LOCALES, lang)).filter((f) => f.endsWith('.json'))) {
    addLocale(
      lang,
      basename(file, '.json'),
      JSON.parse(readFileSync(join(LOCALES, lang, file), 'utf8')),
      'this branch',
    );
  }
}
/** Locale files at a commit: [{ lang, ns, json }]. */
function localesAt(commit) {
  const found = [];
  for (const lang of ['en', 'sw']) {
    const files = git('ls-tree', '--name-only', commit, '--', `${REPO_LOCALES}/${lang}/`)
      .split(/\r?\n/)
      .filter((f) => f.endsWith('.json'));
    for (const file of files) {
      found.push({
        lang,
        ns: basename(file, '.json'),
        json: JSON.parse(git('show', `${commit}:${file}`)),
      });
    }
  }
  return found;
}
for (const ref of refs) {
  // Only what the ref added counts: a key present at the merge base that this
  // branch has since removed stays removed. (A text the ref edited in an
  // existing key isn't picked up; regenerate on `main` once PRs merge.)
  const base = new Set(
    localesAt(git('merge-base', 'HEAD', ref).trim()).flatMap(({ ns, json }) =>
      flatten(json).map(([key]) => `${ns}:${key}`),
    ),
  );
  for (const { lang, ns, json } of localesAt(ref)) {
    for (const [key, value] of flatten(json)) {
      const id = `${ns}:${key}`;
      if (base.has(id) || strings.get(id)?.[lang]) continue;
      addLocale(lang, ns, { [key]: value }, ref);
    }
  }
}

// ─── Usage: which source files mention which keys ────────────────────────
const sources = []; // { name, text }
function walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!['i18n', 'test', 'node_modules'].includes(entry.name)) walk(p);
    } else if (/\.(tsx?|ts)$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)) {
      sources.push({
        name: basename(entry.name).replace(/\.tsx?$/, ''),
        text: readFileSync(p, 'utf8'),
      });
    }
  }
}
walk(join(FRONTEND, 'src'));
for (const ref of refs) {
  const files = git('ls-tree', '-r', '--name-only', ref, '--', 'frontend/src')
    .split('\n')
    .filter((f) => /\.(tsx?|ts)$/.test(f) && !/\.test\.tsx?$/.test(f) && !f.includes('/i18n/'));
  for (const f of files) {
    const name = basename(f).replace(/\.tsx?$/, '');
    // the ref's version too: an open PR may use new keys in a file this
    // branch also has
    sources.push({ name, text: git('show', `${ref}:${f}`) });
  }
}

/** Where a key is used. Literal `ns:key`, a bare `key` in a file that uses the
 * namespace, or a template prefix (`ns:state.${...}`) for run-time keys. */
function screensFor(ns, key) {
  const base = key.replace(/_(zero|one|two|few|many|other)$/, '');
  const exact = new Set();
  const dynamic = new Set();
  for (const { name, text } of sources) {
    const usesNs = text.includes(`'${ns}'`) || text.includes(`"${ns}"`) || text.includes(`${ns}:`);
    if (
      text.includes(`'${ns}:${base}'`) ||
      text.includes(`"${ns}:${base}"`) ||
      text.includes(`\`${ns}:${base}\``) ||
      (usesNs && (text.includes(`'${base}'`) || text.includes(`"${base}"`)))
    ) {
      exact.add(name);
      continue;
    }
    // template keys: `ns:a.b.${x}` or `a.b.${x}` in a file using ns
    for (const m of text.matchAll(/`([A-Za-z0-9_.:-]*)\$\{/g)) {
      const prefix = m[1];
      if (!prefix) continue;
      const full = prefix.includes(':') ? prefix : usesNs ? `${ns}:${prefix}` : null;
      if (full && `${ns}:${base}`.startsWith(full) && full.length > ns.length + 1)
        dynamic.add(name);
    }
  }
  const list = [
    ...exact,
    ...[...dynamic].filter((n) => !exact.has(n)).map((n) => `${n} (dynamic)`),
  ];
  return list.slice(0, 4).join(', ') + (list.length > 4 ? `, +${list.length - 4} more` : '');
}

// ─── Flags ───────────────────────────────────────────────────────────────
const placeholders = (s) =>
  [...s.matchAll(/\{\{\s*(\w+)\s*\}\}/g)]
    .map((m) => m[1])
    .sort()
    .join(',');
const BRANDS = /^(Fikisha|M-Pesa|KSh|eTIMS|OK|ID)$/i;
function flagsFor(row) {
  const flags = [];
  if (!row.sw) flags.push('missing Swahili');
  else if (
    row.en &&
    row.sw.trim() === row.en.trim() &&
    /[A-Za-z]{3,}/.test(row.en.replace(/\{\{\w+\}\}/g, '')) &&
    !BRANDS.test(row.en.trim())
  )
    flags.push('same as English');
  if (row.en && row.sw && placeholders(row.en) !== placeholders(row.sw))
    flags.push('placeholders differ');
  return flags.join('; ');
}

// ─── CSV ─────────────────────────────────────────────────────────────────
const csv = (v) => (/[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
const header = [
  'namespace',
  'key',
  'screens',
  'english',
  'swahili',
  'flags',
  'source',
  'reviewer_ok (Y/N)',
  'suggested_swahili',
  'reviewer_notes',
];
const rows = [...strings.values()].sort((a, b) =>
  a.ns === b.ns ? a.key.localeCompare(b.key) : a.ns.localeCompare(b.ns),
);
const lines = [header.join(',')];
const counts = { total: 0, same: 0, missing: 0, placeholders: 0, unmapped: 0, onRefs: 0 };
for (const row of rows) {
  const screens = screensFor(row.ns, row.key);
  const flags = flagsFor(row);
  counts.total++;
  if (flags.includes('same as English')) counts.same++;
  if (flags.includes('missing')) counts.missing++;
  if (flags.includes('placeholders')) counts.placeholders++;
  if (!screens && row.ns !== 'errors') counts.unmapped++;
  if (row.source !== 'this branch') counts.onRefs++;
  const where =
    screens ||
    (row.ns === 'errors' ? 'Error message (any screen)' : 'not found in code (possibly unused)');
  lines.push(
    [row.ns, row.key, where, row.en, row.sw, flags, row.source, '', '', ''].map(csv).join(','),
  );
}
// UTF-8 BOM so spreadsheet apps read Swahili and symbols correctly
writeFileSync(out, '﻿' + lines.join('\r\n') + '\r\n', 'utf8');
console.log(JSON.stringify({ out: relative(process.cwd(), out), ...counts }));
