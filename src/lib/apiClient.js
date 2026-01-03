import { apiFetch, apiUrl } from "./api.js";

async function handleResponse(response) {
  const text = await response.text();
  try {
    const json = text ? JSON.parse(text) : {};
    if (!response.ok) {
      const err = (json && (json.error || json.detail)) || response.statusText || "Request failed";
      throw new Error(err);
    }
    // If API uses { success: boolean } semantics, surface error when success === false
    if (json && Object.prototype.hasOwnProperty.call(json, "success") && json.success === false) {
      const err = json.error || json.message || "Request returned success=false";
      throw new Error(err);
    }
    return json;
  } catch (e) {
    // If JSON.parse failed but response.ok is true, return raw text
    if (response.ok) return text;
    throw e;
  }
}

// Post generation endpoints
export async function generatePost({ description, caption_provider, image_provider, platforms, subreddit } = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const res = await apiFetch("/generate-post", {
    method: "POST",
    headers,
    body: JSON.stringify({ description, caption_provider, image_provider, platforms, subreddit }),
  });
  return handleResponse(res);
}

export async function generateBatch({ description, days, num_posts, caption_provider, image_provider, asset_type, platforms, subreddit, campaign_name } = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const res = await apiFetch("/generate-batch", {
    method: "POST",
    headers,
    body: JSON.stringify({ description, days, num_posts, caption_provider, image_provider, asset_type, platforms, subreddit, campaign_name }),
  });
  return handleResponse(res);
}

export async function generateCaptionsBatch({ description, num_posts, days, caption_provider } = {}) {
  const res = await apiFetch("/generate-captions-batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, num_posts, days, caption_provider }),
  });
  return handleResponse(res);
}

export async function generateImageOnly({ description, image_provider } = {}) {
  const res = await apiFetch("/generate-image-only", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, image_provider }),
  });
  return handleResponse(res);
}

export async function generateVideoOnly({ description, video_provider = "modelscope", duration_seconds = 30 } = {}) {
  const res = await apiFetch("/generate-video-only", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, video_provider, duration_seconds }),
  });
  return handleResponse(res);
}

export async function createBatch({ description, days, num_posts, campaign_name } = {}) {
  const res = await apiFetch("/api/batch/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, days, num_posts, campaign_name }),
  });
  return handleResponse(res);
}

// Posts / campaigns
export async function getPosts({ limit = 50 } = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = {};

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const res = await apiFetch(`/api/posts?limit=${encodeURIComponent(limit)}`, {
    headers
  });
  return handleResponse(res);
}

export async function createPost(postData = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };
  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }
  const res = await apiFetch("/api/posts", {
    method: "POST",
    headers,
    body: JSON.stringify(postData),
  });
  return handleResponse(res);
}

export async function updatePost(postId, updateData = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };
  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }
  const res = await apiFetch(`/api/posts/${postId}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(updateData),
  });
  return handleResponse(res);
}

export async function deletePost(postId) {
  const res = await apiFetch(`/api/posts/${postId}`, { method: "DELETE" });
  return handleResponse(res);
}

export async function clearAllPosts() {
  const res = await apiFetch(`/api/posts/clear-all`, { method: "DELETE" });
  return handleResponse(res);
}

export async function uploadCustomImage({ data_url, description } = {}) {
  const res = await apiFetch("/upload-custom-image", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data_url, description }),
  });
  return handleResponse(res);
}

// Calendar
export async function getCalendarEvents(params = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = {};

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const qs = new URLSearchParams(params).toString();
  const res = await apiFetch(`/api/calendar/events${qs ? `?${qs}` : ""}`, {
    headers
  });
  return handleResponse(res);
}

export async function createCalendarEvent(eventData = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };
  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }
  const res = await apiFetch(`/api/calendar/events`, {
    method: "POST",
    headers,
    body: JSON.stringify(eventData),
  });
  return handleResponse(res);
}

export async function updateCalendarEvent(eventId, updateData = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };
  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }
  const res = await apiFetch(`/api/calendar/events/${encodeURIComponent(eventId)}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(updateData),
  });
  return handleResponse(res);
}

export async function deleteCalendarEvent(eventId) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = {};
  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }
  const res = await apiFetch(`/api/calendar/events/${encodeURIComponent(eventId)}`, {
    method: "DELETE",
    headers
  });
  return handleResponse(res);
}

