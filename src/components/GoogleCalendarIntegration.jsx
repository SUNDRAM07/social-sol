import { useState, useEffect } from "react";
import Button from "./ui/Button.jsx";
import { toast } from "sonner";
import { apiFetch, apiUrl } from "../lib/api.js";
import apiClient from "../lib/apiClient.js";

const GoogleCalendarIntegration = ({ campaigns = [], onEventCreated, onOpenCalendarModal }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creatingEvents, setCreatingEvents] = useState(new Set());
  const [upcomingEvents, setUpcomingEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [recentPosts, setRecentPosts] = useState([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [showPosts, setShowPosts] = useState(false);

  // Check Google connection status on component mount and when window regains focus
  useEffect(() => {
    checkGoogleStatus();
    
    // Check if we just returned from Google OAuth (hash indicates success)
    if (window.location.hash === '#google-connected') {
      // Remove hash from URL
      window.history.replaceState(null, '', window.location.pathname);
      // Wait a moment for token.json to be written, then check status
      setTimeout(async () => {
        await checkGoogleStatus();
        toast.success("Successfully connected to Google Calendar!");
        // Load events immediately
        loadUpcomingEvents();
      }, 1000);
    }
    
    // Also check when window regains focus (in case user completed OAuth in another tab)
    const handleFocus = () => {
      checkGoogleStatus();
    };
    window.addEventListener('focus', handleFocus);
    
    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, []);
  
  // Auto-load events when connection status changes to connected
  useEffect(() => {
    if (isConnected && upcomingEvents.length === 0 && !loadingEvents) {
      loadUpcomingEvents();
    }
  }, [isConnected]);

  const checkGoogleStatus = async () => {
    try {
      const data = await apiClient.getGoogleStatus();
      setIsConnected(data && (data.connected || data.success));
    } catch (error) {
      console.error("Failed to check Google status:", error);
      setIsConnected(false);
    }
  };

  const loadUpcomingEvents = async () => {
    if (!isConnected) return;
    try {
      setLoadingEvents(true);
      const data = await apiClient.getGoogleUpcomingEvents();
      if (data && data.success && Array.isArray(data.events)) {
        setUpcomingEvents(data.events);
      } else {
        setUpcomingEvents([]);
      }
    } catch (error) {
      console.error("Failed to load upcoming Google events:", error);
      setUpcomingEvents([]);
    } finally {
      setLoadingEvents(false);
    }
  };

  const loadRecentPosts = async () => {
    try {
      setLoadingPosts(true);
      const data = await apiClient.getAllPosts({ limit: 50 });
      if (data && data.success && Array.isArray(data.posts)) {
        const normalized = data.posts.map((p) => ({
          id: String(p.id),
          campaignName: p.campaign_name || p.campaignName || "Untitled Campaign",
          description: p.original_description || p.caption || p.message || "",
          platformList: Array.isArray(p.platforms) && p.platforms.length
            ? p.platforms
            : (p.platform ? [p.platform] : []),
          scheduledAt: p.scheduled_at || p.scheduledAt || p.start_time || p.date || null,
          status: (p.status || "").toLowerCase(),
        }));
        setRecentPosts(normalized);
      } else {
        setRecentPosts([]);
      }
    } catch (error) {
      console.error("Failed to load recent posts:", error);
      setRecentPosts([]);
    } finally {
      setLoadingPosts(false);
    }
  };

  const connectToGoogle = async () => {
    try {
      setLoading(true);
      // Open Google OAuth in a new window
      const response = await apiFetch("/google/connect");
      if (!response.ok) {
        // Try to surface backend error message
        let message = `Google connect failed (${response.status})`;
        try {
          const text = await response.text();
          if (text) {
            const json = JSON.parse(text);
            message = json.detail || json.error || text;
          }
        } catch {
          // ignore parse error, keep default message
        }
        toast.error(message);
        return;
      }

      // Use the Settings page's connect function if available, otherwise redirect
      // Check if we're on Settings page and can use parent's connect function
      if (window.location.pathname.includes('/settings')) {
        // Redirect to Google OAuth - will come back to Settings page
        window.location.href = apiUrl("/google/connect");
      } else {
        // Open in same window
        window.location.href = apiUrl("/google/connect");
      }
    } catch (error) {
      console.error("Failed to connect to Google:", error);
      toast.error("Failed to connect to Google Calendar");
    } finally {
      setLoading(false);
    }
  };

  const createCalendarEvent = async (campaign) => {
    if (!isConnected) {
      toast.error("Please connect to Google Calendar first");
      return;
    }

    if (!campaign.scheduledAt) {
      toast.error("Campaign must be scheduled to create a calendar event");
      return;
    }

    setCreatingEvents(prev => new Set([...prev, campaign.id]));
    
    try {
      const campaignData = {
        id: campaign.id,
        productDescription: campaign.productDescription || campaign.description,
        generatedContent: campaign.generatedContent || campaign.caption,
        scheduledAt: campaign.scheduledAt,
        status: campaign.status,
        imageUrl: campaign.imageUrl,
        driveImageUrl: campaign.driveImageUrl, // Include Google Drive URL for calendar
        activity: campaign.activity || [
          { time: Date.now(), text: "Campaign created" }
        ]
      };

      const response = await apiFetch("/google-calendar/create-event", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(campaignData),
      });

      const data = await response.json();
      
      if (data.success) {
        toast.success(`Calendar event created! View: ${data.eventLink}`);
        if (onEventCreated) {
          onEventCreated(campaign.id, data);
        }
      } else {
        throw new Error(data.error || "Failed to create calendar event");
      }
    } catch (error) {
      console.error("Failed to create calendar event:", error);
      toast.error("Failed to create calendar event");
    } finally {
      setCreatingEvents(prev => {
        const newSet = new Set(prev);
        newSet.delete(campaign.id);
        return newSet;
      });
    }
  };

  const createAllCalendarEvents = async () => {
    if (!isConnected) {
      toast.error("Please connect to Google Calendar first");
      return;
    }

    const scheduledCampaigns = campaigns.filter(c => c.scheduledAt);
    if (scheduledCampaigns.length === 0) {
      toast.error("No scheduled campaigns to create calendar events for");
      return;
    }

    setLoading(true);
    let successCount = 0;
    
    for (const campaign of scheduledCampaigns) {
      try {
        await createCalendarEvent(campaign);
        successCount++;
      } catch (error) {
        console.error(`Failed to create event for campaign ${campaign.id}:`, error);
      }
    }
    
    setLoading(false);
    toast.success(`Created ${successCount} out of ${scheduledCampaigns.length} calendar events`);
  };

  const scheduledCampaigns = campaigns.filter(c => c.scheduledAt);
  const unscheduledCampaigns = campaigns.filter(c => !c.scheduledAt);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-900/60 rounded-lg border border-gray-200/60 dark:border-slate-700/60">
        <div className="flex items-center space-x-3">
          <div className="text-2xl">📅</div>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-slate-50">Google Calendar Integration</h3>
            <p className="text-sm text-gray-600 dark:text-slate-300">
              {isConnected 
                ? `Create calendar reminders for ${scheduledCampaigns.length} scheduled posts` 
                : "Connect to create calendar events for your scheduled posts"
              }
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className={`${isConnected ? 'bg-green-500' : 'bg-red-500'} w-2 h-2 rounded-full`} />
          <span className="text-sm text-gray-600 dark:text-slate-300">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {unscheduledCampaigns.length > 0 && (
        <div className="p-3 bg-yellow-50 dark:bg-amber-900/40 border border-yellow-200 dark:border-amber-700 rounded-lg">
          <div className="flex items-center space-x-2">
            <div className="text-yellow-600">⚠️</div>
            <p className="text-sm text-yellow-800">
              {unscheduledCampaigns.length} campaign(s) need to be scheduled before creating calendar events
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3 items-center">
        {!isConnected ? (
          <Button 
            onClick={connectToGoogle} 
            disabled={loading}
            variant="primary"
          >
            {loading ? "Connecting..." : "Connect Google Calendar"}
          </Button>
        ) : (
          <>
            <Button 
              onClick={createAllCalendarEvents} 
              disabled={loading || scheduledCampaigns.length === 0}
              variant="primary"
            >
              {loading ? "Creating Events..." : `Create All Events (${scheduledCampaigns.length})`}
            </Button>
          </>
        )}
      </div>

      {/* Individual campaign event creation */}
      {isConnected && scheduledCampaigns.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900 dark:text-slate-50">Individual Campaign Events</h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {scheduledCampaigns.map((campaign) => (
              <div key={campaign.id} className="flex items-center justify-between p-2 bg-white dark:bg-slate-900/60 border border-gray-200 dark:border-slate-700 rounded">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate text-gray-900 dark:text-slate-50">
                    {campaign.productDescription || campaign.description || campaign.id}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-slate-300">
                    📅 {new Date(campaign.scheduledAt).toLocaleString()}
                  </div>
                </div>
                <Button
                  size="sm"
                  onClick={() => createCalendarEvent(campaign)}
                  disabled={creatingEvents.has(campaign.id)}
                  variant="secondary"
                >
                  {creatingEvents.has(campaign.id) ? "Creating..." : "Create Event"}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unscheduled campaigns info */}
      {isConnected && unscheduledCampaigns.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900 dark:text-slate-50">Unscheduled Campaigns</h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {unscheduledCampaigns.map((campaign) => (
              <div key={campaign.id} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-slate-900/60 border border-gray-200 dark:border-slate-700 rounded">
                <div className="text-sm text-gray-600 dark:text-slate-300 truncate">
                  {campaign.productDescription || campaign.description || campaign.id}
                </div>
                <span className="text-xs text-gray-500 dark:text-slate-200 px-2 py-1 bg-gray-200 dark:bg-slate-700 rounded">
                  Not Scheduled
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent posts from /api/posts (last 50) - Only show if not using calendar modal */}
      {isConnected && showPosts && !onOpenCalendarModal && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900 dark:text-slate-50">
            Recent Social Posts (from app)
          </h4>
          <div className="space-y-1 max-h-60 overflow-y-auto border border-gray-200 dark:border-slate-700 rounded-lg bg-white/60 dark:bg-slate-900/60 p-3">
            {loadingPosts && (
              <div className="text-sm text-gray-600 dark:text-slate-300 px-2 py-2 text-center">
                ⏳ Loading posts from /api/posts...
              </div>
            )}
            {!loadingPosts && recentPosts.length === 0 && (
              <div className="text-sm text-gray-600 dark:text-slate-300 px-2 py-2 text-center">
                No posts found yet. Create a campaign to see it here.
              </div>
            )}
            {!loadingPosts && recentPosts.length > 0 && (
              <div className="space-y-2 text-xs">
                {recentPosts.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-start justify-between px-3 py-2 rounded-lg bg-gray-50 dark:bg-slate-800/80 border border-gray-200 dark:border-slate-700"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-gray-900 dark:text-slate-50 truncate">
                        {p.campaignName}
                      </div>
                      <div className="text-[11px] text-gray-600 dark:text-slate-300 mt-1">
                        {p.description || "No description"}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-2 items-center">
                        {p.platformList.map((pl) => (
                          <span
                            key={pl}
                            className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-200 text-[10px]"
                          >
                            {pl}
                          </span>
                        ))}
                        {p.scheduledAt && (
                          <span className="text-[10px] text-gray-500 dark:text-slate-300">
                            📅 {new Date(p.scheduledAt).toLocaleString()}
                          </span>
                        )}
                        {p.status && (
                          <span className="text-[10px] text-gray-500 dark:text-slate-400">
                            • {p.status}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default GoogleCalendarIntegration;
