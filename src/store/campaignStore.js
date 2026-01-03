import { create } from "zustand";
import { apiUrl, API_BASE_URL } from "../lib/api.js";

const ensureRelativePublicPath = (value) => {
  if (!value) return null;
  let path = value.trim();
  if (!path) return null;

  // Remove API base URL if present
  if (path.startsWith(API_BASE_URL)) {
    path = path.slice(API_BASE_URL.length);
  }

  // Handle full URLs containing /public/
  const publicIndex = path.indexOf("/public/");
  if (publicIndex !== -1) {
    path = path.slice(publicIndex + 1); // remove leading slash
  }

  // Remove leading slashes
  path = path.replace(/^\/+/, "");

  if (!path.startsWith("public/")) {
    path = `public/${path}`;
  }

  return path;
};

const buildImageEntry = (image) => {
  if (!image) return null;
  const filePathRaw = image.file_path || image.filePath || image.image_path || image.imagePath || image.url || image.image_url || "";
  const relativePath = ensureRelativePublicPath(filePathRaw);
  const imageUrlRaw = image.image_url || image.url || (relativePath ? `/${relativePath}` : "");
  const normalizedUrl = imageUrlRaw
    ? (imageUrlRaw.startsWith("/") ? imageUrlRaw : `/${imageUrlRaw}`)
    : (relativePath ? `/${relativePath}` : "");

  return {
    id: image.id ? String(image.id) : null,
    filePath: relativePath,
    image_url: normalizedUrl || null,
    previewUrl: normalizedUrl ? apiUrl(normalizedUrl) : "",
    generationMethod: image.generation_method || image.generationMethod || "user_upload",
    createdAt: image.created_at || image.createdAt || null,
  };
};
import apiClient from "../lib/apiClient.js";

function nowIso() {
  return new Date().toISOString();
}

