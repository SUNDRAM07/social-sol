import { useMemo, useState, useEffect } from "react";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import Badge from "../components/ui/Badge.jsx";
import { Link, useNavigate } from "react-router-dom";
import apiClient from "../lib/apiClient.js";
import { useCampaignStore } from "../store/campaignStore.js";
import { useAuthStore } from "../store/authStore.js";
import InstagramPostsPopup from "../components/InstagramPostsPopup.jsx";
import TrendingTopicPopup from "../components/TrendingTopicPopup.jsx";

// Stat component for the top stats row
function Stat({ label, value, color = "text-blue-600" }) {
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm">
      <div className="text-sm text-gray-500 font-medium mb-2">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}

// Activity card component for the Recent Activity section
function ActivityCard({ icon, title, subtitle, time }) {
  return (
    <div className="flex items-start gap-3 p-4 border-b border-gray-100">
      <div className="bg-purple-100 p-2 rounded-md">
        {icon}
      </div>
      <div className="flex-1">
        <div className="font-medium text-sm">{title}</div>
        <div className="text-xs text-gray-500">{subtitle}</div>
      </div>
      <div className="text-xs text-gray-400">{time}</div>
    </div>
  );
}

// Metric card component for Total Reach and Engagement
function MetricCard({ title, value, change, color = "bg-purple-600" }) {
  return (
    <div className={`${color} text-white p-6 rounded-lg`}>
      <div className="text-sm font-medium mb-2">{title}</div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-sm">{change}</div>
    </div>
  );
}

