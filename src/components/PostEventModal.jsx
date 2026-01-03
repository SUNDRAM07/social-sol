import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import Modal from "./ui/Modal.jsx";
import Button from "./ui/Button.jsx";
import Input from "./ui/Input.jsx";
import { toast } from "sonner";
import moment from "moment";
import { apiFetch, apiUrl } from "../lib/api.js";
import apiClient from "../lib/apiClient.js";

const PostEventModal = ({
  isOpen,
  onClose,
  event,
  onEventUpdate,
  onEventDelete
}) => {
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    scheduled_time: "",
    scheduled_date: "",
    scheduled_time_only: "",
    image_url: ""
  });
  const [isLoading, setIsLoading] = useState(false);
  const [postData, setPostData] = useState(null);
  const [showImageEditModal, setShowImageEditModal] = useState(false);
  const [imageEditMode, setImageEditMode] = useState(null); // 'ai' or 'upload'
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [imageProvider, setImageProvider] = useState("stability");

  // Load event data when modal opens
  useEffect(() => {
    if (isOpen && event) {
      const scheduledMoment = event.start_time ? moment(event.start_time) : null;
      setFormData({
        title: event.title || "",
        description: event.description || "",
        scheduled_time: scheduledMoment ? scheduledMoment.format("YYYY-MM-DDTHH:mm") : "",
        scheduled_date: scheduledMoment ? scheduledMoment.format("YYYY-MM-DD") : "",
        scheduled_time_only: scheduledMoment ? scheduledMoment.format("HH:mm") : "",
        image_url: event.metadata?.image_url || ""
      });

      // Fetch post data if this event has a post_id
      if (event.post_id) {
        fetchPostData(event.post_id);
      }
    }
  }, [isOpen, event]);

  const fetchPostData = async (postId) => {
    try {
      // First try to fetch the specific post
      try {
        const postResp = await apiFetch(`/api/posts/${postId}`);
        const postDataResp = await postResp.json();
        if (postDataResp.success && postDataResp.post) {
          console.log('Post data from database:', postDataResp.post);
          setPostData(postDataResp.post);
          setFormData(prev => ({
            ...prev,
            // Prefer campaign_name (Basic mode campaign name); fallback to description snippet
            title: postDataResp.post.campaign_name && postDataResp.post.campaign_name.trim()
              ? postDataResp.post.campaign_name.trim()
              : `📱 ${postDataResp.post.original_description?.substring(0, 50)}...`,
            description: postDataResp.post.caption || postDataResp.post.original_description,
            image_url: postDataResp.post.image_path || postDataResp.post.image_url || ""
          }));
          return;
        }
      } catch (e) {
        console.warn('Failed to fetch single post, trying fallback:', e);
      }

      // Fallback: get all posts and find the one we want
      const data = await apiClient.getPosts({ limit: 100 });
      if (data && data.success && data.posts) {
        const p = data.posts.find(x => String(x.id) === String(postId));
        if (p) {
          console.log('Post data from fallback:', p);
          setPostData(p);
          setFormData(prev => ({
            ...prev,
            // Prefer campaign_name for Basic mode; fallback to description snippet
            title: p.campaign_name && p.campaign_name.trim()
              ? p.campaign_name.trim()
              : `📱 ${p.original_description?.substring(0, 50)}...`,
            description: p.caption || p.original_description,
            image_url: p.image_path || p.image_url || ""
          }));
        } else {
          console.warn(`Post with ID ${postId} not found in ${data.posts.length} posts`);
        }
      }
    } catch (error) {
      console.error("Failed to fetch post data:", error);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    if (!formData.title.trim()) {
      toast.error("Event title is required");
      return;
    }

    if (!formData.scheduled_time) {
      toast.error("Scheduled time is required");
      return;
    }

    setIsLoading(true);

    try {
      const scheduledDateTime = new Date(formData.scheduled_time).toISOString();

      // Update calendar event
      const eventUpdateData = {
        title: formData.title.trim(),
        description: formData.description,
        start_time: scheduledDateTime,
        end_time: scheduledDateTime, // Point-in-time event
        metadata: {
          ...event.metadata,
          image_url: formData.image_url
        }
      };

      // Update the calendar event
      if (onEventUpdate) {
        await onEventUpdate(event.id, eventUpdateData);
      }

      // If this event is linked to a post, also update the post in database
      if (event.post_id) {
        try {
          const postUpdateData = {
            caption: formData.description,
            scheduled_at: scheduledDateTime
          };

          // Add image updates if image was changed
          if (formData.image_url) {
            // Only update if it's a server URL, not a data URL
            if (!formData.image_url.startsWith('data:')) {
              // Extract just the filename from the URL
              let imagePath = formData.image_url;

              // Handle different URL formats
              if (imagePath.includes('http://localhost:8000/public/')) {
                // Full URL: http://localhost:8000/public/filename.png
                imagePath = imagePath.replace('http://localhost:8000/public/', '');
              } else if (imagePath.includes('/public/')) {
                // Partial URL: /public/filename.png
                imagePath = imagePath.split('/public/')[1];
              } else if (imagePath.startsWith('/')) {
                // Path: /filename.png -> remove leading slash
                imagePath = imagePath.substring(1);
              }

              // Ensure it starts with public/ if it doesn't already
              if (!imagePath.startsWith('public/')) {
                imagePath = `public/${imagePath}`;
              }

              postUpdateData.image_path = imagePath;
              postUpdateData.image_url = formData.image_url;
              console.log('Updating post with image:', { imagePath, imageUrl: formData.image_url });
            } else {
              console.log('Data URL detected, need to upload to server first');
              // If it's a data URL, we need to upload it to the server first
              try {
                const uploadResponse = await apiClient.uploadCustomImage({
                  data_url: formData.image_url,
                  description: formData.description || postData.original_description || 'Custom image'
                });

                if (uploadResponse && uploadResponse.success && uploadResponse.image_path) {
                  const newImageUrl = apiUrl(uploadResponse.image_path);
                  // Ensure imagePath is properly formatted (remove leading slash if present)
                  let imagePath = uploadResponse.image_path;
                  if (imagePath.startsWith('/')) {
                    imagePath = imagePath.substring(1);
                  }
                  postUpdateData.image_path = imagePath;
                  postUpdateData.image_url = newImageUrl;
                  console.log('Uploaded data URL to server:', { imagePath, imageUrl: newImageUrl });
                } else {
                  console.error('Failed to upload data URL to server');
                }
              } catch (error) {
                console.error('Error uploading data URL:', error);
              }
            }
          }

          const postUpdateResponse = await apiFetch(`/api/posts/${event.post_id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(postUpdateData)
          });

          if (!postUpdateResponse.ok) {
            console.error("Failed to update post in database");
            toast.warning("Event updated but failed to sync with database");
          } else {
            toast.success("Event and post updated successfully");
          }
        } catch (postError) {
          console.error("Error updating post:", postError);
          toast.warning("Event updated but failed to sync with database");
        }
      } else {
        toast.success("Event updated successfully");
      }

      onClose();
    } catch (error) {
      console.error("Error updating event:", error);
      toast.error(`Failed to update event: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this event?")) return;

    setIsLoading(true);

    try {
      if (onEventDelete) {
        await onEventDelete(event.id);
      }
      toast.success("Event deleted successfully");
      onClose();
    } catch (error) {
      console.error("Error deleting event:", error);
      toast.error(`Failed to delete event: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: "",
      description: "",
      scheduled_time: "",
      image_url: ""
    });
    setPostData(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  // Image editing functions
  const handleEditImage = () => {
    setShowImageEditModal(true);
  };

  const handleImageEditMode = (mode) => {
    setImageEditMode(mode);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadedFile(file);
    }
  };

  const generateAIImage = async () => {
    if (!postData) return;

    setIsGeneratingImage(true);
    try {
      const imageData = await apiClient.generateImageOnly({
        description: postData.caption || postData.original_description || formData.description,
        image_provider: imageProvider,
      });

      if (imageData.image_path) {
        const newImageUrl = apiUrl(imageData.image_path);
        console.log('AI Image generated - path:', imageData.image_path, 'URL:', newImageUrl);
        setFormData(prev => ({
          ...prev,
          image_url: newImageUrl
        }));
        toast.success("AI image generated successfully!");
        setShowImageEditModal(false);
      } else {
        console.error('No image_path in AI response:', imageData);
        toast.error("Failed to generate AI image");
      }
    } catch (error) {
      console.error("Error generating AI image:", error);
      toast.error("Failed to generate AI image");
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const uploadCustomImage = async () => {
    if (!uploadedFile || !postData) return;

    setIsUploadingImage(true);
    try {
      // Convert file to data URL
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          // First, display the data URL immediately (like advanced mode)
          const dataUrl = e.target.result;
          setFormData(prev => ({
            ...prev,
            image_url: dataUrl
          }));

          // Then upload to server in background
          const uploadResponse = await apiClient.uploadCustomImage({
            data_url: dataUrl,
            description: postData.caption || postData.original_description || formData.description
          });

          if (uploadResponse && uploadResponse.success && uploadResponse.image_path) {
            const newImageUrl = apiUrl(uploadResponse.image_path);
            console.log('Custom image uploaded - path:', uploadResponse.image_path, 'URL:', newImageUrl);

            // Always switch to server URL since upload was successful
            console.log('Server upload successful, switching to server URL');
            setFormData(prev => ({
              ...prev,
              image_url: newImageUrl
            }));

            toast.success("Custom image uploaded successfully!");
            setShowImageEditModal(false);
          } else {
            console.error('Upload failed - response:', uploadResponse);
            // Keep the data URL even if server upload fails
            toast.warning("Image displayed but server upload failed");
            setShowImageEditModal(false);
          }
        } catch (error) {
          console.error("Error uploading custom image:", error);
          // Keep the data URL even if upload fails
          toast.warning("Image displayed but server upload failed");
          setShowImageEditModal(false);
        } finally {
          setIsUploadingImage(false);
        }
      };
      reader.readAsDataURL(uploadedFile);
    } catch (error) {
      console.error("Error processing file:", error);
      toast.error("Failed to process image file");
      setIsUploadingImage(false);
    }
  };

  const resetImageEdit = () => {
    setImageEditMode(null);
    setUploadedFile(null);
    setShowImageEditModal(false);
  };

  if (!event) return null;

  const modalContent = (
    <>
      {/* Force modal to top layer with inline styles */}
      {isOpen && (
        <style>
          {`
            .event-modal-overlay {
              position: fixed !important;
              top: 0 !important;
              left: 0 !important;
              right: 0 !important;
              bottom: 0 !important;
              z-index: 999999 !important;
              display: flex !important;
              align-items: center !important;
              justify-content: center !important;
            }
          `}
        </style>
      )}
      <div className={`event-modal-overlay ${isOpen ? '' : 'hidden'}`}>
        <div className="absolute inset-0 bg-black/40" onClick={handleClose} />
        <div className="relative bg-white rounded-lg shadow-lg max-w-sm w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
          {/* Sticky Header with Close Button */}
          <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between z-10">
            <h3 className="text-lg font-semibold text-gray-900">Edit Post Event</h3>
            <button
              onClick={handleClose}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Generated Image Display */}
            {formData.image_url && (
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-gray-700">
                    {formData.image_url !== (postData?.image_path || postData?.image_url) ? 'New Image (Preview)' : 'Generated Image'}
                  </label>
                  <button
                    onClick={handleEditImage}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                    Edit Image
                  </button>
                </div>
                <div className="border rounded-lg overflow-hidden bg-gray-50 relative group">
                  <img
                    src={(() => {
                      if (formData.image_url.startsWith('data:')) {
                        return formData.image_url;
                      } else if (formData.image_url.startsWith('http')) {
                        return formData.image_url;
                      } else if (formData.image_url.startsWith('/')) {
                        return apiUrl(formData.image_url);
                      } else if (formData.image_url.startsWith('public/')) {
                        // Handle paths that already start with public/
                        return apiUrl(`/${formData.image_url}`);
                      } else if (formData.image_url) {
                        return apiUrl(`/public/${formData.image_url}`);
                      }
                      return '';
                    })()}
                    alt="Post preview"
                    className="w-full h-12 object-cover"
                    onError={(e) => {
                      console.log('Image failed to load:', formData.image_url);
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                    onLoad={(e) => {
                      console.log('Image loaded successfully:', formData.image_url);
                    }}
                  />
                  <div
                    className="w-full h-12 flex items-center justify-center text-gray-400 bg-gray-100"
                    style={{ display: 'none' }}
                  >
                    <div className="text-center">
                      <div className="text-xl mb-1">🖼️</div>
                      <div className="text-xs">Image not available</div>
                    </div>
                  </div>
                </div>
                {formData.image_url !== (postData?.image_path || postData?.image_url) && (
                  <div className="mt-2 text-xs text-green-600 flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 12l2 2 4-4" />
                      <circle cx="12" cy="12" r="10" />
                    </svg>
                    Image updated - will be saved when you click "Save Changes"
                  </div>
                )}
              </div>
            )}

            {/* Campaign Name - Display actual campaign name instead of "Default Campaign" */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Campaign Name
              </label>
              <div className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-sm text-gray-800">
                {postData?.campaign_name && postData.campaign_name.trim()
                  ? postData.campaign_name.trim()
                  : (formData.title || 'Untitled Campaign')}
              </div>
            </div>

            {/* Caption */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Caption
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange("description", e.target.value)}
                placeholder="Enter post caption..."
                rows={3}
                disabled={isLoading}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white resize-vertical text-xs"
              />
              <div className="text-xs text-gray-500 mt-1">
                {formData.description.length}/280 characters
              </div>
            </div>

            {/* Scheduled Date & Time */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Scheduled Date & Time
              </label>

              {/* Separate date and time inputs */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <input
                    type="date"
                    value={formData.scheduled_date}
                    onChange={(e) => {
                      const newDate = e.target.value;
                      handleInputChange("scheduled_date", newDate);
                      // Combine with time
                      if (newDate && formData.scheduled_time_only) {
                        const combined = `${newDate}T${formData.scheduled_time_only}`;
                        handleInputChange("scheduled_time", combined);
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white"
                    disabled={isLoading}
                    required
                    min={moment().format("YYYY-MM-DD")}
                    max={moment().add(1, 'year').format("YYYY-MM-DD")}
                  />
                </div>
                <div>
                  <input
                    type="time"
                    value={formData.scheduled_time_only}
                    onChange={(e) => {
                      const newTime = e.target.value;
                      handleInputChange("scheduled_time_only", newTime);
                      // Combine with date
                      if (formData.scheduled_date && newTime) {
                        const combined = `${formData.scheduled_date}T${newTime}`;
                        handleInputChange("scheduled_time", combined);
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white"
                    disabled={isLoading}
                    required
                  />
                </div>
                <div className="col-span-2 text-xs text-gray-500">
                  Select date and time separately
                </div>
              </div>
            </div>

            {/* Post Information Display */}
            {(postData || event) && (
              <div className="bg-gray-100 p-2 rounded-md">
                <h4 className="text-xs font-medium text-gray-800 mb-1">Post Information</h4>
                <div className="text-xs text-gray-600 space-y-0.5">
                  <div><strong>Platform:</strong> {
                    (() => {
                      // Try multiple platform field formats
                      let platformValue = null;

                      // Check postData first (from database)
                      if (postData) {
                        if (Array.isArray(postData.platforms) && postData.platforms.length > 0) {
                          platformValue = postData.platforms.join(', ');
                        } else if (postData.platform) {
                          platformValue = postData.platform;
                        }
                      }

                      // Check event data if postData doesn't have platform info
                      if (!platformValue && event) {
                        if (Array.isArray(event.platforms) && event.platforms.length > 0) {
                          platformValue = event.platforms.join(', ');
                        } else if (event.platform) {
                          platformValue = event.platform;
                        }
                      }

                      // Capitalize first letter if we found a platform
                      if (platformValue) {
                        return platformValue.split(', ').map(p =>
                          p.charAt(0).toUpperCase() + p.slice(1)
                        ).join(', ');
                      }

                      return 'Not specified';
                    })()
                  }</div>
                  <div><strong>Status:</strong> {postData?.status || event?.status || 'scheduled'}</div>
                  <div><strong>Created:</strong> {new Date(postData?.created_at || event?.created_at || Date.now()).toLocaleDateString()}</div>
                </div>
              </div>
            )}

          </div>

          {/* Sticky Footer with Action Buttons */}
          <div className="sticky bottom-0 bg-white border-t border-gray-200 p-4">
            <div className="flex justify-end space-x-2">
              <Button
                variant="secondary"
                onClick={handleClose}
                disabled={isLoading}
                className="text-sm px-3 py-1.5"
              >
                Cancel
              </Button>

              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={isLoading}
                className="text-sm px-3 py-1.5"
              >
                Delete
              </Button>

              <Button
                variant="primary"
                onClick={handleSave}
                disabled={isLoading}
                className="text-sm px-3 py-1.5"
              >
                {isLoading ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Image Edit Modal */}
      {showImageEditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[999999]">
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Edit Post Image</h3>
                <button
                  onClick={resetImageEdit}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>

              {!imageEditMode ? (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600 mb-4">Choose how you want to edit the image:</p>

                  <button
                    onClick={() => handleImageEditMode('ai')}
                    className="w-full p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="text-2xl">🤖</div>
                      <div>
                        <div className="font-medium text-gray-900">Create with AI</div>
                        <div className="text-sm text-gray-500">Generate new image using AI based on description</div>
                      </div>
                    </div>
                  </button>

                  <button
                    onClick={() => handleImageEditMode('upload')}
                    className="w-full p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="text-2xl">📁</div>
                      <div>
                        <div className="font-medium text-gray-900">Upload Your Own Image</div>
                        <div className="text-sm text-gray-500">Upload custom image from your device</div>
                      </div>
                    </div>
                  </button>
                </div>
              ) : imageEditMode === 'ai' ? (
                <div className="space-y-4">
                  <div className="flex items-center space-x-2 mb-4">
                    <div className="text-2xl">🤖</div>
                    <div>
                      <div className="font-medium text-gray-900">Generate AI Image</div>
                      <div className="text-sm text-gray-500">Create a new image using AI</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Image Provider
                      </label>
                      <select
                        value={imageProvider}
                        onChange={(e) => setImageProvider(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        disabled={isGeneratingImage}
                      >
                        <option value="stability">Stability AI</option>
                        <option value="chatgpt">ChatGPT</option>
                        <option value="nano_banana">Nano Banana</option>
                      </select>
                    </div>

                    <div className="flex space-x-2">
                      <Button
                        onClick={generateAIImage}
                        disabled={isGeneratingImage}
                        className="flex-1"
                      >
                        {isGeneratingImage ? "Generating..." : "Generate Image"}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => setImageEditMode(null)}
                        disabled={isGeneratingImage}
                      >
                        Back
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center space-x-2 mb-4">
                    <div className="text-2xl">📁</div>
                    <div>
                      <div className="font-medium text-gray-900">Upload Custom Image</div>
                      <div className="text-sm text-gray-500">Upload your own image file</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleFileUpload}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        disabled={isUploadingImage}
                      />
                      {uploadedFile && (
                        <p className="text-sm text-gray-600 mt-1">
                          Selected: {uploadedFile.name}
                        </p>
                      )}
                    </div>

                    <div className="flex space-x-2">
                      <Button
                        onClick={uploadCustomImage}
                        disabled={!uploadedFile || isUploadingImage}
                        className="flex-1"
                      >
                        {isUploadingImage ? "Uploading..." : "Upload Image"}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => setImageEditMode(null)}
                        disabled={isUploadingImage}
                      >
                        Back
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );

  // Use createPortal to render the modal at document body level, outside any other modal containers
  return typeof document !== 'undefined' && isOpen
    ? createPortal(modalContent, document.body)
    : null;
};

export default PostEventModal;