export const useCampaignStore = create((set, get) => ({
  campaigns: [],
  recentActivity: [],
  preferences: {
    notifications: true,
  },
  isLoading: false,

  // Load campaigns from PostgreSQL
  loadCampaignsFromDB: async () => {
    set({ isLoading: true });
    try {
      const data = await apiClient.getPosts({ limit: 50 });

      if (data && data.success && data.posts) {
        // Load campaign names from localStorage
        const campaignNames = JSON.parse(localStorage.getItem('campaign_names') || '{}');

        const campaigns = data.posts.map(post => {
          const normalizedImages = Array.isArray(post.images)
            ? post.images.map(buildImageEntry).filter(Boolean)
            : [];

          let primaryRelativePath = null;
          if (normalizedImages.length > 0) {
            primaryRelativePath = normalizedImages[0].filePath;
          } else if (post.image_url || post.image_path) {
            primaryRelativePath = ensureRelativePublicPath(post.image_url || post.image_path);
          }

          const primaryUrl = primaryRelativePath ? `/${primaryRelativePath}` : null;
          const imageUrl = primaryUrl ? apiUrl(primaryUrl) : "";

          return {
            id: post.id,
            batchId: post.batch_id || null,
            createdAt: new Date(post.created_at).getTime(),
            campaignName: post.campaign_name || post.campaign_table_name || campaignNames[post.id] || "Untitled Campaign",
            productDescription: post.original_description,
            generatedContent: post.caption || "",
            scheduledAt: post.scheduled_at,
            status: post.scheduled_at && (post.status === "scheduled" || post.status === "Scheduled") ? "Scheduled" :
              (post.status === "posted" || post.status === "Posted" || post.status === "published" || post.status === "Published") ? "Posted" :
                (post.status === "failed" || post.status === "Failed") ? "Failed" : "Draft",
            imageUrl,
            image_path: primaryRelativePath,
            images: normalizedImages,
            platforms: Array.isArray(post.platforms) ? post.platforms : (post.platform ? [post.platform] : []),
            engagementMetrics: post.engagement_metrics || null,
            // Add additional fields from database if they exist
            driveFileId: post.drive_file_id || null,
            driveImageUrl: post.drive_image_url || null,
            imageFileId: post.image_file_id || null,
            calendarEventId: post.calendar_event_id || null,
            googleCalendarEventId: post.google_calendar_event_id || null,
            googleCalendarLink: post.google_calendar_link || null,
            activity: [
              { time: new Date(post.created_at).getTime(), text: "Campaign created" },
              post.caption ? { time: new Date(post.created_at).getTime() + 1000, text: "AI caption generated" } : null,
              (primaryRelativePath || post.image_path) ? { time: new Date(post.created_at).getTime() + 2000, text: "Image added" } : null,
              post.scheduled_at ? {
                time: new Date(post.created_at).getTime() + 3000,
                text: `Scheduled for ${new Date(post.scheduled_at).toLocaleString()}`,
              } : null,
            ].filter(Boolean),
          };
        });

        set({ campaigns });
        console.log(`✅ Loaded ${campaigns.length} campaigns from database`);

        // Store in localStorage as backup
        try {
          localStorage.setItem('campaigns_backup', JSON.stringify(campaigns));
        } catch (e) {
          console.warn('Failed to store campaigns backup:', e);
        }
      } else {
        console.log("No campaigns found in database");
        // Try to load from localStorage backup if database is empty
        try {
          const backup = localStorage.getItem('campaigns_backup');
          if (backup) {
            const campaigns = JSON.parse(backup);
            set({ campaigns });
            console.log(`📦 Loaded ${campaigns.length} campaigns from backup`);
          }
        } catch (e) {
          console.warn('Failed to load campaigns backup:', e);
        }
      }
    } catch (error) {
      console.error("Failed to load campaigns from database:", error);
      // Try to load from localStorage backup on network error
      try {
        const backup = localStorage.getItem('campaigns_backup');
        if (backup) {
          const campaigns = JSON.parse(backup);
          set({ campaigns });
          console.log(`📦 Loaded ${campaigns.length} campaigns from backup (network error)`);
        }
      } catch (e) {
        console.warn('Failed to load campaigns backup:', e);
      }
    } finally {
      set({ isLoading: false });
    }
  },
  addActivity: (text) =>
    set((state) => ({
      recentActivity: [
        { time: Date.now(), text },
        ...state.recentActivity,
      ].slice(0, 20),
    })),
  createCampaign: async ({
    campaignName,
    description,
    caption,
    imageUrl,
    scheduledAt = null,
    status = "Draft",
    batchId = null,
  }) => {
    const id = `cmp_${Math.random().toString(36).slice(2, 8)}`;
    const createdAt = Date.now();
    console.log(`🔍 Store createCampaign called - ID: ${id}, Campaign Name: "${campaignName}", Description: "${description}", Caption: "${caption?.substring(0, 50)}..."`);

    // Check if a campaign with the same description and caption already exists (regardless of batch ID)
    const existingCampaign = get().campaigns.find(c =>
      c.productDescription === description &&
      c.generatedContent === caption
    );

    if (existingCampaign) {
      console.log(`⚠️ Duplicate campaign detected, skipping creation. Existing ID: ${existingCampaign.id}, Batch ID: ${existingCampaign.batchId}`);
      return;
    }

    // Save to database with campaign name
    try {
      const postData = {
        original_description: description,
        caption: caption,
        image_path: imageUrl,
        scheduled_at: scheduledAt,
        status: status,
        batch_id: batchId,
        campaign_name: campaignName || ""
      };

      console.log(`💾 Saving campaign to database with campaign_name: "${campaignName}"`);
      const response = await apiClient.createPost(postData);

      if (response && response.success) {
        console.log(`✅ Campaign saved to database with ID: ${response.post_id}`);
        // Use the database ID instead of generated ID
        const newCampaign = {
          id: response.post_id,
          batchId,
          createdAt,
          campaignName: campaignName || "",
          productDescription: description,
          generatedContent: caption || "",
          scheduledAt,
          status,
          imageUrl: imageUrl || "",
          activity: [
            { time: createdAt, text: "Campaign created" },
            caption ? { time: Date.now(), text: "AI caption generated" } : null,
            imageUrl ? { time: Date.now(), text: "AI image generated" } : null,
            scheduledAt
              ? {
                time: Date.now(),
                text: `Scheduled for ${new Date(scheduledAt).toLocaleString()}`,
              }
              : null,
          ].filter(Boolean),
        };

        // Add to local state
        set((state) => ({
          campaigns: [...state.campaigns, newCampaign],
        }));

        // Store campaign name in localStorage for backup
        try {
          const campaignNames = JSON.parse(localStorage.getItem('campaign_names') || '{}');
          campaignNames[response.post_id] = campaignName || "";
          localStorage.setItem('campaign_names', JSON.stringify(campaignNames));
        } catch (e) {
          console.warn('Failed to store campaign name backup:', e);
        }

        return;
      } else {
        console.error(`❌ Failed to save campaign to database:`, response);
      }
    } catch (error) {
      console.error(`❌ Error saving campaign to database:`, error);
    }

    // Fallback: create campaign in local state only (if database save fails)
    const newCampaign = {
      id,
      batchId,
      createdAt,
      campaignName: campaignName || "",
      productDescription: description,
      generatedContent: caption || "",
      scheduledAt,
      status,
      imageUrl: imageUrl || "",
      activity: [
        { time: createdAt, text: "Campaign created" },
        caption ? { time: Date.now(), text: "AI caption generated" } : null,
        imageUrl ? { time: Date.now(), text: "AI image generated" } : null,
        scheduledAt
          ? {
            time: Date.now(),
            text: `Scheduled for ${new Date(scheduledAt).toLocaleString()}`,
          }
          : null,
      ].filter(Boolean),
    };

    // Add to local state immediately
    set((state) => ({ campaigns: [newCampaign, ...state.campaigns] }));
    get().addActivity(`Created campaign ${id}`);

    // Store campaign name in localStorage for persistence (temporary until database column is added)
    if (campaignName) {
      try {
        const campaignNames = JSON.parse(localStorage.getItem('campaign_names') || '{}');
        campaignNames[id] = campaignName;
        localStorage.setItem('campaign_names', JSON.stringify(campaignNames));
      } catch (e) {
        console.warn('Failed to store campaign name:', e);
      }
    }



    // Try to sync with database
    try {
      // Handle image path - remove API base URL for all images
      let imagePath = null;
      if (imageUrl) {
        imagePath = imageUrl.replace(API_BASE_URL, '');
        console.log(`📸 Image path processed: ${imagePath}`);
      }

      const postData = {
        // campaign_name: campaignName || "", // Temporarily disabled until database column is added
        original_description: description,
        caption: caption || "",
        image_path: imagePath,
        scheduled_at: scheduledAt,
        status: status.toLowerCase(),
        platform: "instagram",
        batch_id: batchId
      };

      console.log(`Saving campaign ${id} to database:`, postData);
      console.log(`🔍 Store createCampaign - received batchId: ${batchId}, using batch_id: ${postData.batch_id}`);
      // Fire-and-forget createPost to avoid blocking UI
      apiClient.createPost(postData)
        .then((data) => {
          console.log(`📊 Database response for campaign ${id}:`, data);
          if (data && data.success && data.post_id) {
            console.log(`✅ Campaign ${id} saved to database with ID: ${data.post_id}`);
            // Replace temporary id with real DB id so future updates/deletes work
            set((state) => ({
              campaigns: state.campaigns.map((c) =>
                c.id === id ? { ...c, id: String(data.post_id) } : c
              ),
            }));
          } else {
            console.error(`Failed to save campaign ${id}:`, data);
            console.error(`Response data:`, JSON.stringify(data, null, 2));
          }
        })
        .catch((error) => {
          console.error(`Database error for campaign ${id}:`, error);
          console.error(`Error details:`, error.message, error.stack);
        });
    } catch (error) {
      console.error("Error syncing campaign with database:", error);
    }

    return id;
  },
  updateCampaign: async (id, updates) => {
    // Update local state immediately
    set((state) => ({
      campaigns: state.campaigns.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
    }));

    // Try to sync with database if this is a scheduling, status, or image update
    if (updates.scheduledAt || updates.status || updates.imageUrl) {
      try {
        const campaign = get().campaigns.find(c => c.id === id);
        if (campaign) {
          const postData = {};

          // Add scheduling/status updates
          if (updates.scheduledAt || updates.status) {
            postData.scheduled_at = updates.scheduledAt || campaign.scheduledAt;
            postData.status = (updates.status || campaign.status).toLowerCase();
          }

          // Add image updates
          if (updates.imageUrl) {
            // Handle image path - remove API base URL for database storage
            let imagePath = updates.imageUrl;
            if (imagePath && imagePath.startsWith('http')) {
              imagePath = imagePath.replace(API_BASE_URL, '');
            }
            postData.image_path = imagePath;
            console.log(`📸 Updating image path in database: ${imagePath}`);
          }

          console.log(`Updating campaign ${id} in database:`, postData);
          // Note: We're not awaiting this to avoid blocking UI
          apiClient.updatePost(id, postData)
            .then(data => {
              if (data && data.success) {
                console.log(`✅ Campaign ${id} updated in database successfully`);
              } else {
                console.error(`❌ Failed to update campaign ${id}:`, data && (data.error || data.message));
              }
            })
            .catch(error => {
              console.error(`❌ Database update error for campaign ${id}:`, error);
            });
        }
      } catch (error) {
        console.error("Error syncing campaign update with database:", error);
      }
    }
  },
  updateCampaignsWhere: (predicate, updatesFn) =>
    set((state) => ({
      campaigns: state.campaigns.map((c) =>
        predicate(c) ? { ...c, ...updatesFn(c) } : c
      ),
    })),
  deleteCampaign: async (id) => {
    const prev = get().campaigns;
    // Get campaign name before deleting
    const campaign = prev.find(c => c.id === id);
    const campaignName = campaign ? (campaign.campaignName || campaign.productDescription || 'Unknown Campaign') : 'Unknown Campaign';

    // Optimistic remove from local state
    set((state) => ({ campaigns: state.campaigns.filter((c) => c.id !== id) }));
    get().addActivity(`Deleted campaign "${campaignName}"`);

    // Attempt backend delete; ignore if the id was only local (e.g., cmp_*)
    try {
      const resp = await apiClient.deletePost(id);
      if (!resp || resp.success === false) {
        console.warn(`Backend delete returned error for ${id}:`, resp && (resp.error || resp.message));
      }
    } catch (e) {
      console.error(`Backend delete failed for ${id}:`, e);
      // Optional: rollback on hard failure
      // set({ campaigns: prev });
    }
  },
  deleteCampaignsWhere: (predicate) =>
    set((state) => ({
      campaigns: state.campaigns.filter((c) => !predicate(c)),
    })),
  clearAllCampaigns: async () => {
    try {
      await apiClient.clearAllPosts();
      set({ campaigns: [] });
      get().addActivity("Cleared all campaigns");
    } catch (error) {
      console.error("Failed to clear all campaigns:", error);
    }
  },
  // Simulate real-time status updates
  tick: () => {
    const now = Date.now();
    set((state) => ({
      campaigns: state.campaigns.map((c) => {
        if (
          c.status === "Scheduled" &&
          c.scheduledAt &&
          new Date(c.scheduledAt).getTime() <= now
        ) {
          const didFail = Math.random() < 0.1;
          const status = didFail ? "Failed" : "Posted";
          return {
            ...c,
            status,
            activity: [
              {
                time: now,
                text: status === "Posted" ? "Post published" : "Posting failed",
              },
              ...(c.activity || []),
            ],
          };
        }
        return c;
      }),
    }));
  },
}));

// Start a simple interval for real-time updates
if (typeof window !== "undefined") {
  setInterval(() => {
    try {
      useCampaignStore.getState().tick();
    } catch { }
  }, 5000);
}
