import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { 
  Zap, Clock, TrendingUp, Users, Bell, Send, 
  MessageSquare, Twitter, Hash, Plus, Trash2, 
  ChevronRight, Save, Play, ArrowLeft, Sparkles,
  DollarSign, Activity, Target, AlertTriangle
} from 'lucide-react';
import { apiFetch } from '../lib/api';
import { useAuthStore } from '../store/authStore';

// Trigger icons mapping
const TRIGGER_ICONS = {
  price_above: TrendingUp,
  price_below: TrendingUp,
  holder_milestone: Users,
  whale_transfer: DollarSign,
  new_holder: Users,
  scheduled: Clock,
  recurring: Clock,
  engagement_spike: Activity,
  follower_milestone: Target
};

// Action icons mapping
const ACTION_ICONS = {
  post_twitter: Twitter,
  post_discord: Hash,
  post_telegram: Send,
  post_all: Zap,
  send_notification: Bell,
  generate_content: Sparkles,
  schedule_optimal: Clock
};

// Category colors
const CATEGORY_COLORS = {
  onchain: 'from-purple-500 to-indigo-600',
  time: 'from-blue-500 to-cyan-500',
  platform: 'from-green-500 to-emerald-500'
};

export default function FlowBuilder() {
  const navigate = useNavigate();
  const { flowId } = useParams();
  const { token } = useAuthStore();
  const isEditing = !!flowId;
  
  // Form state
  const [flowName, setFlowName] = useState('');
  const [flowDescription, setFlowDescription] = useState('');
  const [selectedTrigger, setSelectedTrigger] = useState(null);
  const [triggerConfig, setTriggerConfig] = useState({});
  const [conditions, setConditions] = useState([]);
  const [actions, setActions] = useState([]);
  
  // UI state
  const [step, setStep] = useState(1); // 1: Trigger, 2: Conditions, 3: Actions, 4: Review
  const [triggers, setTriggers] = useState({});
  const [actionTypes, setActionTypes] = useState({});
  const [userTier, setUserTier] = useState('FREE');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  
  // Load trigger and action types
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        const [triggersRes, actionsRes] = await Promise.all([
          apiFetch('/api/flows/triggers'),
          apiFetch('/api/flows/actions')
        ]);
        
        const triggersData = await triggersRes.json();
        const actionsData = await actionsRes.json();
        
        if (triggersData.success) {
          setTriggers(triggersData.triggers);
          setUserTier(triggersData.tier);
        }
        
        if (actionsData.success) {
          setActionTypes(actionsData.actions);
        }
        
        // Load existing flow if editing
        if (flowId) {
          const flowRes = await apiFetch(`/api/flows/${flowId}`);
          const flowData = await flowRes.json();
          
          if (flowData.success && flowData.flow) {
            setFlowName(flowData.flow.name);
            setFlowDescription(flowData.flow.description || '');
            setSelectedTrigger(flowData.flow.trigger_type);
            setTriggerConfig(flowData.flow.trigger_config);
            setConditions(flowData.flow.conditions || []);
            setActions(flowData.flow.actions || []);
          }
        }
        
      } catch (err) {
        console.error('Error loading data:', err);
        setError('Failed to load flow builder data');
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [flowId]);
  
  // Add new action
  const addAction = () => {
    setActions([...actions, { type: '', config: {} }]);
  };
  
  // Update action
  const updateAction = (index, field, value) => {
    const newActions = [...actions];
    if (field === 'type') {
      newActions[index] = { type: value, config: {} };
    } else {
      newActions[index].config[field] = value;
    }
    setActions(newActions);
  };
  
  // Remove action
  const removeAction = (index) => {
    setActions(actions.filter((_, i) => i !== index));
  };
  
  // Add condition
  const addCondition = () => {
    setConditions([...conditions, { field: '', operator: 'equals', value: '' }]);
  };
  
  // Update condition
  const updateCondition = (index, field, value) => {
    const newConditions = [...conditions];
    newConditions[index][field] = value;
    setConditions(newConditions);
  };
  
  // Remove condition
  const removeCondition = (index) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };
  
  // Save flow
  const handleSave = async () => {
    if (!flowName || !selectedTrigger || actions.length === 0) {
      setError('Please complete all required fields');
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      
      const payload = {
        name: flowName,
        description: flowDescription,
        trigger_type: selectedTrigger,
        trigger_config: triggerConfig,
        conditions: conditions.filter(c => c.field && c.value),
        actions: actions.filter(a => a.type)
      };
      
      const url = isEditing ? `/api/flows/${flowId}` : '/api/flows/';
      const method = isEditing ? 'PUT' : 'POST';
      
      const response = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      
      if (data.success) {
        navigate('/flows');
      } else {
        setError(data.error || 'Failed to save flow');
      }
      
    } catch (err) {
      console.error('Error saving flow:', err);
      setError('Failed to save flow');
    } finally {
      setSaving(false);
    }
  };
  
  // Test flow
  const handleTest = async () => {
    if (!flowId) {
      setError('Save the flow first to test it');
      return;
    }
    
    try {
      const response = await apiFetch(`/api/flows/${flowId}/test`, { method: 'POST' });
      const data = await response.json();
      
      if (data.success) {
        alert('Flow test executed successfully! Check the results.');
      } else {
        setError(data.error || 'Test failed');
      }
    } catch (err) {
      setError('Failed to test flow');
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }
  
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/flows')}
            className="p-2 hover:bg-[var(--bg-muted)] rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-[var(--text-muted)]" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-[var(--text)]">
              {isEditing ? 'Edit Flow' : 'Create New Flow'}
            </h1>
            <p className="text-[var(--text-muted)] text-sm">
              Build automations with WHEN → IF → DO logic
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {isEditing && (
            <button
              onClick={handleTest}
              className="flex items-center gap-2 px-4 py-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] hover:bg-[var(--bg-muted)] transition-colors"
            >
              <Play className="w-4 h-4" />
              Test
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Flow'}
          </button>
        </div>
      </div>
      
      {/* Error display */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3 text-red-500">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      
      {/* Flow Name */}
      <div className="mb-8 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6">
        <label className="block text-sm font-medium text-[var(--text)] mb-2">
          Flow Name *
        </label>
        <input
          type="text"
          value={flowName}
          onChange={(e) => setFlowName(e.target.value)}
          placeholder="e.g., Tweet when price pumps"
          className="w-full p-3 bg-[var(--bg-muted)] border border-[var(--border)] rounded-lg text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
        <textarea
          value={flowDescription}
          onChange={(e) => setFlowDescription(e.target.value)}
          placeholder="Optional description..."
          rows={2}
          className="w-full mt-3 p-3 bg-[var(--bg-muted)] border border-[var(--border)] rounded-lg text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
        />
      </div>
      
      {/* Step Progress */}
      <div className="flex items-center justify-center gap-4 mb-8">
        {['Trigger', 'Conditions', 'Actions'].map((label, index) => (
          <React.Fragment key={label}>
            <button
              onClick={() => setStep(index + 1)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full transition-colors ${
                step === index + 1
                  ? 'bg-purple-600 text-white'
                  : step > index + 1
                    ? 'bg-green-500/20 text-green-500'
                    : 'bg-[var(--bg-muted)] text-[var(--text-muted)]'
              }`}
            >
              <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center text-sm">
                {index + 1}
              </span>
              {label}
            </button>
            {index < 2 && <ChevronRight className="w-5 h-5 text-[var(--text-muted)]" />}
          </React.Fragment>
        ))}
      </div>
      
      {/* Step 1: Select Trigger */}
      {step === 1 && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text)] mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-purple-500" />
            WHEN - Select Trigger
          </h2>
          
          {/* Trigger categories */}
          {['onchain', 'time', 'platform'].map(category => {
            const categoryTriggers = Object.entries(triggers).filter(
              ([_, t]) => t.category === category
            );
            
            if (categoryTriggers.length === 0) return null;
            
            return (
              <div key={category} className="mb-6">
                <h3 className="text-sm font-medium text-[var(--text-muted)] uppercase mb-3">
                  {category === 'onchain' ? '⛓️ On-Chain Events' : 
                   category === 'time' ? '⏰ Time-Based' : '📱 Platform Events'}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {categoryTriggers.map(([key, trigger]) => {
                    const Icon = TRIGGER_ICONS[key] || Zap;
                    const isSelected = selectedTrigger === key;
                    
                    return (
                      <button
                        key={key}
                        onClick={() => {
                          setSelectedTrigger(key);
                          setTriggerConfig({});
                        }}
                        className={`p-4 rounded-xl border-2 text-left transition-all ${
                          isSelected
                            ? 'border-purple-500 bg-purple-500/10'
                            : 'border-[var(--border)] hover:border-purple-500/50 bg-[var(--bg-muted)]'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`p-2 rounded-lg bg-gradient-to-br ${CATEGORY_COLORS[category]}`}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <div className="font-medium text-[var(--text)]">{trigger.name}</div>
                            <div className="text-sm text-[var(--text-muted)]">{trigger.description}</div>
                            <div className="mt-2 text-xs px-2 py-1 rounded-full bg-[var(--bg-muted)] text-[var(--text-muted)] inline-block">
                              {trigger.tier}+ required
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
          
          {/* Trigger Configuration */}
          {selectedTrigger && triggers[selectedTrigger] && (
            <div className="mt-6 p-4 bg-[var(--bg-muted)] rounded-lg">
              <h4 className="font-medium text-[var(--text)] mb-3">Configure Trigger</h4>
              
              {selectedTrigger.includes('price') && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-[var(--text-muted)] mb-1">Token Address</label>
                    <input
                      type="text"
                      value={triggerConfig.token_address || ''}
                      onChange={(e) => setTriggerConfig({...triggerConfig, token_address: e.target.value})}
                      placeholder="Solana token address..."
                      className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-[var(--text-muted)] mb-1">Threshold (USD)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={triggerConfig.threshold || ''}
                      onChange={(e) => setTriggerConfig({...triggerConfig, threshold: parseFloat(e.target.value)})}
                      placeholder="1.50"
                      className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                    />
                  </div>
                </div>
              )}
              
              {selectedTrigger === 'holder_milestone' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-[var(--text-muted)] mb-1">Token Address</label>
                    <input
                      type="text"
                      value={triggerConfig.token_address || ''}
                      onChange={(e) => setTriggerConfig({...triggerConfig, token_address: e.target.value})}
                      placeholder="Solana token address..."
                      className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-[var(--text-muted)] mb-1">Milestone Count</label>
                    <input
                      type="number"
                      value={triggerConfig.milestone || ''}
                      onChange={(e) => setTriggerConfig({...triggerConfig, milestone: parseInt(e.target.value)})}
                      placeholder="1000"
                      className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                    />
                  </div>
                </div>
              )}
              
              {selectedTrigger === 'recurring' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-[var(--text-muted)] mb-1">Frequency</label>
                    <select
                      value={triggerConfig.frequency || 'daily'}
                      onChange={(e) => setTriggerConfig({...triggerConfig, frequency: e.target.value})}
                      className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-[var(--text-muted)] mb-1">Time</label>
                    <input
                      type="time"
                      value={triggerConfig.time || '09:00'}
                      onChange={(e) => setTriggerConfig({...triggerConfig, time: e.target.value})}
                      className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                    />
                  </div>
                </div>
              )}
              
              {selectedTrigger === 'scheduled' && (
                <div>
                  <label className="block text-sm text-[var(--text-muted)] mb-1">Date & Time</label>
                  <input
                    type="datetime-local"
                    value={triggerConfig.datetime || ''}
                    onChange={(e) => setTriggerConfig({...triggerConfig, datetime: e.target.value})}
                    className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                  />
                </div>
              )}
            </div>
          )}
          
          <div className="mt-6 flex justify-end">
            <button
              onClick={() => setStep(2)}
              disabled={!selectedTrigger}
              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              Next: Conditions
            </button>
          </div>
        </div>
      )}
      
      {/* Step 2: Conditions (Optional) */}
      {step === 2 && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text)] mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-500" />
            IF - Add Conditions (Optional)
          </h2>
          <p className="text-[var(--text-muted)] mb-4">
            Add conditions to filter when the flow should execute
          </p>
          
          {conditions.map((condition, index) => (
            <div key={index} className="flex items-center gap-3 mb-3 p-3 bg-[var(--bg-muted)] rounded-lg">
              <select
                value={condition.field}
                onChange={(e) => updateCondition(index, 'field', e.target.value)}
                className="flex-1 p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
              >
                <option value="">Select field...</option>
                <option value="price">Price</option>
                <option value="holder_count">Holder Count</option>
                <option value="time_of_day">Time of Day</option>
                <option value="day_of_week">Day of Week</option>
              </select>
              
              <select
                value={condition.operator}
                onChange={(e) => updateCondition(index, 'operator', e.target.value)}
                className="w-40 p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
              >
                <option value="equals">=</option>
                <option value="not_equals">≠</option>
                <option value="greater_than">&gt;</option>
                <option value="less_than">&lt;</option>
                <option value="greater_or_equal">≥</option>
                <option value="less_or_equal">≤</option>
              </select>
              
              <input
                type="text"
                value={condition.value}
                onChange={(e) => updateCondition(index, 'value', e.target.value)}
                placeholder="Value"
                className="flex-1 p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
              />
              
              <button
                onClick={() => removeCondition(index)}
                className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          ))}
          
          <button
            onClick={addCondition}
            className="flex items-center gap-2 px-4 py-2 text-purple-500 hover:bg-purple-500/10 rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            Add Condition
          </button>
          
          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="px-6 py-2 border border-[var(--border)] text-[var(--text)] rounded-lg hover:bg-[var(--bg-muted)] transition-colors"
            >
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              Next: Actions
            </button>
          </div>
        </div>
      )}
      
      {/* Step 3: Actions */}
      {step === 3 && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text)] mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-green-500" />
            DO - Define Actions
          </h2>
          <p className="text-[var(--text-muted)] mb-4">
            What should happen when the trigger fires?
          </p>
          
          {actions.map((action, index) => {
            const ActionIcon = ACTION_ICONS[action.type] || Zap;
            
            return (
              <div key={index} className="mb-4 p-4 bg-[var(--bg-muted)] rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-green-500/20">
                    <ActionIcon className="w-5 h-5 text-green-500" />
                  </div>
                  <select
                    value={action.type}
                    onChange={(e) => updateAction(index, 'type', e.target.value)}
                    className="flex-1 p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)]"
                  >
                    <option value="">Select action...</option>
                    {Object.entries(actionTypes).map(([key, actionType]) => (
                      <option key={key} value={key}>{actionType.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => removeAction(index)}
                    className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
                
                {/* Action configuration */}
                {action.type && (
                  <div className="mt-3 space-y-3">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`ai-${index}`}
                        checked={action.config.use_ai !== false}
                        onChange={(e) => updateAction(index, 'use_ai', e.target.checked)}
                        className="rounded border-[var(--border)]"
                      />
                      <label htmlFor={`ai-${index}`} className="text-sm text-[var(--text)]">
                        Use AI to generate content
                      </label>
                    </div>
                    
                    {action.config.use_ai !== false && (
                      <div>
                        <label className="block text-sm text-[var(--text-muted)] mb-1">
                          AI Prompt
                        </label>
                        <textarea
                          value={action.config.ai_prompt || ''}
                          onChange={(e) => updateAction(index, 'ai_prompt', e.target.value)}
                          placeholder="Create an exciting announcement about {trigger_event}..."
                          rows={2}
                          className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] resize-none"
                        />
                        <p className="text-xs text-[var(--text-muted)] mt-1">
                          Use {'{trigger_event}'}, {'{price}'}, {'{amount}'} as variables
                        </p>
                      </div>
                    )}
                    
                    {action.config.use_ai === false && (
                      <div>
                        <label className="block text-sm text-[var(--text-muted)] mb-1">
                          Content
                        </label>
                        <textarea
                          value={action.config.content || ''}
                          onChange={(e) => updateAction(index, 'content', e.target.value)}
                          placeholder="Your post content..."
                          rows={3}
                          className="w-full p-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-[var(--text)] resize-none"
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          
          <button
            onClick={addAction}
            className="flex items-center gap-2 px-4 py-2 text-green-500 hover:bg-green-500/10 rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            Add Action
          </button>
          
          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2 border border-[var(--border)] text-[var(--text)] rounded-lg hover:bg-[var(--bg-muted)] transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleSave}
              disabled={saving || actions.length === 0 || !actions.some(a => a.type)}
              className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Flow'}
            </button>
          </div>
        </div>
      )}
      
      {/* Visual Flow Preview */}
      <div className="mt-8 p-6 bg-[var(--bg-muted)] rounded-xl">
        <h3 className="text-sm font-medium text-[var(--text-muted)] mb-4">Flow Preview</h3>
        <div className="flex items-center justify-center gap-4">
          {/* Trigger */}
          <div className={`p-4 rounded-xl bg-gradient-to-br ${selectedTrigger ? 'from-purple-500 to-indigo-600' : 'from-gray-500 to-gray-600'} text-white min-w-[150px] text-center`}>
            <div className="text-xs opacity-75 mb-1">WHEN</div>
            <div className="font-medium">
              {selectedTrigger ? triggers[selectedTrigger]?.name : 'Select Trigger'}
            </div>
          </div>
          
          <ChevronRight className="w-6 h-6 text-[var(--text-muted)]" />
          
          {/* Conditions */}
          <div className={`p-4 rounded-xl ${conditions.length > 0 ? 'bg-blue-500/20 border-2 border-blue-500' : 'bg-[var(--surface)] border-2 border-dashed border-[var(--border)]'} min-w-[150px] text-center`}>
            <div className="text-xs text-[var(--text-muted)] mb-1">IF</div>
            <div className="font-medium text-[var(--text)]">
              {conditions.length > 0 ? `${conditions.length} condition${conditions.length > 1 ? 's' : ''}` : 'No conditions'}
            </div>
          </div>
          
          <ChevronRight className="w-6 h-6 text-[var(--text-muted)]" />
          
          {/* Actions */}
          <div className={`p-4 rounded-xl ${actions.length > 0 && actions.some(a => a.type) ? 'bg-gradient-to-br from-green-500 to-emerald-600 text-white' : 'bg-[var(--surface)] border-2 border-dashed border-[var(--border)]'} min-w-[150px] text-center`}>
            <div className="text-xs opacity-75 mb-1">DO</div>
            <div className="font-medium">
              {actions.filter(a => a.type).length > 0 
                ? `${actions.filter(a => a.type).length} action${actions.filter(a => a.type).length > 1 ? 's' : ''}`
                : 'Add Actions'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