// Summary card component for Posts Scheduled and AI Ideas
function SummaryCard({ title, value, subtitle }) {
  return (
    <div className="bg-white p-4 rounded-lg shadow-sm">
      <div className="text-lg font-bold mb-1">{value}</div>
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-xs text-gray-400 mt-1">{subtitle}</div>
    </div>
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  // Get campaigns from store
  const campaigns = useCampaignStore((state) => state.campaigns);
  const recentActivity = useCampaignStore((state) => state.recentActivity);

  const [heroData, setHeroData] = useState(null);
  const [analyticsOverview, setAnalyticsOverview] = useState(null);
  const [analyticsPosts, setAnalyticsPosts] = useState([]);
  const [followers, setFollowers] = useState(null);
  const [scheduledPosts, setScheduledPosts] = useState([]);
  const [allPosts, setAllPosts] = useState([]);
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [showInstagramPopup, setShowInstagramPopup] = useState(false);
  const [trendingPopup, setTrendingPopup] = useState({ open: false, topic: null, category: null });

  function getWeekDates(fromDate) {
    const d = new Date(fromDate);
    const week = [];
    for (let i = 0; i < 7; i++) {
      const copy = new Date(d);
      copy.setDate(d.getDate() + i);
      week.push(copy);
    }
    return week;
  }

  // Derive counts per day from scheduled posts in the next 7 days
  const weekDates = getWeekDates(new Date());
  // Prioritize scheduled posts over calendar events since they're more current
  const scheduledSource = useMemo(() => {
    return (scheduledPosts && scheduledPosts.length > 0)
      ? scheduledPosts
      : (calendarEvents && calendarEvents.length > 0)
        ? calendarEvents
        : (allPosts || []).filter((p) => (p.status || '').toLowerCase() === 'scheduled');
  }, [scheduledPosts, calendarEvents, allPosts]);

  const weekCounts = useMemo(() => {
    const counts = new Array(7).fill(0);
    const start = new Date();
    start.setHours(0, 0, 0, 0); // Start of today
    const end = new Date();
    end.setDate(start.getDate() + 7);
    end.setHours(23, 59, 59, 999); // End of 7th day

    for (const item of scheduledSource) {
      const when = new Date(
        item.scheduled_at ||
        item.scheduled_time ||
        item.scheduledAt ||
        item.start_time ||
        item.start ||
        item.date || 0
      );

      if (!isNaN(when.getTime()) && when >= start && when < end) {
        const diffDays = Math.floor((when - start) / (1000 * 60 * 60 * 24));
        if (diffDays >= 0 && diffDays < 7) {
          counts[diffDays] += 1;
        }
      }
    }
    return counts;
  }, [scheduledSource]);

  const stats = useMemo(() => {
    // Prefer backend posts; fallback to store campaigns
    const posts = Array.isArray(allPosts) && allPosts.length > 0 ? allPosts : [];
    const hasPosts = posts.length > 0;

    // Total campaigns: unique campaign_name or batch id
    const ids = new Set();
    if (hasPosts) {
      posts.forEach(p => {
        const key = (p.campaign_name && p.campaign_name.trim()) || p.batch_id || `post_${p.id}`;
        ids.add(key);
      });
    } else {
      campaigns.forEach(c => ids.add(c.batchId || c.campaignName || `single_${c.id}`));
    }
    const totalCampaigns = ids.size;

    // Week window
    const start = new Date();
    const dow = (start.getDay() + 6) % 7; // Mon=0
    start.setHours(0,0,0,0);
    start.setDate(start.getDate() - dow);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    end.setHours(23,59,59,999);

    // Posts this week
    let postsThisWeek = weekCounts.reduce((a,b)=>a+b,0);
    if (postsThisWeek === 0 && hasPosts) {
      postsThisWeek = posts.filter(p => {
        const when = new Date(p.created_at || p.scheduled_at || p.start_time || 0);
        return !isNaN(when) && when >= start && when <= end;
      }).length;
    }

    // Active posts: scheduled or recently posted/published this week
    let activePosts = 0;
    if (hasPosts) {
      activePosts = posts.filter(p => {
        const s = (p.status || '').toLowerCase();
        const when = new Date(p.scheduled_at || p.created_at || 0);
        const activeStatus = s === 'scheduled' || s === 'posted' || s === 'published' || s === 'active';
        return activeStatus || (!isNaN(when) && when >= start && when <= end);
      }).length;
    } else {
      activePosts = campaigns.filter(c => {
        const s = (c.status || '').toLowerCase();
        return s === 'scheduled' || s === 'posted' || s === 'published';
      }).length;
    }

    const totalPosts = hasPosts ? posts.length : campaigns.length;
    const avgEngagement = (analyticsOverview && analyticsOverview.avgEngagement) ? analyticsOverview.avgEngagement : 4.6;
    return { total: totalCampaigns, scheduledThisWeek: postsThisWeek, active: activePosts, avgEngagement, totalPosts };
  }, [campaigns, allPosts, weekCounts, analyticsOverview]);

  // Load analytics and hero data from backend (stale-safe: never overwrite with empty)
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        // Load campaigns from the store first
        const { loadCampaignsFromDB } = useCampaignStore.getState();
        await loadCampaignsFromDB();

        // Skip dashboard statistics remote call; compute locally from posts/campaigns

        // Skip hero and analytics calls since they don't exist
        // const [heroRes, analyticsRes] = await Promise.all([
        //   apiClient.getHero(),
        //   apiClient.getAnalyticsOverview(),
        // ]);

        if (!mounted) return;

        // Skip hero and analytics data setting since we're not calling those APIs
        // if (heroRes && heroRes.success && heroRes.data) {
        //   setHeroData(prev => heroRes.data || prev);
        // }
        // if (analyticsRes && analyticsRes.success && analyticsRes.data) {
        //   setAnalyticsOverview(prev => analyticsRes.data || prev);
        // }

        // Skip analytics posts and followers calls since they might not exist
        // try {
        //   const postsRes = await apiClient.getAnalyticsPosts({ limit: 12 });
        //   if (postsRes && postsRes.success && Array.isArray(postsRes.posts)) {
        //     setAnalyticsPosts(prev => (postsRes.posts.length ? postsRes.posts : prev));
        //   }
        // } catch (e) {
        //   console.warn('Failed to load analytics posts', e);
        // }

        // try {
        //   const followersRes = await apiClient.getFollowers();
        //   if (followersRes && followersRes.success) {
        //     const f = followersRes.followers ?? followersRes.followers_count;
        //     if (typeof f === 'number') setFollowers(prev => f ?? prev);
        //   }
        // } catch (e) {
        //   console.warn('Failed to load followers', e);
        // }

        try {
          const calRes = await apiClient.getCalendarEvents();
          console.log('📅 Calendar events response:', calRes);
          if (calRes && calRes.success && Array.isArray(calRes.events)) {
            const normalized = calRes.events.map((ev, idx) => ({
              id: String(ev.id ?? idx),
              title: ev.title || 'Post Event',
              description: ev.description || '',
              start_time: ev.start_time || ev.start || null,
              end_time: ev.end_time || ev.end || null,
              scheduled_at: ev.start_time || ev.start || null,
              platforms: Array.isArray(ev.platforms) ? ev.platforms : (
                Array.isArray(ev.metadata?.platforms) ? ev.metadata.platforms : (
                  ev.platform ? [ev.platform] : ['Instagram']
                )
              ),
              platform: ev.platform || "",
              post_id: ev.post_id || null,
            }));
            console.log('📅 Normalized calendar events:', normalized);
            setCalendarEvents(prev => (normalized.length ? normalized : prev));
          }
        } catch (e) {
          console.warn('Failed to load calendar events', e);
        }

        try {
          console.log('🚀 Making API call to getScheduledPosts...');
          const schedRes = await apiClient.getScheduledPosts();
          console.log('📅 Scheduled posts response:', schedRes);
          if (schedRes && schedRes.success && Array.isArray(schedRes.scheduled_posts)) {
            const normalized = schedRes.scheduled_posts.map((sp, idx) => ({
              id: String(sp.id ?? sp.post_id ?? sp.event_id ?? idx),
              original_description: sp.original_description || sp.caption || sp.title || sp.message || "",
              caption: sp.caption || "",
              campaign_name: sp.campaign_name || "",
              platforms: sp.platforms || [],
              platform: sp.platform || "",
              scheduled_at: sp.scheduled_at || sp.scheduled_time || sp.start_time || sp.date || null,
              status: (sp.status || "scheduled").toLowerCase(),
              start_time: sp.start_time || null,
            }));
            console.log('📅 Normalized scheduled posts:', normalized);
            console.log('📅 Setting scheduled posts state...');
            setScheduledPosts(prev => {
              console.log('📅 Previous scheduled posts:', prev);
              const newValue = normalized.length ? normalized : prev;
              console.log('📅 New scheduled posts value:', newValue);
              return newValue;
            });
          } else {
            console.log('📅 No scheduled posts found or invalid response');
          }
        } catch (e) {
          console.error('❌ Failed to load scheduled posts', e);
        }

        try {
          const allRes = await apiClient.getAllPosts({ limit: 100 });
          console.log('📅 All posts response:', allRes);
          if (allRes && allRes.success && Array.isArray(allRes.posts)) {
            const normalized = allRes.posts.map((p) => ({
              id: String(p.id),
              original_description: p.original_description || p.caption || p.title || p.message || "",
              caption: p.caption || "",
              campaign_name: p.campaign_name || "",
              platforms: p.platforms || [],
              platform: p.platform || "",
              created_at: p.created_at || p.createdAt || null,
              scheduled_at: p.scheduled_at || p.scheduled_time || p.start_time || p.scheduledAt || null,
              status: (p.status || "").toLowerCase(),
              batch_id: p.batch_id || null,
            }));
            console.log('📅 Normalized all posts:', normalized);
            setAllPosts(prev => (normalized.length ? normalized : prev));
          }
        } catch (e) {
          console.warn('Failed to load all posts', e);
        }

        // Skip scheduler status call since it might not exist
        // try {
        //   const schedStatus = await apiClient.getSchedulerStatus();
        //   if (schedStatus && schedStatus.success && typeof schedStatus.status !== 'undefined') {
        //     setSchedulerStatus(prev => schedStatus.status ?? prev);
        //   }
        // } catch (e) {
        //   console.warn('Failed to load scheduler status', e);
        // }

      } catch (e) {
        console.error("Failed to load analytics/hero:", e);
      }
    };

    load();
    return () => { mounted = false; };
  }, []);

  // Removed state store dependency: rely solely on backend data in this page

  // derive effective stats from analyticsOverview or computed stats
  const effectiveStats = analyticsOverview ? {
    total: analyticsOverview.total || stats.total,
    scheduledThisWeek: analyticsOverview.scheduledThisWeek || stats.scheduledThisWeek,
    active: analyticsOverview.active || stats.active,
    avgEngagement: analyticsOverview.avgEngagement || stats.avgEngagement,
    totalPosts: analyticsOverview.totalPosts || stats.totalPosts
  } : stats;

  const recent = useMemo(() => {
    // Use campaign store activity first, then campaigns, then backend data
    if (recentActivity && recentActivity.length > 0) {
      return recentActivity.slice(0, 3);
    }

    if (campaigns && campaigns.length > 0) {
      return campaigns
        .slice()
        .sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
        .slice(0, 3)
        .map(c => ({
          text: c.campaignName || c.productDescription || `Campaign created`,
          time: c.createdAt || Date.now()
        }));
    }

    if (allPosts && allPosts.length > 0) {
      return allPosts
        .slice()
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
        .slice(0, 3)
        .map(p => ({
          text: p.campaign_name || p.original_description || `Campaign ${p.id}`,
          time: new Date(p.created_at || Date.now()).getTime()
        }));
    }

    // Default sample data based on Figma design
    return [
      {
        text: "Posted to Instagram",
        subtitle: "Summer Product Launch campaign",
        time: new Date(Date.now() - 2 * 60 * 60 * 1000).getTime(),
        icon: "📱"
      },
      {
        text: "Analytics updated",
        subtitle: "Engagement increased by 24%",
        time: new Date(Date.now() - 5 * 60 * 60 * 1000).getTime(),
        icon: "📊"
      },
      {
        text: "AI generated 6 new ideas",
        subtitle: "For your Holiday Sale campaign",
        time: new Date(Date.now() - 24 * 60 * 60 * 1000).getTime(),
        icon: "💡"
      }
    ];
  }, [recentActivity, campaigns, allPosts]);

  // Weekly trending topics based on Figma design
  const trendingTopics = [
    { name: "AI Technology", color: "bg-blue-100 text-blue-600" },
    { name: "Social Media", color: "bg-purple-100 text-purple-600" },
    { name: "Marketing", color: "bg-pink-100 text-pink-600" },
    { name: "Automation", color: "bg-green-100 text-green-600" }
  ];

  return (
    <div className="max-w-full relative">
      {/* Animated background decoration */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-purple-400/20 to-pink-400/20 rounded-full blur-3xl -z-10 animate-float"></div>
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-blue-400/20 to-indigo-400/20 rounded-full blur-3xl -z-10 animate-float" style={{ animationDelay: '2s' }}></div>
      
      {/* 30-Day Free Trial Banner */}
      <div className="bg-gradient-to-r from-purple-600 via-indigo-600 to-pink-600 text-white px-4 sm:px-6 py-4 mx-4 sm:mx-6 mb-6 rounded-xl shadow-colored-lg backdrop-blur-sm border border-white/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-600/50 to-pink-600/50 opacity-50 animate-pulse"></div>
        <div className="relative z-10 flex items-center gap-3 flex-1">
          <div className="flex items-center gap-3 flex-1">
            <div className="bg-white/20 p-2 rounded-lg flex-shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 sm:h-6 sm:w-6" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-base sm:text-lg">30 Day Free Trial</h3>
              <p className="text-xs sm:text-sm text-white/90">Enjoy full access to all features. Contact us to continue after your trial.</p>
            </div>
          </div>
          <Button
            variant="outline"
            className="bg-white/10 border-white/30 text-white hover:bg-white/20 px-4 sm:px-6 py-2 rounded-md font-semibold w-full sm:w-auto"
            onClick={() => navigate('/help-support')}
          >
            Contact Us
          </Button>
        </div>
      </div>

      {/* Instagram Posts Popup */}
      {showInstagramPopup && (
        <InstagramPostsPopup 
          isOpen={showInstagramPopup} 
          onClose={() => setShowInstagramPopup(false)} 
        />
      )}

      {trendingPopup.open && (
        <TrendingTopicPopup
          isOpen={trendingPopup.open}
          topic={trendingPopup.topic}
          category={trendingPopup.category}
          onClose={() => setTrendingPopup({ open: false, topic: null, category: null })}
        />
      )}
      
      {/* Hero Section */}
      <div className="relative bg-gradient-to-br from-purple-50 via-indigo-50 to-pink-50 p-6 mb-8 mx-6 rounded-2xl border border-purple-100/50 shadow-lg overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-400/5 via-transparent to-pink-400/5"></div>
        <div className="relative z-10 flex flex-col lg:flex-row items-start gap-12 max-w-7xl mx-auto">
          <div className="flex-1 pt-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-purple-600 text-sm font-semibold">✨ AI-Powered Social Media Manager</span>
            </div>
            <h1 className="text-3xl font-bold text-purple-700 mb-3">Automate Your Social Media Success</h1>
            <p className="text-gray-700 mb-4 font-medium text-lg">Your manager that never sleeps</p>
            <p className="text-gray-600 mb-8">Build, grow, and scale your business with a team of AI helpers — schedule posts, reply to comments, and automate work while you sleep.</p>
            
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-2">
                <span className="text-purple-600">●</span>
                <span className="text-gray-700">Schedule unlimited posts across all platforms</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-purple-600">●</span>
                <span className="text-gray-700">AI-powered content generation in 28+ languages</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-purple-600">●</span>
                <span className="text-gray-700">Real-time analytics and performance tracking</span>
              </li>
            </ul>
            
            <div className="flex gap-4">
              <Button 
                variant="primary" 
                className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-md font-medium"
                onClick={() => navigate('/help-support')}
              >
                Get Started Free
              </Button>
              <Button variant="outline" className="border border-gray-300 hover:bg-gray-50 px-6 py-2.5 rounded-md font-medium">Watch Demo</Button>
            </div>
          </div>
          
          <div className="flex-1">
            <div className="relative rounded-2xl overflow-hidden shadow-2xl border border-purple-100 w-full bg-purple-50 h-[320px] md:h-[360px] lg:h-[400px]">
              
                <img
                  src="https://images.unsplash.com/photo-1582005450386-52b25f82d9bb?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzb2NpYWwlMjBtZWRpYSUyMG1hcmtldGluZyUyMHRlYW18ZW58MXx8fHwxNzYxNjY3NjI2fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                  alt="Social Media Management Platform"
                  className="absolute inset-0 w-full h-full object-cover"
                />
                
              <div className="absolute inset-0 bg-gradient-to-tr from-purple-900/20 to-pink-900/20"></div>

              {/* Top-left platform connection badges */}
              <div className="absolute top-6 left-6 flex gap-3">
                <div className="flex items-center gap-2 bg-white/95 backdrop-blur-sm rounded-xl shadow-xl px-4 py-2 border border-purple-100">
                  <img src="/socialanywhere/icons/facebook.png" alt="Facebook" className="w-5 h-5" />
                  <span className="text-xs text-gray-700">Facebook</span>
                </div>
                <div className="flex items-center gap-2 bg-white/95 backdrop-blur-sm rounded-xl shadow-xl px-4 py-2 border border-purple-100">
                  <img src="/socialanywhere/icons/instagram.png" alt="Instagram" className="w-5 h-5" />
                  <span className="text-xs text-gray-700">Instagram</span>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

      {/* Welcome back section */}
      <div className="px-6 mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">Welcome back, {user?.name || 'kuruba ram'}</h2>
          <p className="text-gray-600 mt-1">Here is what is happening with your campaigns today.</p>
        </div>
        <Link to="/create">
          <Button variant="primary" className="bg-purple-600 text-white px-4 py-2 rounded-md">
            New Campaign
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-colored mx-6 p-6 mb-8 border border-purple-100/50 card-modern">
        <div className="grid grid-cols-3 gap-6">
          <div className="relative">
            <div className="absolute -top-2 -right-2 w-16 h-16 bg-purple-200/30 rounded-full blur-xl"></div>
            <div className="text-gray-600 mb-1 text-sm font-medium">Total campaigns</div>
            <div className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">{effectiveStats.total}</div>
          </div>
          <div className="relative">
            <div className="absolute -top-2 -right-2 w-16 h-16 bg-blue-200/30 rounded-full blur-xl"></div>
            <div className="text-gray-600 mb-1 text-sm font-medium">Posts this week</div>
            <div className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">{effectiveStats.scheduledThisWeek}</div>
          </div>
          <div className="relative">
            <div className="absolute -top-2 -right-2 w-16 h-16 bg-green-200/30 rounded-full blur-xl"></div>
            <div className="text-gray-600 mb-1 text-sm font-medium">Active</div>
            <div className="text-4xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">{effectiveStats.active}</div>
          </div>
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mx-6 mb-8">
        {/* Recent Activity */}
        <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-colored overflow-hidden border border-purple-100/50 card-modern">
          <div className="p-4 border-b border-gray-100 bg-gradient-to-r from-purple-50 to-transparent">
            <h2 className="font-semibold text-lg bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">Recent Activity</h2>
          </div>
          <div>
            <div 
              className="flex items-start gap-3 p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50"
              onClick={() => setShowInstagramPopup(true)}
            >
              <div className="bg-purple-100 p-2 rounded-md">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-purple-600" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Posted to Instagram</div>
                <div className="text-xs text-gray-500">Summer Product Launch campaign</div>
              </div>
              <div className="text-xs text-gray-400">2 hours ago</div>
            </div>
            
            <div className="flex items-start gap-3 p-4 border-b border-gray-100">
              <div className="bg-blue-100 p-2 rounded-md">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M3 3a1 1 0 000 2h10a1 1 0 100-2H3zm0 4a1 1 0 000 2h6a1 1 0 100-2H3zm0 4a1 1 0 100 2h8a1 1 0 100-2H3z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Analytics updated</div>
                <div className="text-xs text-gray-500">Engagement increased by 24%</div>
              </div>
              <div className="text-xs text-gray-400">5 hours ago</div>
            </div>
            
            <div className="flex items-start gap-3 p-4">
              <div className="bg-yellow-100 p-2 rounded-md">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-yellow-600" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
                </svg>
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">AI generated 6 new ideas</div>
                <div className="text-xs text-gray-500">For your Holiday Sale campaign</div>
              </div>
              <div className="text-xs text-gray-400">Yesterday</div>
            </div>
          </div>
        </div>
        
        {/* Weekly Trending Topics */}
        <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-colored overflow-hidden border border-purple-100/50 card-modern">
          <div className="p-4 border-b border-gray-100 bg-gradient-to-r from-indigo-50 to-transparent flex justify-between items-center">
            <h2 className="font-semibold text-lg bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">Weekly Trending Topics</h2>
            <button className="text-gray-400 hover:text-gray-600">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
          
          <div className="p-4">
            <div className="flex flex-wrap gap-2 mb-6">
              {trendingTopics.map((topic, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => setTrendingPopup({ open: true, topic: topic.name, category: topic.name })}
                  className={`${topic.color} px-3 py-1 rounded-full text-xs font-medium hover:opacity-80 transition`}
                >
                  {topic.name}
                </button>
              ))}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <MetricCard
                title="Total Reach"
                value="0"
                change="0% this week"
                color="bg-gradient-to-br from-pink-500 to-purple-600"
              />

              <MetricCard
                title="Engagement"
                value="0"
                change="0% this week"
                color="bg-gradient-to-br from-purple-500 to-indigo-600"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main content grid - second row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mx-6 mb-8">
        {/* Left column */}
        <div>
          {/* AI Copywriter */}
          <Link to="/create" className="block">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-colored p-4 mb-6 flex justify-between items-center hover:shadow-colored-lg transition-all duration-200 border border-purple-100/50 card-modern group">
              <div>
                <h2 className="font-semibold mb-1 bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent group-hover:from-purple-700 group-hover:to-indigo-700 transition-all">AI Copywriter</h2>
                <p className="text-sm text-gray-600">Captions, ads & blogs in 28+ languages.</p>
              </div>
              <div className="bg-gradient-to-br from-purple-600 to-indigo-600 p-2 rounded-lg shadow-colored group-hover:scale-110 transition-transform">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </div>
            </div>
          </Link>

          {/* Idea Generator */}
          <Link to="/idea-generator" className="block">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-colored p-4 mb-6 flex justify-between items-center hover:shadow-colored-lg transition-all duration-200 border border-blue-100/50 card-modern group">
              <div>
                <h2 className="font-semibold mb-1 bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent group-hover:from-blue-700 group-hover:to-cyan-700 transition-all">Idea Generator</h2>
                <p className="text-sm text-gray-600">Generate creative content ideas with AI assistance.</p>
              </div>
              <div className="bg-gradient-to-br from-blue-600 to-cyan-600 p-2 rounded-lg shadow-colored group-hover:scale-110 transition-transform">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
                </svg>
              </div>
            </div>
          </Link>
        </div>

        {/* Right column */}
        <div>
          {/* Quick Actions */}
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-colored p-4 border border-indigo-100/50 card-modern">
            <h2 className="font-semibold mb-4 text-lg bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">Quick Actions</h2>
            <div className="space-y-3">
              <Link to="/analytics" className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors">
                <div className="bg-blue-100 p-2 rounded-md">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                  </svg>
                </div>
                <span className="text-gray-700">View Analytics</span>
              </Link>
              
              <Link to="/campaigns" className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors">
                <div className="bg-yellow-100 p-2 rounded-md">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-yellow-600" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z" />
                  </svg>
                </div>
                <span className="text-gray-700">Manage Campaigns</span>
              </Link>
              
              <Link to="/settings" className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors">
                <div className="bg-gray-100 p-2 rounded-md">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                  </svg>
                </div>
                <span className="text-gray-700">Connect Platforms</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* End of Dashboard */}

      {/* Features removed per request */}


    </div>
  );
}

export default Dashboard;
