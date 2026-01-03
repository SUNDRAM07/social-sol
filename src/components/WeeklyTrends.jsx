import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { RefreshCw } from 'lucide-react';
import Card from './ui/Card.jsx';
import Button from './ui/Button.jsx';
import Badge from './ui/Badge.jsx';
import { apiFetch } from '../lib/api.js';
import TrendingTopicPopup from './TrendingTopicPopup';

const WeeklyTrends = () => {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState('all');
  const [topics, setTopics] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [showPopup, setShowPopup] = useState(false);
  const [showCategoryPopup, setShowCategoryPopup] = useState(false);

  const categories = {
    all: 'All',
    technology: 'Technology',
    business: 'Business',
    lifestyle: 'Lifestyle', 
    entertainment: 'Entertainment',
    news: 'News'
  };

  // Load trending topics from backend
  const loadTrendingTopics = async (category = 'all', forceRefresh = false) => {
    try {
      setLoading(true);
      setError(null);

      const endpoint = forceRefresh 
        ? '/api/trending/refresh'
        : `/api/trending/ai-topics${category && category !== 'all' ? `?category=${category}` : ''}`;
      
      const method = forceRefresh ? 'POST' : 'GET';
      const response = await apiFetch(endpoint, { method });
      const data = await response.json();

      if (data.success) {
        setTopics(data.topics || {});
        if (data.error_state) {
          toast.error('Unable to fetch trending topics from AI service');
        }
      } else {
        // Handle API error response
        setTopics(data.topics || {});
        toast.error(data.error || 'Failed to load trending topics');
      }
    } catch (err) {
      console.error('Error loading trending topics:', err);
      setError(err.message);
      toast.error('Failed to load trending topics');
      
      // Set error topics instead of fallback
      setTopics({
        technology: ['Unable to fetch trending topics'],
        business: ['Unable to fetch trending topics'],
        lifestyle: ['Unable to fetch trending topics'],
        entertainment: ['Unable to fetch trending topics'],
        news: ['Unable to fetch trending topics']
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadTrendingTopics(activeCategory);
  }, [activeCategory]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadTrendingTopics(activeCategory, true);
  };

  const handleTopicClick = (topic, category) => {
    // Don't navigate if it's an error message
    if (topic === 'Unable to fetch trending topics') {
      return;
    }
    
    // Show popup with topic details
    setSelectedTopic(topic);
    setSelectedCategory(category);
    setShowPopup(true);
  };

  const handleCategoryClick = (category) => {
    // Set active category as before
    setActiveCategory(category);
    
    // Also show popup with category details
    if (category !== 'all') {
      setSelectedCategory(category);
      setShowCategoryPopup(true);
    }
  };

  const getFilteredTopics = () => {
    if (activeCategory === 'all') {
      return topics;
    }
    return { [activeCategory]: topics[activeCategory] || [] };
  };

  const getCategoryColor = (category) => {
    const colors = {
      technology: 'blue',
      business: 'green', 
      lifestyle: 'purple',
      entertainment: 'pink',
      news: 'orange'
    };
    return colors[category] || 'gray';
  };

  const cardTitle = (
    <div className="flex items-center justify-between w-full">
      <span className="font-medium text-sm">Weekly Trending Topics</span>
      <button
        onClick={handleRefresh}
        disabled={refreshing}
        className="p-1 rounded-lg hover:bg-[var(--bg-muted)] transition-colors disabled:opacity-50"
        title="Refresh topics"
      >
        <RefreshCw className={`w-4 h-4 text-[var(--text-muted)] ${refreshing ? 'animate-spin' : ''}`} />
      </button>
    </div>
  );

  return (
    <Card title={cardTitle} className="h-[500px]">
      <div className="flex flex-col" style={{height: 'calc(500px - 80px)'}}>{/* Account for card padding, title, and margins */}

        {/* Category tabs */}
        <div className="flex flex-wrap gap-2 mb-3">
          {Object.entries(categories).map(([key, label]) => (
            <button
              key={key}
              onClick={() => handleCategoryClick(key)}
              title={key !== 'all' ? `View ${label} trends` : undefined}
              aria-pressed={activeCategory === key}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                activeCategory === key
                  ? 'bg-[var(--primary)] text-white'
                  : 'bg-[var(--bg-muted)] text-muted-contrast hover:bg-[var(--border)]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Topics list - properly constrained */}
        <div className="flex-1 min-h-0">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-[var(--primary)] border-t-transparent"></div>
            </div>
          )}
          
          {error && (
            <div className="text-center py-4 text-muted-contrast">
              <p className="text-sm">Failed to load trends</p>
              <Button 
                onClick={() => loadTrendingTopics(activeCategory)}
                variant="secondary"
                size="sm"
                className="mt-2"
              >
                Try Again
              </Button>
            </div>
          )}
          
          {!loading && !error && (
            <div className="h-full overflow-y-auto space-y-2 trending-scroll" style={{scrollbarWidth: 'thin', scrollbarColor: 'var(--border) transparent'}}>
              {Object.entries(getFilteredTopics()).map(([category, categoryTopics]) =>
                categoryTopics?.map((topic, index) => {
                  const isErrorTopic = topic === 'Unable to fetch trending topics';
                  return (
                    <div key={`${category}-${index}`} className="group">
                      <div
                        className={`w-full text-left px-3 py-2 rounded-lg border border-[var(--border)] 
                                  transition-all duration-200 ${
                                    isErrorTopic 
                                      ? 'cursor-default opacity-60 bg-[var(--bg-muted)]'
                                      : 'cursor-pointer hover:border-[var(--primary)] hover:bg-[var(--bg-muted)] group-hover:shadow-sm'
                                  }`}
                        onClick={() => !isErrorTopic && handleTopicClick(topic, category)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-medium truncate ${
                              isErrorTopic 
                                ? 'text-muted-contrast italic'
                                : 'text-contrast'
                            }`}>
                              {topic}
                            </p>
                          </div>
                          {!isErrorTopic && (
                            <div className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <span className="text-xs text-muted-contrast">→</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              ).flat()}
              
              {Object.keys(getFilteredTopics()).length === 0 && (
                <div className="text-center py-8 text-muted-contrast">
                  <p className="text-sm">No trending topics available</p>
                  <p className="text-xs mt-1">Try refreshing or check your connection</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Trending Topic Popup */}
      {showPopup && (
        <TrendingTopicPopup
          topic={selectedTopic}
          category={selectedCategory}
          onClose={() => setShowPopup(false)}
        />
      )}

      {/* Category Popup */}
      {showCategoryPopup && (
        <TrendingTopicPopup
          topic={`${categories[selectedCategory]} Trends`}
          category={selectedCategory}
          isCategoryPopup={true}
          onClose={() => setShowCategoryPopup(false)}
        />
      )}
    </Card>
  );
};

export default WeeklyTrends;