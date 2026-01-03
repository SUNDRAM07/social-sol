import React, { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api.js';
import { useNavigate } from 'react-router-dom';

function TrendingTopicPopup({ isOpen, onClose, topic, category }) {
  const [loading, setLoading] = useState(false); // details loader
  const [error, setError] = useState(null);
  const [details, setDetails] = useState(null);
  const [topicList, setTopicList] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();

  // Map dashboard chip names -> backend categories
  const mapCategory = (name) => {
    const n = (name || '').toLowerCase();
    if (n.includes('ai') || n.includes('automation') || n.includes('tech')) return 'technology';
    if (n.includes('marketing') || n.includes('business')) return 'business';
    if (n.includes('social')) return 'news';
    return 'technology';
  };

  // Fetch topics for the category
  const loadTopics = async (catName) => {
    try {
      setTopicsLoading(true);
      const apiCat = mapCategory(catName || category || topic);
      const res = await apiFetch(`/api/trending/ai-topics?category=${encodeURIComponent(apiCat)}`);
      const data = await res.json();
      const list = data?.topics?.[apiCat] || Object.values(data?.topics || {})?.[0] || [];
      setTopicList(Array.isArray(list) ? list : []);
      // Auto-load first topic details if none selected
      if (Array.isArray(list) && list.length > 0) {
        fetchDetails(list[0], apiCat);
      }
    } catch (e) {
      console.error('Failed to load topics', e);
    } finally {
      setTopicsLoading(false);
    }
  };

  // Fetch details for a specific topic (or category overview if same)
  const fetchDetails = async (t = topic, cat = mapCategory(category || topic)) => {
    try {
      setLoading(true);
      setError(null);
      setDetails(null);
      const res = await apiFetch('/social-media/trending/topic-details', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: t, category: cat })
      });
      const data = await res.json();
      if (data.success) {
        const det = data.details || {};
        setDetails({
          overview: det.overview || '',
          key_points: det.keyPoints || det.key_points || [],
          related_topics: det.relatedTopics || det.related_topics || [],
        });
      } else {
        setError(data.error || 'Failed to fetch topic details');
      }
    } catch (e) {
      console.error('Failed to fetch topic details', e);
      setError('Error connecting to server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    loadTopics(category || topic);
    // Also fetch category overview
    fetchDetails(topic, mapCategory(category || topic));
  }, [isOpen, topic, category]);

  if (!isOpen) return null;

  const prefillCreate = () => {
    const overview = details?.overview || `${topic} insights`;
    const bullet = (details?.key_points || []).slice(0, 5).map((p) => `• ${p}`).join(' ');
    const description = `${overview}. ${bullet}`.trim();
    navigate('/create', {
      state: {
        prefilledDescription: description,
        fromTrending: true,
        trendingTopic: topic,
        trendingCategory: category
      }
    });
  };

  const refreshTopics = async () => {
    try {
      setRefreshing(true);
      await apiFetch('/api/trending/refresh', { method: 'POST' });
      await loadTopics(category || topic);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white w-full max-w-2xl max-h-[85vh] rounded-lg shadow-xl overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">{topic} — Topic Insights</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-4 overflow-y-auto max-h-[calc(85vh-4rem)] space-y-4">
          {/* Topics row */}
          <div className="flex items-center justify-between">
            <div className="flex flex-wrap gap-2">
              {topicsLoading ? (
                <span className="text-xs text-gray-500">Loading topics…</span>
              ) : topicList.length === 0 ? (
                <span className="text-xs text-gray-500">No topics available</span>
              ) : (
                topicList.map((t, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      const cat = mapCategory(category || topic);
                      navigate('/create', {
                        state: {
                          prefilledDescription: t,
                          fromTrending: true,
                          trendingTopic: t,
                          trendingCategory: cat
                        }
                      });
                      onClose();
                    }}
                    className="px-2 py-1 text-xs rounded-full border border-purple-200 text-purple-700 hover:bg-purple-50"
                  >
                    {t}
                  </button>
                ))
              )}
            </div>
            <button onClick={refreshTopics} disabled={refreshing} className="text-xs px-2 py-1 rounded-md border border-gray-300 hover:bg-gray-50 disabled:opacity-60">
              {refreshing ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center items-center py-10">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-700"></div>
            </div>
          ) : error ? (
            <div className="text-center text-red-600 py-6">{error}</div>
          ) : (
            <>
              <div className="bg-purple-50 border border-purple-100 rounded-md p-3 text-sm text-gray-800">
                {details?.overview || 'No overview available.'}
              </div>

              {details?.key_points?.length > 0 && (
                <div>
                  <div className="text-sm font-semibold text-gray-700 mb-2">Key points</div>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
                    {details.key_points.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}

              {details?.related_topics?.length > 0 && (
                <div>
                  <div className="text-sm font-semibold text-gray-700 mb-2">Related topics</div>
                  <div className="flex flex-wrap gap-2">
                    {details.related_topics.map((rt, i) => (
                      <span key={i} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full border border-gray-200">
                        {rt}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
        <div className="p-4 border-t border-gray-200 flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50">Close</button>
          <button onClick={prefillCreate} disabled={!details} className="px-4 py-2 text-sm rounded-md bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-60">Create campaign</button>
        </div>
      </div>
    </div>
  );
}

export default TrendingTopicPopup;
