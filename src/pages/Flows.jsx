import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Zap, Plus, Play, Pause, Edit2, Trash2, 
  Clock, Activity, ChevronRight, BarChart3,
  TrendingUp, Users, Twitter, Hash, Send
} from 'lucide-react';
import { apiFetch } from '../lib/api';

// Icon mappings
const TRIGGER_ICONS = {
  price_above: TrendingUp,
  price_below: TrendingUp,
  holder_milestone: Users,
  scheduled: Clock,
  recurring: Clock,
  engagement_spike: Activity
};

const ACTION_ICONS = {
  post_twitter: Twitter,
  post_discord: Hash,
  post_telegram: Send,
  post_all: Zap
};

export default function Flows() {
  const navigate = useNavigate();
  const [flows, setFlows] = useState([]);
  const [stats, setStats] = useState({ total_flows: 0, active_flows: 0, total_triggers: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Load flows
  useEffect(() => {
    loadFlows();
  }, []);
  
  const loadFlows = async () => {
    try {
      setLoading(true);
      const response = await apiFetch('/api/flows/');
      const data = await response.json();
      
      if (data.success) {
        setFlows(data.flows || []);
        setStats(data.stats || { total_flows: 0, active_flows: 0, total_triggers: 0 });
      }
    } catch (err) {
      console.error('Error loading flows:', err);
      setError('Failed to load flows');
    } finally {
      setLoading(false);
    }
  };
  
  // Toggle flow active state
  const toggleFlow = async (flowId, e) => {
    e.stopPropagation();
    try {
      const response = await apiFetch(`/api/flows/${flowId}/toggle`, { method: 'POST' });
      const data = await response.json();
      
      if (data.success) {
        // Update local state
        setFlows(flows.map(f => 
          f.id === flowId ? { ...f, is_active: data.is_active } : f
        ));
      }
    } catch (err) {
      console.error('Error toggling flow:', err);
    }
  };
  
  // Delete flow
  const deleteFlow = async (flowId, e) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this flow?')) return;
    
    try {
      const response = await apiFetch(`/api/flows/${flowId}`, { method: 'DELETE' });
      const data = await response.json();
      
      if (data.success) {
        setFlows(flows.filter(f => f.id !== flowId));
      }
    } catch (err) {
      console.error('Error deleting flow:', err);
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
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-[var(--text)] flex items-center gap-3">
            <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600">
              <Zap className="w-7 h-7 text-white" />
            </div>
            Automation Flows
          </h1>
          <p className="mt-2 text-[var(--text-muted)]">
            Build powerful automations with WHEN → IF → DO logic
          </p>
        </div>
        
        <button
          onClick={() => navigate('/flows/new')}
          className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:opacity-90 transition-opacity shadow-lg shadow-purple-500/25"
        >
          <Plus className="w-5 h-5" />
          Create Flow
        </button>
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--text-muted)]">Total Flows</p>
              <p className="text-2xl font-bold text-[var(--text)]">{stats.total_flows || 0}</p>
            </div>
            <div className="p-3 rounded-xl bg-purple-500/20">
              <Zap className="w-6 h-6 text-purple-500" />
            </div>
          </div>
        </div>
        
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--text-muted)]">Active Flows</p>
              <p className="text-2xl font-bold text-green-500">{stats.active_flows || 0}</p>
            </div>
            <div className="p-3 rounded-xl bg-green-500/20">
              <Activity className="w-6 h-6 text-green-500" />
            </div>
          </div>
        </div>
        
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--text-muted)]">Total Triggers</p>
              <p className="text-2xl font-bold text-[var(--text)]">{stats.total_triggers || 0}</p>
            </div>
            <div className="p-3 rounded-xl bg-blue-500/20">
              <BarChart3 className="w-6 h-6 text-blue-500" />
            </div>
          </div>
        </div>
      </div>
      
      {/* Flows List */}
      {flows.length === 0 ? (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-12 text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 flex items-center justify-center">
            <Zap className="w-10 h-10 text-purple-500" />
          </div>
          <h3 className="text-xl font-semibold text-[var(--text)] mb-2">No Flows Yet</h3>
          <p className="text-[var(--text-muted)] mb-6 max-w-md mx-auto">
            Create your first automation flow to automatically post content when specific events happen.
          </p>
          <button
            onClick={() => navigate('/flows/new')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:opacity-90 transition-opacity"
          >
            <Plus className="w-5 h-5" />
            Create Your First Flow
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {flows.map((flow) => {
            const TriggerIcon = TRIGGER_ICONS[flow.trigger_type] || Zap;
            const actionTypes = flow.actions?.map(a => a.type) || [];
            
            return (
              <div
                key={flow.id}
                onClick={() => navigate(`/flows/${flow.id}`)}
                className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 hover:border-purple-500/50 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {/* Status indicator */}
                    <div className={`w-3 h-3 rounded-full ${flow.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                    
                    {/* Flow info */}
                    <div>
                      <h3 className="font-semibold text-[var(--text)] group-hover:text-purple-500 transition-colors">
                        {flow.name}
                      </h3>
                      {flow.description && (
                        <p className="text-sm text-[var(--text-muted)]">{flow.description}</p>
                      )}
                    </div>
                  </div>
                  
                  {/* Flow visual */}
                  <div className="hidden md:flex items-center gap-2">
                    {/* Trigger */}
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/20 rounded-lg">
                      <TriggerIcon className="w-4 h-4 text-purple-500" />
                      <span className="text-sm text-purple-500 capitalize">
                        {flow.trigger_type?.replace('_', ' ')}
                      </span>
                    </div>
                    
                    <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                    
                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      {actionTypes.slice(0, 3).map((actionType, i) => {
                        const ActionIcon = ACTION_ICONS[actionType] || Zap;
                        return (
                          <div key={i} className="p-1.5 bg-green-500/20 rounded-lg">
                            <ActionIcon className="w-4 h-4 text-green-500" />
                          </div>
                        );
                      })}
                      {actionTypes.length > 3 && (
                        <span className="text-sm text-[var(--text-muted)]">+{actionTypes.length - 3}</span>
                      )}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-[var(--text-muted)] mr-2">
                      {flow.trigger_count || 0} runs
                    </span>
                    
                    <button
                      onClick={(e) => toggleFlow(flow.id, e)}
                      className={`p-2 rounded-lg transition-colors ${
                        flow.is_active 
                          ? 'bg-green-500/20 text-green-500 hover:bg-green-500/30' 
                          : 'bg-[var(--bg-muted)] text-[var(--text-muted)] hover:text-[var(--text)]'
                      }`}
                      title={flow.is_active ? 'Pause flow' : 'Activate flow'}
                    >
                      {flow.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </button>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/flows/${flow.id}`);
                      }}
                      className="p-2 bg-[var(--bg-muted)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
                      title="Edit flow"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={(e) => deleteFlow(flow.id, e)}
                      className="p-2 bg-[var(--bg-muted)] rounded-lg text-[var(--text-muted)] hover:text-red-500 transition-colors"
                      title="Delete flow"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                {/* Last triggered */}
                {flow.last_triggered_at && (
                  <div className="mt-3 pt-3 border-t border-[var(--border)] flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <Clock className="w-4 h-4" />
                    Last triggered: {new Date(flow.last_triggered_at).toLocaleString()}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
      
      {/* Premium upsell for free users */}
      {stats.total_flows === 0 && (
        <div className="mt-8 p-6 bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-500/30 rounded-xl">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-purple-500/20">
              <Zap className="w-6 h-6 text-purple-500" />
            </div>
            <div>
              <h3 className="font-semibold text-[var(--text)]">Unlock Automation Flows</h3>
              <p className="text-sm text-[var(--text-muted)]">
                Premium & Agency tiers get access to powerful automation flows with on-chain triggers.
              </p>
            </div>
            <button
              onClick={() => navigate('/tokens')}
              className="ml-auto px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors whitespace-nowrap"
            >
              Upgrade Now
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
