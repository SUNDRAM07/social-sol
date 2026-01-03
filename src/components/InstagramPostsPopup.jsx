import React, { useState, useEffect, useMemo } from 'react';
import { apiFetch } from '../lib/api.js';
import apiClient from '../lib/apiClient.js';
import formatDistanceToNow from 'date-fns/formatDistanceToNow';
import format from 'date-fns/format';

function InstagramPostsPopup({ isOpen, onClose }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weekStartISO, setWeekStartISO] = useState(null);
  const [campaignCounts, setCampaignCounts] = useState([]);
  const [totalThisWeek, setTotalThisWeek] = useState(0);

  useEffect(() => {
    if (isOpen) {
      fetchWeeklyPosts();
    }
  }, [isOpen]);

  const fetchWeeklyPosts = async () => {
    try {
      setLoading(true);

      // 1) Fetch IG posts from Graph (optional, for thumbnails/time)
      let igPosts = [];
      try {
        const response = await apiFetch('/api/instagram/weekly-posts');
        const data = await response.json();
        if (data?.success) {
          igPosts = Array.isArray(data.posts) ? data.posts : [];
          setWeekStartISO(data.week_start || null);
        }
      } catch (_) {
        // Non-fatal
      }

      // 2) Fetch your app posts to derive campaign names and counts
      let total = 0;
      const byCampaign = new Map();
      try {
        const all = await apiClient.getAllPosts({ limit: 300 });
        if (all?.success && Array.isArray(all.posts)) {
          const start = startOfWeek();
          const end = endOfWeek(start);
          const filtered = all.posts.filter(p => {
            const platformOk = (p.platform || '').toLowerCase() === 'instagram' || (Array.isArray(p.platforms) && p.platforms.map(x => (x||'').toLowerCase()).includes('instagram'));
            if (!platformOk) return false;
            const when = new Date(p.created_at || p.scheduled_at || 0);
            return !isNaN(when) && when >= start && when <= end;
          });
          total = filtered.length;
          filtered.forEach(p => {
            const name = (p.campaign_name || 'Untitled campaign').trim() || 'Untitled campaign';
            byCampaign.set(name, (byCampaign.get(name) || 0) + 1);
          });
        }
      } catch (e) {
        console.warn('Failed to load app posts for weekly summary', e);
      }

      const list = Array.from(byCampaign.entries()).map(([campaign, count]) => ({ campaign, count })).sort((a,b)=>b.count-a.count);
      setCampaignCounts(list);
      setTotalThisWeek(total);

      // Keep ig posts list for detail section
      setPosts(igPosts);
    } catch (err) {
      setError('Error connecting to server');
      console.error('Error fetching Instagram weekly posts:', err);
    } finally {
      setLoading(false);
    }
  };

  function startOfWeek() {
    const t = new Date();
    const day = (t.getDay() + 6) % 7; // Mon=0
    t.setHours(0,0,0,0);
    t.setDate(t.getDate() - day);
    return t;
  }
  function endOfWeek(start){
    const e = new Date(start);
    e.setDate(start.getDate()+6);
    e.setHours(23,59,59,999);
    return e;
  }

  // Build a 7-day window with counts
  const weekSummary = useMemo(() => {
    // Determine start of week (Mon) from API or local calc
    const start = weekStartISO ? new Date(weekStartISO) : (() => {
      const t = new Date();
      const day = (t.getDay() + 6) % 7; // Mon=0 .. Sun=6
      t.setHours(0,0,0,0);
      t.setDate(t.getDate() - day);
      return t;
    })();

    const days = Array.from({ length: 7 }).map((_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });

    const counts = days.map(() => 0);
    const byDateKey = (ts) => format(new Date(ts), 'yyyy-MM-dd');
    const mapIndex = new Map(days.map((d, i) => [format(d, 'yyyy-MM-dd'), i]));

    for (const p of posts) {
      if (!p.timestamp) continue;
      const key = byDateKey(p.timestamp);
      const idx = mapIndex.get(key);
      if (idx !== undefined) counts[idx] += 1;
    }

    return {
      start,
      end: new Date(days[6]),
      days,
      counts,
      total: counts.reduce((a,b)=>a+b,0)
    };
  }, [posts, weekStartISO]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden border border-gray-200">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-sm font-medium text-gray-700">Instagram Posts This Week</h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="p-4 overflow-y-auto max-h-[calc(80vh-4rem)] space-y-4">
          {loading ? (
            <div className="flex justify-center items-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-700"></div>
            </div>
          ) : error ? (
            <div className="text-red-500 text-center py-4">{error}</div>
          ) : (
            <>
              {/* Week summary header */}
              <div className="bg-purple-50 border border-purple-100 rounded-lg p-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-sm text-purple-800">
                    Week {format(weekSummary.start, 'dd MMM')} - {format(weekSummary.end, 'dd MMM')}
                  </div>
                  <div className="text-sm font-semibold text-purple-700">
                    Total posts: {totalThisWeek || weekSummary.total}
                  </div>
                </div>
                {/* By campaign */}
                <div className="mt-3">
                  <div className="text-xs font-semibold text-gray-700 mb-2">By campaign</div>
                  {campaignCounts.length === 0 ? (
                    <div className="text-xs text-gray-500">No Instagram posts found for this week</div>
                  ) : (
                    <div className="space-y-1">
                      {campaignCounts.map((c) => (
                        <div key={c.campaign} className="flex items-center justify-between bg-white border border-purple-100 rounded-md px-3 py-1">
                          <div className="text-xs text-gray-700 truncate pr-2">{c.campaign}</div>
                          <div className="text-xs font-semibold text-purple-700">{c.count}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {/* Per day counts (from IG API if available) */}
                <div className="mt-3 grid grid-cols-7 gap-2">
                  {weekSummary.days.map((d, i) => (
                    <div key={i} className="bg-white rounded-md border border-purple-100 p-2 text-center">
                      <div className="text-[10px] text-gray-500 uppercase">{format(d, 'EEE')}</div>
                      <div className="text-xs text-gray-700">{format(d, 'dd')}</div>
                      <div className="mt-1 text-sm font-semibold text-purple-700">{weekSummary.counts[i]}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Posts list */}
              {posts.length === 0 ? (
                <div className="text-gray-500 text-center py-4">No Instagram posts found for this week</div>
              ) : (
                <div className="space-y-4">
                  {posts.map(post => (
                    <div key={post.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex items-start gap-3">
                        {post.media_url && (
                          <div className="w-16 h-16 rounded-md overflow-hidden flex-shrink-0">
                            <img 
                              src={post.media_url} 
                              alt="Post" 
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                e.target.onerror = null;
                                e.target.src = '/icons/instagram.png';
                              }}
                            />
                          </div>
                        )}
                        <div className="flex-1">
                          <div className="text-sm line-clamp-2 mb-1">
                            {post.caption || 'No caption'}
                          </div>
                          <div className="flex justify-between items-center text-xs text-gray-500">
                            <div>
                              {post.timestamp ? formatDistanceToNow(new Date(post.timestamp), { addSuffix: true }) : 'Unknown date'}
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                                </svg>
                                {post.like_count || 0}
                              </span>
                              <span className="flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M18 5v8a2 2 0 01-2 2h-5l-5 4v-4H4a2 2 0 01-2-2V5a2 2 0 012-2h12a2 2 0 012 2zM7 8H5v2h2V8zm2 0h2v2H9V8zm6 0h-2v2h2V8z" clipRule="evenodd" />
                                </svg>
                                {post.comments_count || 0}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default InstagramPostsPopup;
