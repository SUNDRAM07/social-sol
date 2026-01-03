import { useEffect, useMemo, useState, useRef } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate } from "react-router-dom";
import { useCampaignStore } from "../store/campaignStore.js";
import { toast } from "sonner";
import { deletePost, updatePost, uploadCustomImage } from "../lib/apiClient.js";
import { apiUrl, API_BASE_URL } from "../lib/api.js";

const generateLocalImageId = () => `${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;

const ensureRelativePublicPath = (value) => {
  if (!value) return null;
  let path = value.trim();
  if (!path) return null;

  if (path.startsWith(API_BASE_URL)) {
    path = path.slice(API_BASE_URL.length);
  }

  const publicIndex = path.indexOf("/public/");
  if (publicIndex !== -1) {
    path = path.slice(publicIndex + 1);
  }

  path = path.replace(/^\/+/, "");

  if (!path.startsWith("public/")) {
    path = path.replace(/^public\/?/, "");
    path = `public/${path}`;
  }

  return path;
};

const toPublicUrl = (value) => {
  const relative = ensureRelativePublicPath(value);
  return relative ? `/${relative}` : null;
};

const toPreviewUrl = (value) => {
  if (!value) return "";
  const normalized = value.startsWith("/") ? value : `/${value}`;
  return apiUrl(normalized);
};

const createEditingImageEntry = (image = {}, options = {}) => {
  const relativePath = ensureRelativePublicPath(
    image.filePath ||
    image.file_path ||
    image.image_path ||
    image.image_url ||
    image.url ||
    ""
  );

  const imageUrl = relativePath
    ? `/${relativePath}`
    : (image.image_url && image.image_url.startsWith("/") ? image.image_url : null);

  const previewUrl = image.previewUrl
    || (imageUrl ? apiUrl(imageUrl) : (image.url && /^https?:\/\//i.test(image.url) ? image.url : ""));

  return {
    id: image.id ? String(image.id) : null,
    filePath: relativePath,
    image_url: imageUrl,
    previewUrl,
    generationMethod: image.generationMethod || image.generation_method || (options.isNew ? "user_upload" : (image.generation_method || "user_upload")),
    createdAt: image.createdAt || image.created_at || null,
    remove: false,
    isNew: !!options.isNew,
    localId: options.localId || generateLocalImageId(),
  };
};

const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = (e) => resolve(e.target.result);
  reader.onerror = reject;
  reader.readAsDataURL(file);
});

function MyCampaigns() {
  const navigate = useNavigate();
  const campaigns = useCampaignStore((s) => s.campaigns);
  const loadCampaignsFromDB = useCampaignStore((s) => s.loadCampaignsFromDB);
  const deleteCampaign = useCampaignStore((s) => s.deleteCampaign);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const menuRef = useRef(null);
  const buttonRefs = useRef({});
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(null);
  const [editingPosts, setEditingPosts] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewingCampaign, setViewingCampaign] = useState(null);
  const [viewingPosts, setViewingPosts] = useState([]);

  useEffect(() => { loadCampaignsFromDB(); }, [loadCampaignsFromDB]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        // Check if click is on a menu button
        const isMenuButton = Object.values(buttonRefs.current).some(ref => 
          ref && ref.contains(event.target)
        );
        if (!isMenuButton) {
          setOpenMenuId(null);
        }
      }
    };
    if (openMenuId) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [openMenuId]);

  const rows = useMemo(() => {
    const sumReach = (m) => {
      if (!m) return 0;
      if (typeof m.reach === 'number') return m.reach;
      if (typeof m.impressions === 'number') return m.impressions;
      return 0;
    };
    const sumEngagement = (m) => {
      if (!m) return 0;
      if (typeof m.engaged_users === 'number') return m.engaged_users;
      const r = m.reactions || {};
      const likes = Number(r.like || r.likes || 0);
      const comments = Number(m.comments || 0);
      const shares = Number(m.shares || 0);
      const saves = Number(m.saves || 0);
      return likes + comments + shares + saves;
    };

    const map = new Map();
    for (const c of campaigns) {
      const key = (c.campaignName && c.campaignName.trim()) || c.batchId || c.id;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(c);
    }
    return Array.from(map.entries()).map(([key, items]) => {
      const total = items.length;
      const scheduled = items.filter(i => i.status === 'Scheduled').length;
      const posted = items.filter(i => i.status === 'Posted').length;
      const name = items[0]?.campaignName || items[0]?.productDescription || 'Untitled Campaign';
      const allPlatforms = Array.from(new Set(items.flatMap(i => i.platforms || (i.platform ? [i.platform] : [])))).filter(Boolean);
      const next = items.map(i => i.scheduledAt).filter(Boolean).map(d=>new Date(d)).filter(d=>!isNaN(d)).sort((a,b)=>a-b)[0] || null;
      const reach = items.reduce((acc, it) => acc + sumReach(it.engagementMetrics), 0);
      const engagement = items.reduce((acc, it) => acc + sumEngagement(it.engagementMetrics), 0);
      return {
        id: String(key),
        name,
        status: posted>0 ? 'Active' : (scheduled>0 ? 'Scheduled' : 'Draft'),
        platforms: allPlatforms,
        posts: total,
        reach: reach || '-',
        engagement: engagement || '-',
        scheduledAt: next,
        createdAt: items[0]?.createdAt || Date.now(),
      };
    }).sort((a,b)=> (b.createdAt||0)-(a.createdAt||0));
  }, [campaigns]);

  const stats = useMemo(()=>({
    total: rows.length,
    active: rows.filter(r=>r.status==='Active').length,
    scheduled: rows.filter(r=>r.status==='Scheduled').length,
    drafts: rows.filter(r=>r.status==='Draft').length,
  }), [rows]);

  const handleUpdate = (row) => {
    // Get all posts for this campaign
    const campaignPosts = campaigns.filter(c => 
      (c.campaignName && c.campaignName.trim() === row.name) || 
      (c.batchId && c.batchId === row.id)
    );
    // Open edit modal instead of navigating
    setEditingCampaign(row);
    setEditingPosts(campaignPosts.map(post => {
      // Format scheduled date for datetime-local input (YYYY-MM-DDTHH:mm)
      let editScheduledAt = '';
      if (post.scheduledAt) {
        try {
          const scheduledDate = new Date(post.scheduledAt);
          if (!isNaN(scheduledDate.getTime())) {
            const year = scheduledDate.getFullYear();
            const month = String(scheduledDate.getMonth() + 1).padStart(2, '0');
            const day = String(scheduledDate.getDate()).padStart(2, '0');
            const hours = String(scheduledDate.getHours()).padStart(2, '0');
            const minutes = String(scheduledDate.getMinutes()).padStart(2, '0');
            editScheduledAt = `${year}-${month}-${day}T${hours}:${minutes}`;
          }
        } catch (e) {
          console.warn('Error formatting scheduled date:', e);
        }
      }

      const normalizedImages = Array.isArray(post.images) && post.images.length
        ? post.images.map(image => createEditingImageEntry(image))
        : [];

      let fallbackImage = null;
      if (!normalizedImages.length && (post.imageUrl || post.image_path)) {
        fallbackImage = createEditingImageEntry({
          image_url: post.imageUrl || post.image_path || "",
          file_path: post.image_path || null,
          previewUrl: post.imageUrl || null,
        });
      }

      const editImages = normalizedImages.length
        ? normalizedImages
        : (fallbackImage ? [fallbackImage] : []);

      return {
        ...post,
        editCaption: post.caption || post.generatedContent || '',
        editScheduledAt,
        editPlatforms: post.platforms || [],
        editImages,
        originalImagesSignature: JSON.stringify(
          (editImages || []).map(img => ({
            id: img.id,
            filePath: img.filePath,
            image_url: img.image_url,
          }))
        ),
      };
    }));
    setEditModalOpen(true);
    setOpenMenuId(null); // Close the dropdown menu
  };

  const handleDelete = async (row) => {
    if (!window.confirm(`Are you sure you want to delete campaign "${row.name}"? This will delete all ${row.posts} posts.`)) {
      return;
    }
    
    try {
      // Get all posts for this campaign
      const campaignPosts = campaigns.filter(c => 
        (c.campaignName && c.campaignName.trim() === row.name) || 
        (c.batchId && c.batchId === row.id)
      );
      
      // Delete all posts
      for (const post of campaignPosts) {
        try {
          await deletePost(post.id);
          deleteCampaign(post.id);
        } catch (e) {
          console.error(`Failed to delete post ${post.id}:`, e);
        }
      }
      
      toast.success(`Campaign "${row.name}" deleted successfully`);
      await loadCampaignsFromDB();
    } catch (error) {
      console.error('Error deleting campaign:', error);
      toast.error('Failed to delete campaign');
    }
  };

  const handleView = (row) => {
    // Get all posts for this campaign
    const campaignPosts = campaigns.filter(c => 
      (c.campaignName && c.campaignName.trim() === row.name) || 
      (c.batchId && c.batchId === row.id)
    );
    // Open view modal instead of navigating
    setViewingCampaign(row);
    setViewingPosts(campaignPosts);
    setViewModalOpen(true);
    setOpenMenuId(null); // Close the dropdown menu
  };

  const handleCalendar = (row) => {
    // Navigate to calendar view filtered by this campaign
    navigate('/calendar', { 
      state: { 
        campaignId: row.id,
        campaignName: row.name
      } 
    });
  };

  const handleSaveCampaign = async () => {
    if (!editingCampaign || editingPosts.length === 0) return;

    setIsSaving(true);
    try {
      let successCount = 0;
      let errorCount = 0;

      for (let index = 0; index < editingPosts.length; index++) {
        const post = editingPosts[index];
        try {
          const updateData = {};

          const originalCaption = post.caption || post.generatedContent || '';
          if ((post.editCaption || '') !== originalCaption) {
            updateData.caption = post.editCaption || '';
          }

          const editScheduledAtTrimmed = (post.editScheduledAt || '').trim();
          if (editScheduledAtTrimmed) {
            try {
              const newScheduledAt = new Date(editScheduledAtTrimmed).toISOString();
              let originalScheduledAt = '';
              if (post.scheduledAt) {
                try {
                  const originalDate = new Date(post.scheduledAt);
                  if (!isNaN(originalDate.getTime())) {
                    originalScheduledAt = originalDate.toISOString();
                  }
                } catch (e) {
                  console.warn('Error parsing original scheduled_at:', e);
                }
              }
              if (newScheduledAt !== originalScheduledAt) {
                updateData.scheduled_at = newScheduledAt;
                if (post.status !== 'Posted' && post.status !== 'posted') {
                  updateData.status = 'scheduled';
                }
                console.log(`✅ Scheduled date updated for post ${post.id}: ${newScheduledAt}`);
              }
            } catch (error) {
              console.error(`Error parsing scheduled date for post ${post.id}:`, error);
              toast.error(`Invalid date format for post ${index + 1}`);
            }
          } else if (post.scheduledAt) {
            updateData.scheduled_at = null;
            if (post.status !== 'Posted' && post.status !== 'posted') {
              updateData.status = 'draft';
            }
            console.log(`✅ Scheduled date cleared for post ${post.id}`);
          }

          if (JSON.stringify((post.editPlatforms || []).slice().sort()) !== JSON.stringify((post.platforms || []).slice().sort())) {
            updateData.platforms = post.editPlatforms || [];
          }

          const editImages = Array.isArray(post.editImages) ? post.editImages : [];
          const imagesPayload = editImages.map((image, imageIndex) => {
            const relativePath = image.filePath || ensureRelativePublicPath(image.image_url) || null;
            const imageUrl = relativePath ? `/${relativePath}` : (image.image_url || null);
            return {
              id: image.id,
              image_url: imageUrl,
              file_path: relativePath,
              remove: !!image.remove,
              order: imageIndex,
              generation_method: image.generationMethod || (image.isNew ? "user_upload" : "user_upload"),
            };
          });

          const hadImagesBefore = Array.isArray(post.images) && post.images.length > 0;
          const originalImagesSignature = post.originalImagesSignature || "";
          const newImagesSignature = JSON.stringify(
            imagesPayload.map(img => ({
              id: img.id,
              file_path: img.file_path,
              image_url: img.image_url,
              remove: !!img.remove,
            }))
          );

          if (newImagesSignature !== originalImagesSignature) {
            updateData.images = imagesPayload;
            const primaryImage = imagesPayload.find((img) => !img.remove && img.image_url);
            if (primaryImage) {
              updateData.image_url = primaryImage.image_url;
              updateData.image_path = primaryImage.file_path;
            } else if (imagesPayload.length === 0 || imagesPayload.every(img => img.remove)) {
              updateData.image_url = null;
              updateData.image_path = null;
            }
          } else if (!hadImagesBefore && imagesPayload.length === 0) {
            delete updateData.images;
          }

          if (Object.keys(updateData).length > 0) {
            console.log(`📤 Updating post ${post.id} with data:`, updateData);
            const updateResponse = await updatePost(post.id, updateData);
            console.log(`📥 Update response for post ${post.id}:`, updateResponse);

            if (updateResponse && updateResponse.success) {
              successCount++;
              if (updateResponse.post) {
                console.log(`✅ Post ${post.id} updated successfully:`, {
                  scheduled_at: updateResponse.post.scheduled_at,
                  image_url: updateResponse.post.image_url,
                  image_path: updateResponse.post.image_path,
                  status: updateResponse.post.status,
                });
              }
            } else {
              console.error(`❌ Update failed for post ${post.id}:`, updateResponse);
              errorCount++;
            }
          } else {
            console.log(`ℹ️ No changes detected for post ${post.id}`);
          }
        } catch (error) {
          console.error(`Error updating post ${post.id}:`, error);
          errorCount++;
        }
      }

      if (successCount > 0) {
        toast.success(`Successfully updated ${successCount} post(s)`);
        try {
          await loadCampaignsFromDB();
          await new Promise(resolve => setTimeout(resolve, 300));
        } catch (reloadError) {
          console.error('Error reloading campaigns:', reloadError);
          toast.warning('Updates saved but failed to refresh. Please refresh the page.');
        }
        setEditModalOpen(false);
        setEditingCampaign(null);
        setEditingPosts([]);
      } else if (errorCount > 0) {
        toast.error(`Failed to update ${errorCount} post(s)`);
      } else {
        toast.info('No changes to save');
      }
    } catch (error) {
      console.error('Error saving campaign:', error);
      toast.error('Failed to save campaign updates');
    } finally {
      setIsSaving(false);
    }
  };

  const updateEditImages = (postId, updater) => {
    setEditingPosts(prev => prev.map(post => {
      if (post.id !== postId) return post;
      const nextImages = updater(post.editImages || [], post) || [];
      return { ...post, editImages: nextImages };
    }));
  };

  const handleAddImagesFromFiles = async (postId, fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    const targetPost = editingPosts.find((p) => p.id === postId);

    for (const file of files) {
      if (!file.type || !file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        continue;
      }

      if (file.size > 10 * 1024 * 1024) {
        toast.error('Image size must be less than 10MB');
        continue;
      }

      try {
        const dataUrl = await readFileAsDataUrl(file);
        const response = await uploadCustomImage({
          data_url: dataUrl,
          description: editingCampaign?.name || targetPost?.campaignName || targetPost?.editCaption || file.name || 'Uploaded image',
        });

        if (!response?.success || !(response.image_url || response.image_path || response.url)) {
          console.error('Upload response missing image URL', response);
          toast.error('Failed to upload image');
          continue;
        }

        const newEntry = createEditingImageEntry({
          id: null,
          image_url: response.image_url || response.url || response.image_path,
          file_path: response.image_path || response.image_url,
          previewUrl: response.image_url
            ? apiUrl(response.image_url)
            : (response.image_path ? apiUrl(response.image_path) : ''),
          generation_method: "user_upload",
        }, { isNew: true });

        updateEditImages(postId, (images) => [...images, newEntry]);
        toast.success('Image uploaded');
      } catch (error) {
        console.error('Failed to upload image:', error);
        toast.error('Failed to upload image');
      }
    }
  };

  const handleAddImageFromUrl = (postId) => {
    const input = window.prompt("Enter image URL or /public path:");
    if (!input) return;

    const relativePath = ensureRelativePublicPath(input);
    if (!relativePath) {
      toast.error("Please provide a valid /public/... path.");
      return;
    }

    const imageUrl = `/${relativePath}`;
    const newEntry = createEditingImageEntry({
      id: null,
      image_url: imageUrl,
      file_path: relativePath,
      previewUrl: apiUrl(imageUrl),
      generation_method: "user_upload",
    }, { isNew: true });

    updateEditImages(postId, (images) => [...images, newEntry]);
    toast.success("Image added");
  };

  const handleDeleteNewImage = (postId, localId) => {
    updateEditImages(postId, (images) => images.filter((img) => img.localId !== localId));
  };

  const handleToggleRemoveImage = (postId, localId) => {
    updateEditImages(postId, (images) => images.reduce((acc, img) => {
      if (img.localId !== localId) {
        acc.push(img);
        return acc;
      }
      if (!img.id) {
        return acc;
      }
      acc.push({ ...img, remove: !img.remove });
      return acc;
    }, []));
  };

  const handleMakePrimaryImage = (postId, localId) => {
    updateEditImages(postId, (images) => {
      const index = images.findIndex((img) => img.localId === localId);
      if (index <= 0) return images;
      const updated = [...images];
      const [selected] = updated.splice(index, 1);
      updated.unshift({ ...selected, remove: false });
      return updated;
    });
  };

  const updatePostField = (postId, field, value) => {
    setEditingPosts(prev => prev.map(post => 
      post.id === postId ? { ...post, [field]: value } : post
    ));
  };

  const togglePlatform = (postId, platform) => {
    setEditingPosts(prev => prev.map(post => {
      if (post.id === postId) {
        const currentPlatforms = post.editPlatforms || [];
        const newPlatforms = currentPlatforms.includes(platform)
          ? currentPlatforms.filter(p => p !== platform)
          : [...currentPlatforms, platform];
        return { ...post, editPlatforms: newPlatforms };
      }
      return post;
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">My Campaigns</h1>
          <p className="text-sm text-gray-500">Manage and track your social media campaigns</p>
        </div>
        <Link to="/create" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700">New Campaign</Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[{label:'Total Campaigns', value:stats.total}, {label:'Active', value:stats.active}, {label:'Scheduled', value:stats.scheduled}, {label:'Drafts', value:stats.drafts}].map((s,i)=> (
          <div key={i} className="rounded-2xl border border-gray-200 bg-white p-6">
            <div className="text-sm text-gray-500 mb-2">{s.label}</div>
            <div className="text-3xl font-semibold text-gray-900">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-6 py-3 font-medium">Campaign Name</th>
                <th className="text-left px-6 py-3 font-medium">Status</th>
                <th className="text-left px-6 py-3 font-medium">Platforms</th>
                <th className="text-left px-6 py-3 font-medium">Posts</th>
                <th className="text-left px-6 py-3 font-medium">Reach</th>
                <th className="text-left px-6 py-3 font-medium">Engagement</th>
                <th className="text-left px-6 py-3 font-medium">Scheduled</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map(row => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{row.name}</div>
                    <div className="text-xs text-gray-500">Created {new Date(row.createdAt).toISOString().slice(0,10)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${row.status==='Active' ? 'bg-green-50 text-green-700' : (row.status==='Scheduled' ? 'bg-blue-50 text-blue-700' : 'bg-gray-100 text-gray-700')}`}>{row.status}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      {row.platforms && row.platforms.length > 0 ? (
                        <>
                          {row.platforms.slice(0,4).map(p => {
                            // Map platform names to icon files
                            const iconMap = {
                              'twitter': 'x',
                              'facebook': 'facebook',
                              'instagram': 'instagram',
                              'reddit': 'reddit',
                              'linkedin': 'linkedin'
                            };
                            const iconName = iconMap[p.toLowerCase()] || p;
                            const iconPath = `/icons/${iconName}.png`;
                            const platformName = p === 'twitter' ? 'X (Twitter)' : p.charAt(0).toUpperCase() + p.slice(1);
                            
                            return (
                              <img 
                                key={p} 
                                src={iconPath} 
                                alt={p} 
                                className="w-5 h-5 object-contain"
                                title={platformName}
                                onError={(e) => {
                                  // Fallback: show platform name as text badge if icon fails to load
                                  e.target.style.display = 'none';
                                  if (!e.target.nextSibling || (e.target.nextSibling.tagName !== 'SPAN' && !e.target.nextSibling.classList?.contains('platform-fallback'))) {
                                    const fallback = document.createElement('span');
                                    fallback.className = 'platform-fallback px-1.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 rounded capitalize';
                                    fallback.textContent = p === 'twitter' ? 'X' : p;
                                    fallback.title = platformName;
                                    e.target.parentNode.insertBefore(fallback, e.target.nextSibling);
                                  }
                                }}
                              />
                            );
                          })}
                          {row.platforms.length > 4 && (
                            <span className="text-xs text-gray-500 font-medium" title={row.platforms.slice(4).join(', ')}>
                              +{row.platforms.length - 4}
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="text-xs text-gray-400 italic">No platforms</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">{row.posts}</td>
                  <td className="px-6 py-4">{row.reach}</td>
                  <td className="px-6 py-4">{row.engagement}</td>
                  <td className="px-6 py-4">{row.scheduledAt ? new Date(row.scheduledAt).toISOString().slice(0,10) : '-'}</td>
                  <td className="px-6 py-4 text-right relative">
                    <button 
                      ref={el => buttonRefs.current[row.id] = el}
                      className="p-2 rounded hover:bg-gray-100 relative" 
                      title="More"
                      onClick={(e) => {
                        const button = e.currentTarget;
                        const rect = button.getBoundingClientRect();
                        const menuWidth = 192; // w-48 = 12rem = 192px
                        const left = rect.right + window.scrollX - menuWidth;
                        // Ensure menu doesn't go off-screen on the left
                        const adjustedLeft = Math.max(8, left);
                        setMenuPosition({
                          top: rect.bottom + window.scrollY + 4,
                          left: adjustedLeft
                        });
                        setOpenMenuId(openMenuId === row.id ? null : row.id);
                      }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Portal for dropdown menu overlay */}
      {openMenuId && rows.find(r => r.id === openMenuId) && createPortal(
        <div 
          ref={menuRef}
          className="fixed w-48 bg-white rounded-md shadow-lg z-[9999] border border-gray-200"
          style={{
            top: `${menuPosition.top}px`,
            left: `${menuPosition.left}px`
          }}
        >
          <div className="py-1">
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const row = rows.find(r => r.id === openMenuId);
                if (row) {
                  handleView(row);
                  setOpenMenuId(null);
                }
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View
            </button>
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const row = rows.find(r => r.id === openMenuId);
                if (row) {
                  handleUpdate(row);
                  setOpenMenuId(null);
                }
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Update
            </button>
            <button
              onClick={() => {
                const row = rows.find(r => r.id === openMenuId);
                if (row) {
                  handleCalendar(row);
                  setOpenMenuId(null);
                }
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Calendar
            </button>
            <button
              onClick={() => {
                const row = rows.find(r => r.id === openMenuId);
                if (row) {
                  handleDelete(row);
                  setOpenMenuId(null);
                }
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          </div>
        </div>,
        document.body
      )}

      {/* Edit Campaign Modal */}
      {editModalOpen && editingCampaign && createPortal(
        <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4" style={{ backgroundColor: 'transparent' }}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Edit Campaign</h2>
                <p className="text-sm text-gray-500 mt-1">{editingCampaign.name}</p>
              </div>
              <button
                onClick={() => {
                  setEditModalOpen(false);
                  setEditingCampaign(null);
                  setEditingPosts([]);
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <div className="space-y-6">
                {editingPosts.map((post, index) => (
                  <div key={post.id} className="border border-gray-200 rounded-lg p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-gray-900">Post {index + 1}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        post.status === 'Posted' ? 'bg-green-100 text-green-700' :
                        post.status === 'Scheduled' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {post.status}
                      </span>
                    </div>

                    {/* Caption */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Caption
                      </label>
                      <textarea
                        value={post.editCaption || ''}
                        onChange={(e) => updatePostField(post.id, 'editCaption', e.target.value)}
                        placeholder="Enter post caption..."
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
                      />
                      <div className="text-xs text-gray-500 mt-1">
                        {post.editCaption?.length || 0} characters
                      </div>
                    </div>

                    {/* Scheduled Date & Time */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Scheduled Date & Time
                      </label>
                      <input
                        type="datetime-local"
                        value={post.editScheduledAt || ''}
                        onChange={(e) => updatePostField(post.id, 'editScheduledAt', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
                      />
                    </div>

                    {/* Platforms */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Platforms
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {['facebook', 'instagram', 'twitter', 'linkedin', 'reddit'].map(platform => (
                          <label
                            key={platform}
                            className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-colors ${
                              post.editPlatforms?.includes(platform)
                                ? 'bg-purple-100 text-purple-700 border-2 border-purple-500'
                                : 'bg-gray-100 text-gray-700 border-2 border-transparent hover:bg-gray-200'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={post.editPlatforms?.includes(platform) || false}
                              onChange={() => togglePlatform(post.id, platform)}
                              className="sr-only"
                            />
                            <span className="capitalize">{platform === 'twitter' ? 'X' : platform}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Image Editor */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Images
                      </label>
                      <div className="space-y-4">
                        <div className="flex flex-wrap gap-4">
                          {post.editImages && post.editImages.length > 0 ? (
                            post.editImages.map((image) => {
                              const previewUrl = image.previewUrl || (image.image_url ? apiUrl(image.image_url) : "");
                              const markedForRemoval = !!image.remove;
                              return (
                                <div key={image.localId} className="relative w-40">
                                  <div className={`relative border rounded-lg overflow-hidden ${markedForRemoval ? 'opacity-60 border-red-400' : 'border-gray-200'}`}>
                                    {previewUrl ? (
                                      <img
                                        src={previewUrl}
                                        alt="Campaign"
                                        className="w-full h-32 object-cover"
                                        onError={(e) => {
                                          e.target.src = "";
                                          e.target.alt = "Preview unavailable";
                                        }}
                                      />
                                    ) : (
                                      <div className="flex items-center justify-center h-32 bg-gray-100 text-gray-500 text-xs">
                                        No preview
                                      </div>
                                    )}
                                    {markedForRemoval && (
                                      <div className="absolute inset-0 bg-red-500/40 flex items-center justify-center">
                                        <span className="text-white text-xs font-semibold">Marked for removal</span>
                                      </div>
                                    )}
                                  </div>
                                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                                    {image.id ? (
                                      <button
                                        type="button"
                                        onClick={() => handleToggleRemoveImage(post.id, image.localId)}
                                        className={`px-2 py-1 rounded-md border ${markedForRemoval ? 'border-gray-300 text-gray-600 hover:border-gray-400' : 'border-red-200 text-red-600 hover:border-red-300 hover:text-red-700'}`}
                                      >
                                        {markedForRemoval ? 'Undo remove' : 'Remove'}
                                      </button>
                                    ) : (
                                      <button
                                        type="button"
                                        onClick={() => handleDeleteNewImage(post.id, image.localId)}
                                        className="px-2 py-1 rounded-md border border-red-200 text-red-600 hover:border-red-300 hover:text-red-700"
                                      >
                                        Delete
                                      </button>
                                    )}
                                    {!markedForRemoval && (
                                      <button
                                        type="button"
                                        onClick={() => handleMakePrimaryImage(post.id, image.localId)}
                                        className="px-2 py-1 rounded-md border border-gray-200 text-gray-600 hover:border-gray-300 hover:text-gray-700"
                                      >
                                        Make primary
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })
                          ) : (
                            <p className="text-sm text-gray-500">No images yet. Add one below.</p>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <label className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-200 text-sm font-medium text-gray-700 bg-white hover:border-purple-300 hover:text-purple-700 cursor-pointer">
                            <input
                              type="file"
                              accept="image/*"
                              multiple
                              className="hidden"
                              onChange={(e) => {
                                const files = e.target.files;
                                if (files?.length) {
                                  handleAddImagesFromFiles(post.id, files);
                                  e.target.value = "";
                                }
                              }}
                            />
                            <span>Upload images</span>
                          </label>
                          <button
                            type="button"
                            onClick={() => handleAddImageFromUrl(post.id)}
                            className="inline-flex items-center px-3 py-2 rounded-md border border-gray-200 text-sm font-medium text-gray-700 bg-white hover:border-purple-300 hover:text-purple-700"
                          >
                            Add via URL
                          </button>
                        </div>

                        <p className="text-xs text-gray-500">
                          Supported formats: JPG, PNG, GIF. Max size per image: 10MB.
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setEditModalOpen(false);
                  setEditingCampaign(null);
                  setEditingPosts([]);
                }}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveCampaign}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSaving && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* View Campaign Modal */}
      {viewModalOpen && viewingCampaign && createPortal(
        <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4" style={{ backgroundColor: 'transparent' }}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">View Campaign</h2>
                <p className="text-sm text-gray-500 mt-1">{viewingCampaign.name}</p>
              </div>
              <button
                onClick={() => {
                  setViewModalOpen(false);
                  setViewingCampaign(null);
                  setViewingPosts([]);
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <div className="space-y-6">
                {viewingPosts.map((post, index) => (
                  <div key={post.id} className="border border-gray-200 rounded-lg p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-gray-900">Post {index + 1}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        post.status === 'Posted' ? 'bg-green-100 text-green-700' :
                        post.status === 'Scheduled' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {post.status}
                      </span>
                    </div>

                    {/* Caption */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Caption
                      </label>
                      <div className="w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-sm text-gray-700 min-h-[60px]">
                        {post.caption || post.generatedContent || 'No caption'}
                      </div>
                    </div>

                    {/* Scheduled Date & Time */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Scheduled Date & Time
                      </label>
                      <div className="w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-sm text-gray-700">
                        {post.scheduledAt 
                          ? new Date(post.scheduledAt).toLocaleString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })
                          : 'Not scheduled'}
                      </div>
                    </div>

                    {/* Platforms */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Platforms
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {(post.platforms || []).length > 0 ? (
                          post.platforms.map(platform => (
                            <span
                              key={platform}
                              className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 border-2 border-purple-500"
                            >
                              <span className="capitalize">{platform === 'twitter' ? 'X' : platform}</span>
                            </span>
                          ))
                        ) : (
                          <span className="text-sm text-gray-500">No platforms selected</span>
                        )}
                      </div>
                    </div>

                    {/* Images */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Images
                      </label>
                      <div className="flex flex-wrap gap-4">
                        {post.images && post.images.length > 0 ? (
                          post.images.map((image) => {
                            const imgUrl = image.image_url ? apiUrl(image.image_url) : (image.url ? apiUrl(image.url) : "");
                            return (
                              <div key={image.id || image.file_path} className="w-40">
                                {imgUrl ? (
                                  <img
                                    src={imgUrl}
                                    alt="Campaign"
                                    className="w-full h-32 object-cover rounded-md border border-gray-200"
                                    onError={(e) => {
                                      e.target.src = "";
                                      e.target.alt = "Image unavailable";
                                    }}
                                  />
                                ) : (
                                  <div className="flex items-center justify-center h-32 bg-gray-100 text-gray-500 text-xs rounded-md">
                                    No image
                                  </div>
                                )}
                                {image.generation_method && (
                                  <div className="mt-1 text-[10px] uppercase tracking-wide text-gray-400">
                                    {image.generation_method}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        ) : (
                          (post.imageUrl || post.image_path) ? (
                            <img
                              src={post.imageUrl || post.image_path}
                              alt="Post preview"
                              className="w-full max-w-xs h-auto rounded-md border border-gray-200"
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          ) : (
                            <p className="text-sm text-gray-500">No images</p>
                          )
                        )}
                      </div>
                    </div>

                    {/* Additional Info */}
                    <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-100">
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Created</label>
                        <div className="text-sm text-gray-700">
                          {post.createdAt 
                            ? new Date(post.createdAt).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric'
                              })
                            : 'N/A'}
                        </div>
                      </div>
                      {post.postedAt && (
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">Posted</label>
                          <div className="text-sm text-gray-700">
                            {new Date(post.postedAt).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric'
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end">
              <button
                onClick={() => {
                  setViewModalOpen(false);
                  setViewingCampaign(null);
                  setViewingPosts([]);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
              >
                Close
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}

export default MyCampaigns;
