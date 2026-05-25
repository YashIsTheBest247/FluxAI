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

const BASE = "";

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
  return json<Job>(
    await fetch(`${BASE}/api/generate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ media_type: "video", ...payload, auto_upload: true }),
      cache: "no-store",
    })
  );
}

export async function getJob(id: string): Promise<Job> {
  return json<Job>(await fetch(`${BASE}/api/jobs/${id}`, { cache: "no-store" }));
}

export async function listJobs(): Promise<Job[]> {
  return json<Job[]>(await fetch(`${BASE}/api/jobs`, { cache: "no-store" }));
}

export async function listVideos(q?: string): Promise<Video[]> {
  const url = q ? `${BASE}/api/videos?q=${encodeURIComponent(q)}` : `${BASE}/api/videos`;
  return json<Video[]>(await fetch(url, { cache: "no-store" }));
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
