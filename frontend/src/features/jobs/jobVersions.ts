/**
 * The last version of each job this tab has seen (ADR-2D-44). Job detail
 * and every job action return the job's `version`; the next action on that
 * job sends it back as `If-Match`. If someone else changed the job in
 * between, the server refuses with `412 stale_job` instead of acting on
 * what the person no longer sees (the query client then refreshes it).
 *
 * Unknown job → no header, which the server still accepts.
 */
const versions = new Map<string, number>();

export function rememberJobVersion<T>(job: T): T {
  const j = job as { id?: unknown; version?: unknown } | null | undefined;
  if (j && typeof j.id === 'string' && typeof j.version === 'number') versions.set(j.id, j.version);
  return job;
}

export function jobVersion(jobId: string): number | undefined {
  return versions.get(jobId);
}

/** Tests, and sign-out. */
export function forgetJobVersions(): void {
  versions.clear();
}
