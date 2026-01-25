import { useState, useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useCampaignStore } from "../store/campaignStore.js";
import { apiFetch } from "../lib/api.js";
import Card from "../components/ui/Card.jsx";
import { format } from "date-fns";

function Calendar() {
  const location = useLocation();
  const campaigns = useCampaignStore((s) => s.campaigns);
  const loadCampaignsFromDB = useCampaignStore((s) => s.loadCampaignsFromDB);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [viewMode, setViewMode] = useState("month"); // month, week, day
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  // Get campaign filter from location state
  const campaignFilter = location.state?.campaignId || null;
  const campaignName = location.state?.campaignName || null;

  useEffect(() => {
    loadCampaignsFromDB();
    loadCalendarEvents();
  }, [selectedDate, campaignFilter]);

  const loadCalendarEvents = async () => {
    try {
      setLoading(true);
      const startDate = new Date(selectedDate);
      startDate.setDate(1); // First day of month
      const endDate = new Date(selectedDate);
      endDate.setMonth(endDate.getMonth() + 1);
      endDate.setDate(0); // Last day of month

      const response = await apiFetch(
        `/api/calendar/events?start_date=${startDate.toISOString()}&end_date=${endDate.toISOString()}`
      );
      const data = await response.json();

      if (data.success && data.events) {
        let events = data.events;

        // Filter by campaign if specified
        if (campaignFilter) {
          const campaignPosts = campaigns.filter(c =>
            (c.campaignName && c.campaignName.trim() === campaignName) ||
            (c.batchId && c.batchId === campaignFilter)
          );
          const postIds = new Set(campaignPosts.map(p => p.id));
          events = events.filter(e => e.post_id && postIds.has(e.post_id));
        }

        setCalendarEvents(events);
      }
    } catch (error) {
      console.error("Error loading calendar events:", error);
    } finally {
      setLoading(false);
    }
  };

  // Get all posts (scheduled and existing) from campaigns
  const scheduledPosts = useMemo(() => {
    // Get all posts with scheduled_at, including both Scheduled and Posted status
    let posts = campaigns.filter(c => c.scheduledAt);

    // Filter by campaign if specified
    if (campaignFilter) {
      posts = posts.filter(c =>
        (c.campaignName && c.campaignName.trim() === campaignName) ||
        (c.batchId && c.batchId === campaignFilter)
      );
    }

    return posts.map(post => ({
      id: post.id,
      title: post.campaignName || post.productDescription || "Untitled Post",
      description: post.generatedContent || post.caption || "",
      start: new Date(post.scheduledAt),
      end: new Date(new Date(post.scheduledAt).getTime() + 30 * 60 * 1000), // 30 min duration
      platforms: post.platforms || [],
      imageUrl: post.imageUrl,
      status: post.status,
      campaignName: post.campaignName,
      createdAt: post.createdAt,
      updatedAt: post.updatedAt
    }));
  }, [campaigns, campaignFilter, campaignName]);

  // Group posts by date
  const postsByDate = useMemo(() => {
    const grouped = {};
    scheduledPosts.forEach(post => {
      const dateKey = format(post.start, "yyyy-MM-dd");
      if (!grouped[dateKey]) {
        grouped[dateKey] = [];
      }
      grouped[dateKey].push(post);
    });
    return grouped;
  }, [scheduledPosts]);

  // Get days in current month view
  const daysInMonth = useMemo(() => {
    const year = selectedDate.getFullYear();
    const month = selectedDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const days = [];
    
    // Add days from previous month to fill first week
    const startDay = firstDay.getDay();
    for (let i = startDay - 1; i >= 0; i--) {
      const date = new Date(year, month, -i);
      days.push(date);
    }
    
    // Add days of current month
    for (let day = 1; day <= lastDay.getDate(); day++) {
      days.push(new Date(year, month, day));
    }
    
    // Add days from next month to fill last week
    const remaining = 42 - days.length; // 6 weeks * 7 days
    for (let day = 1; day <= remaining; day++) {
      days.push(new Date(year, month + 1, day));
    }
    
    return days;
  }, [selectedDate]);

  const navigateMonth = (direction) => {
    const newDate = new Date(selectedDate);
    newDate.setMonth(newDate.getMonth() + direction);
    setSelectedDate(newDate);
  };

  const navigateToday = () => {
    setSelectedDate(new Date());
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-[var(--text)]">Calendar</h1>
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <span className="ml-4 text-[var(--text-muted)]">Loading calendar...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text)]">Calendar</h1>
          {campaignName && (
            <p className="text-sm text-[var(--text-muted)]">Showing posts for: {campaignName}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigateMonth(-1)}
            className="px-3 py-2 border border-[var(--border)] rounded bg-[var(--surface)] text-[var(--text)] hover:bg-[var(--bg-muted)] transition-colors"
          >
            ← Prev
          </button>
          <button
            onClick={navigateToday}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          >
            Today
          </button>
          <button
            onClick={() => navigateMonth(1)}
            className="px-3 py-2 border border-[var(--border)] rounded bg-[var(--surface)] text-[var(--text)] hover:bg-[var(--bg-muted)] transition-colors"
          >
            Next →
          </button>
        </div>
      </div>

      <Card>
        <div className="p-6">
          <div className="mb-4 text-xl font-semibold text-center text-[var(--text)]">
            {format(selectedDate, "MMMM yyyy")}
          </div>
          
          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-1">
            {/* Day headers */}
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
              <div key={day} className="p-2 text-center text-sm font-semibold text-[var(--text-muted)]">
                {day}
              </div>
            ))}
            
            {/* Calendar days */}
            {daysInMonth.map((date, idx) => {
              const dateKey = format(date, "yyyy-MM-dd");
              const isCurrentMonth = date.getMonth() === selectedDate.getMonth();
              const isToday = format(date, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd");
              const dayPosts = postsByDate[dateKey] || [];
              
              return (
                <div
                  key={idx}
                  className={`min-h-[100px] border border-[var(--border)] p-2 ${
                    !isCurrentMonth ? "bg-[var(--bg-muted)] text-[var(--text-muted)] opacity-60" : "bg-[var(--surface)]"
                  } ${isToday ? "ring-2 ring-blue-500" : ""}`}
                >
                  <div className={`text-sm font-medium mb-1 ${isToday ? "text-blue-500" : "text-[var(--text)]"}`}>
                    {format(date, "d")}
                  </div>
                  <div className="space-y-1">
                    {dayPosts.slice(0, 3).map(post => (
                      <div
                        key={post.id}
                        className="text-xs p-1 bg-blue-500/10 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 rounded truncate cursor-pointer hover:bg-blue-500/20 dark:hover:bg-blue-500/30 transition-colors"
                        title={`${post.title} - ${format(post.start, "h:mm a")}`}
                      >
                        <div className="font-medium truncate">{post.title}</div>
                        <div className="text-blue-500">{format(post.start, "h:mm a")}</div>
                        <div className="flex items-center gap-1 mt-1">
                          {post.platforms?.slice(0, 3).map(platform => (
                            <img
                              key={platform}
                              src={`/icons/${platform === 'twitter' ? 'x' : platform}.png`}
                              alt={platform}
                              className="w-3 h-3"
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                    {dayPosts.length > 3 && (
                      <div className="text-xs text-[var(--text-muted)] text-center">
                        +{dayPosts.length - 3} more
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {/* All Posts List (Scheduled and Posted) */}
      <Card title={`All Posts (${scheduledPosts.length})`}>
        <div className="space-y-4">
          {scheduledPosts.length === 0 ? (
            <div className="text-center py-8 text-[var(--text-muted)]">
              No posts found
              {campaignFilter && ` for campaign "${campaignName}"`}
            </div>
          ) : (
            scheduledPosts
              .sort((a, b) => a.start - b.start)
              .map(post => {
                const isNew = post.createdAt && post.updatedAt && 
                  new Date(post.updatedAt) > new Date(post.createdAt) &&
                  (new Date(post.updatedAt).getTime() - new Date(post.createdAt).getTime()) < 60000; // Updated within 1 minute of creation
                const isPosted = post.status === "Posted";
                const isScheduled = post.status === "Scheduled";
                
                return (
                  <div
                    key={post.id}
                    className={`border rounded-lg p-4 hover:bg-[var(--bg-muted)] transition-colors ${
                      isPosted ? 'border-green-500/30 bg-green-500/10' : 
                      isScheduled ? 'border-blue-500/30 bg-blue-500/10' : 
                      'border-[var(--border)] bg-[var(--surface)]'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <h3 className="font-semibold text-[var(--text)]">{post.title}</h3>
                          <span className={`px-2 py-1 rounded text-xs ${
                            isPosted ? 'bg-green-500/20 text-green-600 dark:text-green-400' :
                            isScheduled ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400' :
                            'bg-[var(--bg-muted)] text-[var(--text-muted)]'
                          }`}>
                            {format(post.start, "MMM d, yyyy h:mm a")}
                          </span>
                          {isNew && (
                            <span className="px-2 py-1 bg-purple-500/20 text-purple-600 dark:text-purple-400 rounded text-xs">
                              New
                            </span>
                          )}
                          <span className={`px-2 py-1 rounded text-xs ${
                            isPosted ? 'bg-green-500/10 text-green-600 dark:text-green-400' :
                            isScheduled ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' :
                            'bg-[var(--bg-muted)] text-[var(--text-muted)]'
                          }`}>
                            {post.status}
                          </span>
                        </div>
                        {post.description && (
                          <p className="text-sm text-[var(--text-muted)] line-clamp-2 mb-2">
                            {post.description}
                          </p>
                        )}
                        <div className="flex items-center gap-2">
                          {post.platforms?.map(platform => (
                            <img
                              key={platform}
                              src={`/icons/${platform === 'twitter' ? 'x' : platform}.png`}
                              alt={platform}
                              className="w-5 h-5"
                            />
                          ))}
                        </div>
                      </div>
                      {post.imageUrl && (
                        <img
                          src={post.imageUrl}
                          alt={post.title}
                          className="w-20 h-20 object-cover rounded ml-4"
                        />
                      )}
                    </div>
                  </div>
                );
              })
          )}
        </div>
      </Card>
    </div>
  );
}

export default Calendar;


