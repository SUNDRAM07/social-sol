import { useState, useEffect } from "react";
import Button from "./ui/Button.jsx";
import { toast } from "sonner";
import { apiFetch, apiUrl } from "../lib/api.js";
import apiClient from "../lib/apiClient.js";

const GoogleDriveIntegration = ({ campaigns = [], onSaveComplete, updateCampaign }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savingCampaigns, setSavingCampaigns] = useState(new Set());

  // Check Google connection status on component mount
  useEffect(() => {
    checkGoogleStatus();
  }, []);

  const checkGoogleStatus = async () => {
    try {
      const data = await apiClient.getGoogleStatus();
      setIsConnected(data && (data.connected || data.success));
    } catch (error) {
      console.error("Failed to check Google status:", error);
      setIsConnected(false);
    }
  };

  const connectToGoogle = async () => {
    try {
      setLoading(true);
      // Open Google OAuth in a new window
      const response = await apiFetch("/google/connect");
      if (response.ok) {
        window.open(apiUrl("/google/connect"), "_blank", "width=500,height=600");
        // Poll for connection status
        const pollInterval = setInterval(async () => {
          await checkGoogleStatus();
          const statusData = await apiClient.getGoogleStatus();
          if (statusData && (statusData.connected || statusData.success)) {
            setIsConnected(true);
            clearInterval(pollInterval);
            toast.success("Successfully connected to Google Drive!");
          }
        }, 2000);
        
        // Stop polling after 60 seconds
        setTimeout(() => clearInterval(pollInterval), 60000);
      }
    } catch (error) {
      console.error("Failed to connect to Google:", error);
      toast.error("Failed to connect to Google Drive");
    } finally {
      setLoading(false);
    }
  };

  const saveCampaignToDrive = async (campaign) => {
    if (!isConnected) {
      toast.error("Please connect to Google Drive first");
      return;
    }

    setSavingCampaigns(prev => new Set([...prev, campaign.id]));
    
    try {
      const campaignData = {
        id: campaign.id,
        productDescription: campaign.productDescription || campaign.description,
        generatedContent: campaign.generatedContent || campaign.caption,
        scheduledAt: campaign.scheduledAt,
        status: campaign.status,
        imageUrl: campaign.imageUrl,
        activity: campaign.activity || [
          { time: Date.now(), text: "Campaign created" }
        ]
      };

      const data = await apiClient.saveCampaignToDrive(campaignData);
      if (data && data.success) {
        toast.success(`Campaign saved to Google Drive! File ID: ${data.fileId}`);
        if (onSaveComplete) {
          const saveData = {
            ...data,
            updatedImageUrl: data.updatedImageUrl || campaign.imageUrl,
          };
          onSaveComplete(campaign.id, saveData);
        }
      } else {
        throw new Error(data && (data.error || data.message) || "Failed to save to Google Drive");
      }
    } catch (error) {
      console.error("Failed to save campaign:", error);
      toast.error("Failed to save campaign to Google Drive");
    } finally {
      setSavingCampaigns(prev => {
        const newSet = new Set(prev);
        newSet.delete(campaign.id);
        return newSet;
      });
    }
  };

  const saveAllCampaignsToDrive = async () => {
    if (!isConnected) {
      toast.error("Please connect to Google Drive first");
      return;
    }

    if (campaigns.length === 0) {
      toast.error("No campaigns to save");
      return;
    }

    setLoading(true);
    let successCount = 0;
    
    for (const campaign of campaigns) {
      try {
        await saveCampaignToDrive(campaign);
        successCount++;
      } catch (error) {
        console.error(`Failed to save campaign ${campaign.id}:`, error);
      }
    }
    
    setLoading(false);
    toast.success(`Saved ${successCount} out of ${campaigns.length} campaigns to Google Drive`);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center space-x-3">
          <div className="text-2xl">📁</div>
          <div>
            <h3 className="font-medium text-gray-900">Google Drive Integration</h3>
            <p className="text-sm text-gray-600">
              {isConnected ? "Connected to Google Drive" : "Connect to save campaigns to Google Drive"}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className={`${isConnected ? 'bg-green-500' : 'bg-red-500'} w-2 h-2 rounded-full`} />
          <span className="text-sm text-gray-600">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        {!isConnected ? (
          <Button 
            onClick={connectToGoogle} 
            disabled={loading}
            variant="primary"
          >
            {loading ? "Connecting..." : "Connect Google Drive"}
          </Button>
        ) : (
          <>
            <Button 
              onClick={saveAllCampaignsToDrive} 
              disabled={loading || campaigns.length === 0}
              variant="primary"
            >
              {loading ? "Saving All..." : `Save All to Drive (${campaigns.length})`}
            </Button>
            <Button 
              onClick={checkGoogleStatus}
              variant="secondary" 
              size="sm"
            >
              Refresh Status
            </Button>
          </>
        )}
      </div>

      {/* Individual campaign save buttons */}
      {isConnected && campaigns.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900">Individual Campaign Actions</h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {campaigns.map((campaign) => (
              <div key={campaign.id} className="flex items-center justify-between p-2 bg-white border rounded">
                <div className="text-sm truncate max-w-xs">
                  {campaign.productDescription || campaign.description || campaign.id}
                </div>
                <Button
                  size="sm"
                  onClick={() => saveCampaignToDrive(campaign)}
                  disabled={savingCampaigns.has(campaign.id)}
                  variant="secondary"
                >
                  {savingCampaigns.has(campaign.id) ? "Saving..." : "Save to Drive"}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GoogleDriveIntegration;