// Google integrations (backend routes)
export async function getGoogleStatus() {
  const res = await apiFetch(`/google/status`);
  return handleResponse(res);
}

export async function saveCampaignToDrive(campaignData = {}) {
  const res = await apiFetch(`/google-drive/save-campaign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(campaignData),
  });
  return handleResponse(res);
}

export async function createGoogleCalendarEvent(data = {}) {
  const res = await apiFetch(`/google-calendar/create-event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function getGoogleUpcomingEvents() {
  const res = await apiFetch(`/google-calendar/upcoming-events`);
  return handleResponse(res);
}

// Analytics / status
export async function getAnalyticsOverview() {
  const res = await apiFetch(`/api/analytics/overview`);
  return handleResponse(res);
}

export async function getAnalyticsPosts({ limit = 10 } = {}) {
  const res = await apiFetch(`/api/analytics/posts?limit=${encodeURIComponent(limit)}`);
  return handleResponse(res);
}

export async function getFollowers() {
  const res = await apiFetch(`/api/analytics/followers`);
  return handleResponse(res);
}

export async function getHealth() {
  const res = await apiFetch(`/health`);
  return handleResponse(res);
}

export async function getHero() {
  const res = await apiFetch(`/api/hero`);
  return handleResponse(res);
}

export async function getScheduledPosts() {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = {};

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const res = await apiFetch(`/api/scheduled-posts`, {
    headers
  });
  return handleResponse(res);
}

export async function getAllPosts({ limit = 50 } = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = {};

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const res = await apiFetch(`/api/posts?limit=${encodeURIComponent(limit)}`, {
    headers
  });
  return handleResponse(res);
}

export async function getSchedulerStatus() {
  const res = await apiFetch(`/api/scheduler/status`);
  return handleResponse(res);
}

// Trending topics
export async function getTrendingTopics({ category } = {}) {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  const res = await apiFetch(`/api/trending/ai-topics${qs}`);
  return handleResponse(res);
}

export async function refreshTrendingTopics() {
  const res = await apiFetch(`/api/trending/refresh`, { method: "POST" });
  return handleResponse(res);
}

// Scheduling
export async function generateScheduleDates({ num_posts, days } = {}) {
  const res = await apiFetch("/api/generate-schedule", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ num_posts, days }),
  });
  return handleResponse(res);
}

// Schedule a post (authenticated)
export async function schedulePost(postId, data = {}) {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };
  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }
  const res = await apiFetch(`/api/posts/${postId}/schedule`, {
    method: "PUT",
    headers,
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

// Authentication endpoints
export async function register({ email, password, name }) {
  const res = await apiFetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  return handleResponse(res);
}

export async function login({ email, password }) {
  const res = await apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse(res);
}

export async function deleteAccount() {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = { "Content-Type": "application/json" };

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const res = await apiFetch("/auth/delete-account", {
    method: "DELETE",
    headers
  });
  return handleResponse(res);
}

// Check if user has any connected platforms
export async function checkPlatformConnections() {
  const token = localStorage.getItem('auth-storage');
  const authData = token ? JSON.parse(token) : null;
  const headers = {};

  if (authData?.state?.token) {
    headers['Authorization'] = `Bearer ${authData.state.token}`;
  }

  const res = await apiFetch("/social-media/check-connections", {
    headers
  });
  return handleResponse(res);
}

export default {
  generatePost,
  generateBatch,
  generateCaptionsBatch,
  generateImageOnly,
  generateVideoOnly,
  createBatch,
  getPosts,
  createPost,
  updatePost,
  deletePost,
  clearAllPosts,
  uploadCustomImage,
  getCalendarEvents,
  createCalendarEvent,
  updateCalendarEvent,
  deleteCalendarEvent,
  getGoogleStatus,
  saveCampaignToDrive,
  createGoogleCalendarEvent,
  getGoogleUpcomingEvents,
  getAnalyticsOverview,
  getAnalyticsPosts,
  getFollowers,
  getHealth,
  getHero,
  getScheduledPosts,
  getAllPosts,
  getSchedulerStatus,
  getTrendingTopics,
  refreshTrendingTopics,
  generateScheduleDates,
  schedulePost,
  register,
  login,
  deleteAccount,
  checkPlatformConnections,
};


