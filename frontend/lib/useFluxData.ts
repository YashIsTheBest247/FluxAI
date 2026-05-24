"use client";

import { useCallback, useEffect, useState } from "react";
import { clearPendingJobs, listJobs, listVideos, type Job, type Video } from "./api";

let _jobs: Job[] = [];
let _videos: Video[] = [];
const _jobsListeners = new Set<(j: Job[]) => void>();
const _videosListeners = new Set<(v: Video[]) => void>();
let _polling = false;
let _pollTimer: ReturnType<typeof setInterval> | null = null;
let _bootCleanupDone = false;

async function tick() {
  try {
    const [j, v] = await Promise.all([listJobs(), listVideos()]);
    _jobs = j;
    _videos = v;
    _jobsListeners.forEach((fn) => fn(_jobs));
    _videosListeners.forEach((fn) => fn(_videos));
  } catch { /* swallow — keep polling */ }
}

async function bootCleanup() {
  // On every fresh page load, wipe queued / in-progress / failed jobs from the previous session.
  // Completed jobs stay (their videos live in the library).
  if (_bootCleanupDone) return;
  _bootCleanupDone = true;
  try {
    await clearPendingJobs();
  } catch { /* if the backend is down we'll just continue */ }
}

function ensurePolling() {
  if (_polling) return;
  _polling = true;
  bootCleanup().then(tick);
  _pollTimer = setInterval(tick, 2500);
}

function stopPolling() {
  if (_jobsListeners.size === 0 && _videosListeners.size === 0 && _pollTimer) {
    clearInterval(_pollTimer);
    _pollTimer = null;
    _polling = false;
  }
}

/** Live view of jobs + videos. Refreshes every 2.5s while any consumer is mounted. */
export function useFluxData() {
  const [jobs, setJobs] = useState<Job[]>(_jobs);
  const [videos, setVideos] = useState<Video[]>(_videos);

  useEffect(() => {
    _jobsListeners.add(setJobs);
    _videosListeners.add(setVideos);
    ensurePolling();
    return () => {
      _jobsListeners.delete(setJobs);
      _videosListeners.delete(setVideos);
      stopPolling();
    };
  }, []);

  const refresh = useCallback(() => tick(), []);
  return { jobs, videos, refresh };
}
