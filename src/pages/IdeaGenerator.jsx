import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload } from 'lucide-react';
import Card from '../components/ui/Card.jsx';
import PageHeader from '../components/layout/PageHeader.jsx';
import { useAuthStore } from '../store/authStore';
import { apiFetch, apiUrl } from '../lib/api.js';

export default function IdeaGenerator() {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  
  // State for all form inputs
  const [ageRange, setAgeRange] = useState([18, 35]);
  const [platforms, setPlatforms] = useState([]);
  const [goals, setGoals] = useState([]);
  const [location, setLocation] = useState('');
  const [brandVoice, setBrandVoice] = useState('');
  const [trendMinerFile, setTrendMinerFile] = useState(null);
  const [brandAssets, setBrandAssets] = useState({ urls: '', files: [] });
  const [competitorAssets, setCompetitorAssets] = useState({ urls: '', files: [] });
  const [seasonalEvent, setSeasonalEvent] = useState('');
  const [extraInfo, setExtraInfo] = useState('');

  const sliderRef = useRef(null);
  const [isDragging, setIsDragging] = useState(null);

  const handleSliderMouseDown = useCallback((e, thumb) => {
    e.preventDefault();
    setIsDragging(thumb);
  }, []);

  const handleSliderMouseMove = useCallback((e) => {
    if (!isDragging || !sliderRef.current) return;

    const rect = sliderRef.current.getBoundingClientRect();
    const percentage = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const value = Math.round(0 + percentage * (65 - 0));

    setAgeRange(prev => {
      const newRange = [...prev];
      if (isDragging === 'min') {
        newRange[0] = Math.min(value, newRange[1] - 1);
      } else {
        newRange[1] = Math.max(value, newRange[0] + 1);
      }
      return newRange;
    });
  }, [isDragging]);

  const handleSliderMouseUp = useCallback(() => {
    setIsDragging(null);
  }, []);

  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleSliderMouseMove);
      document.addEventListener('mouseup', handleSliderMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleSliderMouseMove);
        document.removeEventListener('mouseup', handleSliderMouseUp);
      };
    }
  }, [isDragging, handleSliderMouseMove, handleSliderMouseUp]);

  const handleGoalToggle = (goal) => {
    setGoals(prev => 
      prev.includes(goal) 
        ? prev.filter(g => g !== goal)
        : [...prev, goal]
    );
  };

  const handlePlatformToggle = (platform) => {
    setPlatforms(prev => 
      prev.includes(platform) 
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  };

  const handleFileUpload = (e, type) => {
    const files = Array.from(e.target.files);
    if (type === 'trendMiner') {
      setTrendMinerFile(files[0]);
      console.log('📄 Trend miner file selected:', files[0].name);
    } else if (type === 'brandAssets') {
      setBrandAssets(prev => ({ ...prev, files: [...prev.files, ...files] }));
      console.log('🏢 Brand asset files selected:', files.length);
    } else if (type === 'competitorAssets') {
      setCompetitorAssets(prev => ({ 
        ...prev, 
        files: [...(prev.files || []), ...files] 
      }));
      console.log('🏪 Competitor asset files selected:', files.length);
    }
  };

  const [generatedIdeas, setGeneratedIdeas] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showIdeaModal, setShowIdeaModal] = useState(false);
  const [selectedIdea, setSelectedIdea] = useState(null);
  const [modalScrollTop, setModalScrollTop] = useState(0);

  const uploadFilesToServer = async () => {
    const uploadPromises = [];

    // Upload trend miner file
    if (trendMinerFile) {
      console.log('📤 Uploading trend miner file:', trendMinerFile.name);
      const formData = new FormData();
      formData.append('files', trendMinerFile);
      
      uploadPromises.push(
        fetch(apiUrl('/api/idea-generator/upload-files?file_type=trend_data'), {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token || ''}`
          },
          body: formData
        })
      );
    }

    // Upload brand assets files
    if (brandAssets.files && brandAssets.files.length > 0) {
      console.log('📤 Uploading brand asset files:', brandAssets.files.length);
      const formData = new FormData();
      brandAssets.files.forEach(file => {
        formData.append('files', file);
      });
      
      uploadPromises.push(
        fetch(apiUrl('/api/idea-generator/upload-files?file_type=brand_assets'), {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token || ''}`
          },
          body: formData
        })
      );
    }

    // Upload competitor assets files
    if (competitorAssets.files && competitorAssets.files.length > 0) {
      console.log('📤 Uploading competitor asset files:', competitorAssets.files.length);
      const formData = new FormData();
      competitorAssets.files.forEach(file => {
        formData.append('files', file);
      });
      
      uploadPromises.push(
        fetch(apiUrl('/api/idea-generator/upload-files?file_type=competitor_assets'), {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token || ''}`
          },
          body: formData
        })
      );
    }

    // Wait for all uploads to complete
    if (uploadPromises.length > 0) {
      const results = await Promise.all(uploadPromises);
      console.log('✅ File uploads completed:', results.length);
      
      // Log any upload failures
      for (let i = 0; i < results.length; i++) {
        if (!results[i].ok) {
          console.warn(`⚠️ Upload ${i+1} failed:`, results[i].status);
        }
      }
    }
  };

  const handleGenerateIdea = async () => {
    setIsGenerating(true);
    try {
      // Step 1: Upload files to server for analysis
      await uploadFilesToServer();
      
      // Step 2: Prepare the request data
      // Helper function to safely trim and return null if empty
      const safeTrim = (value) => {
        if (!value || typeof value !== 'string') return null;
        const trimmed = value.trim();
        return trimmed.length > 0 ? trimmed : null;
      };
      
      const requestData = {
        age_range: ageRange,
        location: safeTrim(location),  // Send null if empty, backend will default to 'global'
        goals: goals,
        brand_voice: safeTrim(brandVoice),
        platforms: platforms,
        trend_miner_data: trendMinerFile ? `Uploaded file: ${trendMinerFile.name}` : null,
        brand_assets_urls: typeof brandAssets === 'string' ? safeTrim(brandAssets) : safeTrim(brandAssets?.urls),
        competitor_urls: typeof competitorAssets === 'string' ? safeTrim(competitorAssets) : safeTrim(competitorAssets?.urls),
        seasonal_event: safeTrim(seasonalEvent),
        extra_information: safeTrim(extraInfo)
      };

      console.log('🚀 Sending idea generation request with analysis:', requestData);

      const response = await apiFetch('/api/idea-generator/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      const result = await response.json();
      console.log('📥 Received response:', result);

      if (result.success && result.ideas) {
        setGeneratedIdeas(result.ideas);
        console.log(`✅ Generated ${result.ideas.length} ideas successfully!`);
        
        // Auto-scroll to the generated ideas section after a short delay
        setTimeout(() => {
          const generatedIdeasSection = document.querySelector('#generated-ideas-section');
          if (generatedIdeasSection) {
            generatedIdeasSection.scrollIntoView({ 
              behavior: 'smooth', 
              block: 'start' 
            });
          }
        }, 500);
      } else {
        console.error('❌ Failed to generate ideas:', result.error);
        alert(`Failed to generate ideas: ${result.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('❌ Error generating ideas:', error);
      alert(`Error generating ideas: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExpandIdea = (idea) => {
    setModalScrollTop(window.scrollY);
    setSelectedIdea(idea);
    setShowIdeaModal(true);
  };

  const handleCreateCampaign = (idea) => {
    // Navigate to create campaign page with comprehensive idea data
    const campaignData = {
      // Campaign basic info
      campaign_name: idea.title,
      description: idea.summary,
      
      // Content details
      content_type: idea.content_type || 'Mixed',
      platforms: idea.platforms || platforms,
      
      // Timing and scheduling
      best_time_to_post: idea.best_time_to_post || '6-8 PM',
      
      // Engagement and targeting
      target_audience: idea.target_audience,
      estimated_engagement: idea.estimated_engagement || 5.0,
      trending_score: idea.trending_score || 75,
      
      // Hashtags and content strategy
      hashtags: idea.hashtags || [],
      
      // Additional details for campaign creation
      detailed_description: idea.description,
      why_viral: idea.why_viral,
      execution_tips: idea.execution_tips,
      
      // Auto-suggest campaign settings
      suggested_days: 7, // Default 7 days for campaign
      suggested_posts: 5, // Suggest 5 posts for the campaign
      
      // Form prefill indicators
      prefilled_from_idea: true,
      idea_source: 'ai_generator'
    };
    
    // Store comprehensive campaign data in localStorage
    localStorage.setItem('prefilledCampaignData', JSON.stringify(campaignData));
    
    console.log('🚀 Navigating to create campaign with data:', campaignData);
    
    // Navigate to create campaign page
    navigate('/create');
  };

  const handleClear = () => {
    setAgeRange([18, 35]);
    setPlatforms([]);
    setGoals([]);
    setLocation('');
    setBrandVoice('');
    setTrendMinerFile(null);
    setBrandAssets({ urls: '', files: [] });
    setCompetitorAssets({ urls: '', files: [] });
    setSeasonalEvent('');
    setExtraInfo('');
  };

  const goalOptions = ['Awareness', 'Engagement', 'Brand Building', 'Lead Generation', 'Sales'];
  const brandVoiceOptions = ['Friendly', 'Professional', 'Casual', 'Formal', 'Inspiring'];
  const platformOptions = ['Facebook', 'Instagram', 'Reddit', 'Twitter/X'];

  const minPercentage = ((ageRange[0] - 0) / (65 - 0)) * 100;
  const maxPercentage = ((ageRange[1] - 0) / (65 - 0)) * 100;

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold">Idea Generator</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">Create compelling content ideas with AI-powered insights and targeting</p>
        </div>
      </div>
      
      {/* Pillars Section */}
      <div className="space-y-6">
        <h2 className="page-title">Pillars</h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            {/* Audience Card */}
            <Card title={<span>Audience <span className="text-xs text-[var(--text-muted)] font-normal">(Age Group)</span></span>}>
              <div className="space-y-6">
                <div className="flex justify-between text-xs text-[var(--text-muted)]">
                  <span>0</span>
                  <span>65+</span>
                </div>
                
                <div className="relative h-2" ref={sliderRef}>
                  {/* Track background */}
                  <div className="absolute w-full h-2 bg-[var(--bg-muted)] rounded-lg top-0"></div>
                  
                  {/* Active range */}
                  <div 
                    className="absolute h-2 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg top-0"
                    style={{
                      left: `${minPercentage}%`,
                      width: `${maxPercentage - minPercentage}%`
                    }}
                  ></div>
                  
                  {/* Min thumb */}
                  <div 
                    className="absolute w-5 h-5 bg-white border-2 border-blue-500 rounded-full cursor-pointer shadow-md hover:shadow-lg transition-shadow"
                    style={{ left: `${minPercentage}%`, transform: 'translateX(-50%) translateY(-6px)', top: '0px' }}
                    onMouseDown={(e) => handleSliderMouseDown(e, 'min')}
                  ></div>
                  
                  {/* Max thumb */}
                  <div 
                    className="absolute w-5 h-5 bg-white border-2 border-blue-500 rounded-full cursor-pointer shadow-md hover:shadow-lg transition-shadow"
                    style={{ left: `${maxPercentage}%`, transform: 'translateX(-50%) translateY(-6px)', top: '0px' }}
                    onMouseDown={(e) => handleSliderMouseDown(e, 'max')}
                  ></div>
                </div>
                
                <div className="flex justify-between text-sm font-medium text-[var(--text)]">
                  <span className="bg-[var(--bg-muted)] px-2 py-1 rounded text-xs">{ageRange[0]} years</span>
                  <span className="bg-[var(--bg-muted)] px-2 py-1 rounded text-xs">{ageRange[1]} years</span>
                </div>
              </div>
            </Card>

            {/* Platform Card */}
            <Card title={<span>Platform <span className="text-red-500">*</span></span>}>
              <div className="flex flex-wrap gap-2">
                {platformOptions.map((platform) => (
                  <button
                    key={platform}
                    onClick={() => handlePlatformToggle(platform)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      platforms.includes(platform)
                        ? 'bg-blue-500 text-white shadow-md'
                        : 'bg-[var(--bg-muted)] text-[var(--text)] hover:bg-blue-100 border border-[var(--border)]'
                    }`}
                  >
                    {platform}
                  </button>
                ))}
              </div>
            </Card>

            {/* Location Card */}
            <Card title="Location">
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Enter city, country, or 'global'"
                className="w-full p-3 border border-[var(--border)] rounded-lg bg-[var(--surface)] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              />
            </Card>
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Goals Card */}
            <Card title={<span>Goals <span className="text-red-500">*</span></span>}>
              <div className="space-y-3">
                {goalOptions.map((goal) => (
                  <label key={goal} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={goals.includes(goal)}
                      onChange={() => handleGoalToggle(goal)}
                      className="w-4 h-4 text-blue-500 border-[var(--border)] rounded focus:ring-blue-500"
                    />
                    <span className="text-[var(--text)] text-sm">{goal}</span>
                  </label>
                ))}
              </div>
            </Card>

            {/* Brand Voice Card */}
            <Card title="Brand Voice">
              <div className="space-y-3">
                {brandVoiceOptions.map((voice) => (
                  <label key={voice} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="brandVoice"
                      value={voice}
                      checked={brandVoice === voice}
                      onChange={(e) => setBrandVoice(e.target.value)}
                      className="w-4 h-4 text-blue-500 border-[var(--border)] focus:ring-blue-500"
                    />
                    <span className="text-[var(--text)] text-sm">{voice}</span>
                  </label>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Information Section */}
      <div className="space-y-6">
        <h2 className="page-title">Information</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Trend Miner Card */}
          <Card title="Trend Miner">
            <div className="border-2 border-dashed border-blue-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
              <Upload className="w-8 h-8 mx-auto mb-3 text-blue-500" />
              <p className="text-sm text-[var(--text-muted)] mb-3">Upload CSV file for trend analysis</p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileUpload(e, 'trendMiner')}
                className="hidden"
                id="trend-upload"
              />
              <label
                htmlFor="trend-upload"
                className="inline-block bg-blue-500 text-white px-4 py-2 rounded-lg cursor-pointer hover:bg-blue-600 transition-colors text-sm font-medium"
              >
                Choose File
              </label>
              {trendMinerFile && (
                <p className="text-sm text-[var(--text)] mt-3 p-2 bg-[var(--bg-muted)] rounded">
                  📄 {trendMinerFile.name}
                </p>
              )}
            </div>
          </Card>

          {/* Seasonal Event Card - Moved to second position */}
          <Card title="Seasonal Event">
            <input
              type="text"
              value={seasonalEvent}
              onChange={(e) => setSeasonalEvent(e.target.value)}
              placeholder="e.g., Black Friday, Christmas"
              className="w-full p-3 border border-[var(--border)] rounded-lg bg-[var(--surface)] text-[var(--text)] text-sm placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all"
            />
          </Card>

          {/* Competitor Assets Card */}
          <Card title="Competitor Assets">
            <div className="space-y-4">
              {/* URL Input */}
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-2">
                  Competitor URLs
                </label>
                <textarea
                  value={typeof competitorAssets === 'string' ? competitorAssets : (competitorAssets.urls || '')}
                  onChange={(e) => setCompetitorAssets(typeof competitorAssets === 'string' ? e.target.value : { ...competitorAssets, urls: e.target.value })}
                  placeholder="Enter competitor URLs (one per line)..."
                  rows={3}
                  className="w-full p-3 border border-[var(--border)] rounded-lg bg-[var(--surface)] text-[var(--text)] text-sm placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-orange-500 resize-none transition-all"
                />
              </div>
              
              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-2">
                  Upload Assets
                </label>
                <div className="border-2 border-dashed border-orange-300 rounded-lg p-4 text-center hover:border-orange-400 transition-colors">
                  <Upload className="w-6 h-6 mx-auto mb-2 text-orange-500" />
                  <p className="text-xs text-[var(--text-muted)] mb-2">Upload competitor assets for analysis</p>
                  <input
                    type="file"
                    multiple
                    accept="image/*,video/*,.pdf"
                    onChange={(e) => {
                      const files = Array.from(e.target.files);
                      setCompetitorAssets(prev => {
                        if (typeof prev === 'string') {
                          return { urls: prev, files: files };
                        }
                        return { ...prev, files: [...(prev.files || []), ...files] };
                      });
                    }}
                    className="hidden"
                    id="competitor-upload"
                  />
                  <label
                    htmlFor="competitor-upload"
                    className="inline-block bg-orange-500 text-white px-3 py-1.5 rounded-md cursor-pointer hover:bg-orange-600 transition-colors text-xs font-medium"
                  >
                    Choose Files
                  </label>
                  {(competitorAssets.files && competitorAssets.files.length > 0) && (
                    <p className="text-xs text-[var(--text)] mt-2 p-2 bg-[var(--bg-muted)] rounded">
                      📁 {competitorAssets.files.length} file{competitorAssets.files.length !== 1 ? 's' : ''} selected
                    </p>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Brand Assets Card - Moved to fourth position */}
          <Card title="Brand Assets">
            <div className="space-y-4">
              {/* URL Input */}
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-2">
                  Asset URLs
                </label>
                <textarea
                  value={brandAssets.urls || ''}
                  onChange={(e) => setBrandAssets(prev => ({ ...prev, urls: e.target.value }))}
                  placeholder="Enter brand asset URLs (one per line)..."
                  rows={3}
                  className="w-full p-3 border border-[var(--border)] rounded-lg bg-[var(--surface)] text-[var(--text)] text-sm placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-green-500 resize-none transition-all"
                />
              </div>
              
              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-2">
                  Upload Files
                </label>
                <div className="border-2 border-dashed border-green-300 rounded-lg p-4 text-center hover:border-green-400 transition-colors">
                  <Upload className="w-6 h-6 mx-auto mb-2 text-green-500" />
                  <p className="text-xs text-[var(--text-muted)] mb-2">Upload images, videos, or assets</p>
                  <input
                    type="file"
                    multiple
                    accept="image/*,video/*"
                    onChange={(e) => handleFileUpload(e, 'brandAssets')}
                    className="hidden"
                    id="brand-upload"
                  />
                  <label
                    htmlFor="brand-upload"
                    className="inline-block bg-green-500 text-white px-3 py-1.5 rounded-md cursor-pointer hover:bg-green-600 transition-colors text-xs font-medium"
                  >
                    Choose Files
                  </label>
                  {brandAssets.files && brandAssets.files.length > 0 && (
                    <p className="text-xs text-[var(--text)] mt-2 p-2 bg-[var(--bg-muted)] rounded">
                      📁 {brandAssets.files.length} file{brandAssets.files.length !== 1 ? 's' : ''} selected
                    </p>
                  )}
                </div>
              </div>
            </div>
          </Card>
        </div>

      {/* Extra Information Card */}
      <Card title="Extra Information">
        <textarea
          value={extraInfo}
          onChange={(e) => setExtraInfo(e.target.value)}
          placeholder="Add any extra details or requirements..."
          rows={4}
          className="w-full p-3 border border-[var(--border)] rounded-lg bg-[var(--surface)] text-[var(--text)] text-sm placeholder-[var(--text-muted)] placeholder:text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none transition-all"
        />
      </Card>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row justify-center gap-4 pt-6">
        <button
          onClick={handleGenerateIdea}
          disabled={isGenerating || platforms.length === 0 || goals.length === 0}
          className={`px-8 py-3 rounded-2xl font-semibold shadow-lg transition-all duration-300 transform ${
            isGenerating || platforms.length === 0 || goals.length === 0
              ? 'bg-gray-400 cursor-not-allowed text-white'
              : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white hover:shadow-xl hover:scale-105'
          }`}
        >
          {isGenerating ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Generating...
            </>
          ) : (
            '✨ Generate Ideas'
          )}
        </button>
        <button
          onClick={handleClear}
          className="glass-hover bg-[var(--surface)] text-[var(--text)] px-8 py-3 rounded-2xl font-medium border border-[var(--border)] hover:bg-[var(--bg-muted)] transition-all duration-300"
        >
          🗑️ Clear All
        </button>
      </div>
      </div>

      {/* Generated Ideas Results */}
      {generatedIdeas.length > 0 && (
        <div id="generated-ideas-section" className="space-y-6 relative">
          <div className="text-center">
            <h2 className="text-xl font-semibold text-[var(--text)] mb-2">🎉 Generated Ideas</h2>
            <p className="text-sm text-[var(--text-muted)]">Here are {generatedIdeas.length} trending content ideas tailored for your audience</p>
          </div>
          
          <div className="flex flex-col items-center">
            <div className="flex flex-wrap gap-6 justify-center max-w-6xl mx-auto">
            {generatedIdeas.map((idea, index) => (
              <div key={idea.id || index} className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-sm hover:shadow-md transition-all duration-300 group w-full max-w-sm">
                {/* Idea Header */}
                <div className="mb-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-lg font-semibold text-[var(--text)] line-clamp-2 group-hover:text-[var(--primary)] transition-colors">
                      {idea.title}
                    </h3>
                    <div className="flex items-center gap-1 ml-2 flex-shrink-0">
                      <span className="text-xs font-medium text-[var(--primary)]">{idea.trending_score}%</span>
                      <svg className="w-4 h-4 text-[var(--primary)]" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-sm text-[var(--text-muted)] line-clamp-3 mb-3">
                    {idea.summary}
                  </p>
                </div>

                {/* Idea Stats */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--text-muted)]">Content Type:</span>
                    <span className="font-medium text-[var(--text)]">{idea.content_type}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--text-muted)]">Engagement:</span>
                    <span className="font-medium text-[var(--text)]">{idea.estimated_engagement}/10</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--text-muted)]">Best Time:</span>
                    <span className="font-medium text-[var(--text)]">{idea.best_time_to_post}</span>
                  </div>
                </div>

                {/* Platforms */}
                <div className="mb-4">
                  <div className="flex flex-wrap gap-1">
                    {idea.platforms.map((platform, idx) => (
                      <span key={idx} className="px-2 py-1 bg-[var(--bg-muted)] text-[var(--text)] text-xs rounded-md">
                        {platform.charAt(0).toUpperCase() + platform.slice(1)}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExpandIdea(idea)}
                    className="flex-1 px-3 py-2 text-sm font-medium text-[var(--primary)] border border-[var(--primary)] rounded-lg hover:bg-[var(--primary)] hover:text-white transition-colors"
                  >
                    Expand
                  </button>
                  <button
                    onClick={() => handleCreateCampaign(idea)}
                    className="flex-1 px-3 py-2 text-sm font-medium text-white bg-[var(--primary)] rounded-lg hover:bg-[var(--primary)] hover:opacity-90 transition-colors"
                  >
                    Create
                  </button>
                </div>
              </div>
            ))}
            </div>

        </div>
        </div>
      )}
      
      {/* Modal Overlay */}
      {showIdeaModal && selectedIdea && (
        <div 
          className="absolute z-50 p-4 pointer-events-none"
          style={{
            top: `${modalScrollTop}px`,
            left: 0,
            right: 0,
            minHeight: '100vh'
          }}
        >
          <div className="flex items-center justify-center min-h-screen">
            <div 
              className="bg-[var(--surface)] rounded-2xl shadow-2xl border border-[var(--border)] max-h-[90vh] w-full max-w-4xl overflow-hidden relative pointer-events-auto"
            >
            {/* Close button overlay */}
            <div className="absolute top-4 right-4 z-10">
              <button
                onClick={() => setShowIdeaModal(false)}
                className="bg-[var(--surface)] hover:bg-[var(--bg-muted)] p-2 rounded-full shadow-lg border border-[var(--border)] transition-colors"
              >
                <svg className="w-5 h-5 text-[var(--text)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Modal Header */}
            <div className="p-6 border-b border-[var(--border)] pr-16">
              <div>
                <h2 className="text-xl font-semibold text-[var(--text)] mb-2">{selectedIdea.title}</h2>
                <div className="flex items-center gap-4 text-sm text-[var(--text-muted)]">
                  <span>🔥 Trending Score: {selectedIdea.trending_score}%</span>
                  <span>📊 Est. Engagement: {selectedIdea.estimated_engagement}/10</span>
                  <span>⏰ {selectedIdea.best_time_to_post}</span>
                </div>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 200px)' }}>
              <div className="space-y-6">
                {/* Description */}
                <div>
                  <h3 className="font-semibold text-[var(--text)] mb-2">📝 Detailed Description</h3>
                  <p className="text-[var(--text-muted)] leading-relaxed whitespace-pre-wrap">{selectedIdea.description}</p>
                </div>

                {/* Why This Will Go Viral */}
                {selectedIdea.why_viral && (
                  <div>
                    <h3 className="font-semibold text-[var(--text)] mb-2">🚀 Why This Will Go Viral</h3>
                    <p className="text-[var(--text-muted)] leading-relaxed">{selectedIdea.why_viral}</p>
                  </div>
                )}

                {/* Execution Tips */}
                {selectedIdea.execution_tips && (
                  <div>
                    <h3 className="font-semibold text-[var(--text)] mb-2">💡 Execution Tips</h3>
                    <ul className="space-y-1">
                      {Array.isArray(selectedIdea.execution_tips) 
                        ? selectedIdea.execution_tips.map((tip, idx) => (
                            <li key={idx} className="text-[var(--text-muted)] flex items-start gap-2">
                              <span className="text-[var(--primary)] mt-1">•</span>
                              <span>{tip}</span>
                            </li>
                          ))
                        : <li className="text-[var(--text-muted)]">{selectedIdea.execution_tips}</li>
                      }
                    </ul>
                  </div>
                )}

                {/* Hashtags */}
                {selectedIdea.hashtags && selectedIdea.hashtags.length > 0 && (
                  <div>
                    <h3 className="font-semibold text-[var(--text)] mb-2"># Suggested Hashtags</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedIdea.hashtags.map((hashtag, idx) => (
                        <span key={idx} className="px-3 py-1 bg-[var(--bg-muted)] text-[var(--primary)] text-sm rounded-full">
                          {hashtag.startsWith('#') ? hashtag : `#${hashtag}`}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Target Audience */}
                <div>
                  <h3 className="font-semibold text-[var(--text)] mb-2">🎯 Target Audience</h3>
                  <p className="text-[var(--text-muted)]">{selectedIdea.target_audience}</p>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex gap-3 p-6 border-t border-[var(--border)] bg-[var(--bg-muted)]">
              <button
                onClick={() => setShowIdeaModal(false)}
                className="flex-1 px-4 py-2 text-[var(--text)] border border-[var(--border)] rounded-lg hover:bg-[var(--bg-muted)] transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleCreateCampaign(selectedIdea);
                  setShowIdeaModal(false);
                }}
                className="flex-1 px-4 py-2 text-white bg-[var(--primary)] rounded-lg hover:bg-[var(--primary)] hover:opacity-90 transition-colors font-medium"
              >
                Create Campaign
              </button>
            </div>
          </div>
        </div>
      </div>
      )}
    </div>
  )
}
