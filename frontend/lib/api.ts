export type JobStage =
  | "queued"
  | "script"
  | "image"
  | "voice"
  | "subtitles"
  | "assembly"
  | "upload"
  | "done"
  | "failed";

export interface StageProgress {
  stage: JobStage;
  label: string;
  progress: number;
  detail?: string | null;
}

export type MediaType = "video" | "podcast";

export interface Video {
  id: string;
  title: string;
  topic: string;
  duration: number;
  created_at: string;
  file_url: string;
  audio_url?: string | null;
  thumbnail_url?: string | null;
  resolution: string;
  scene_count: number;
  youtube_url?: string | null;
  media_type: MediaType;
}

export interface Job {
  id: string;
  topic: string;
  duration: number;
  key_points?: string | null;
  stage: JobStage;
  stages: StageProgress[];
  progress: number;
  error?: string | null;
  video?: Video | null;
  created_at: string;
  updated_at: string;
  auto_upload: boolean;
  privacy: string;
  youtube_url?: string | null;
  media_type: MediaType;
}

// `NEXT_PUBLIC_API_URL` is set in Vercel to the Fly backend (e.g.
// "https://fragment-backend.fly.dev"). Empty for local dev so paths stay relative
// and the Next.js rewrite/proxy can take over. Strip any trailing slash so
// `${BASE}/api/...` never doubles up.
const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

/** Turn backend-relative media paths ("/media/...") into absolute URLs when
 *  the API lives on a different origin. No-op in local dev (BASE === ""). */
function absolutize(url: string | null | undefined): string | null | undefined {
  if (!url) return url;
  if (/^https?:\/\//i.test(url)) return url;
  return `${BASE}${url}`;
}

function normalizeVideo(v: Video): Video {
  return {
    ...v,
    file_url: absolutize(v.file_url) as string,
    thumbnail_url: absolutize(v.thumbnail_url),
    audio_url: absolutize(v.audio_url),
  };
}

function normalizeJob(j: Job): Job {
  return { ...j, video: j.video ? normalizeVideo(j.video) : j.video };
}

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`${r.status} ${r.statusText}${txt ? ` — ${txt}` : ""}`);
  }
  return r.json();
}

export async function generate(payload: {
  topic: string;
  duration: number;
  key_points?: string;
  privacy?: string;
  media_type?: MediaType;
}): Promise<Job> {
  const j = await json<Job>(
    await fetch(`${BASE}/api/generate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ media_type: "video", ...payload, auto_upload: true }),
      cache: "no-store",
    })
  );
  return normalizeJob(j);
}

export async function getJob(id: string): Promise<Job> {
  return normalizeJob(await json<Job>(await fetch(`${BASE}/api/jobs/${id}`, { cache: "no-store" })));
}

export async function listJobs(): Promise<Job[]> {
  const js = await json<Job[]>(await fetch(`${BASE}/api/jobs`, { cache: "no-store" }));
  return js.map(normalizeJob);
}

export async function listVideos(q?: string): Promise<Video[]> {
  const url = q ? `${BASE}/api/videos?q=${encodeURIComponent(q)}` : `${BASE}/api/videos`;
  const vs = await json<Video[]>(await fetch(url, { cache: "no-store" }));
  return vs.map(normalizeVideo);
}

export async function deleteVideo(id: string): Promise<void> {
  await fetch(`${BASE}/api/videos/${id}`, { method: "DELETE" });
}

export async function clearPendingJobs(): Promise<{ cleared: number }> {
  return json(await fetch(`${BASE}/api/jobs/pending`, { method: "DELETE" }));
}

export interface Health {
  status: string;
  mock_mode: boolean;
  version: string;
  channel_url?: string | null;
}

export async function health(): Promise<Health> {
  return json<Health>(await fetch(`${BASE}/api/health`, { cache: "no-store" }));
}
