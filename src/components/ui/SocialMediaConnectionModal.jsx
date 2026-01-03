import React, { useState, useEffect } from 'react';
import Modal from './Modal.jsx';
import Button from './Button.jsx';
import { Facebook, Twitter, MessageCircle, Instagram } from 'lucide-react';

const PLATFORM_CONFIGS = {
  facebook: {
    name: 'Facebook',
    icon: Facebook,
    color: 'bg-blue-600',
    fields: [
      { key: 'FACEBOOK_PAGE_ID', label: 'Page ID', type: 'text', required: true, placeholder: 'Your Facebook Page ID' },
      { key: 'FACEBOOK_ACCESS_TOKEN', label: 'Access Token', type: 'password', required: true, placeholder: 'Your Facebook Page Access Token' }
    ],
    description: 'Connect your Facebook page to post content automatically.'
  },
  instagram: {
    name: 'Instagram',
    icon: Instagram,
    color: 'bg-gradient-to-br from-purple-600 via-pink-600 to-orange-600',
    fields: [
      { key: 'INSTAGRAM_ACCOUNT_ID', label: 'Instagram Business Account ID', type: 'text', required: true, placeholder: 'Your Instagram Business Account ID' },
      { key: 'INSTAGRAM_ACCESS_TOKEN', label: 'Access Token', type: 'password', required: true, placeholder: 'Your Instagram Graph API Access Token' },
      { key: 'INSTAGRAM_USERNAME', label: 'Username (Optional)', type: 'text', required: false, placeholder: '@yourusername' }
    ],
    description: 'Connect your Instagram Business account by providing your Account ID and Access Token. Get these from Facebook Developer Console.',
    helpLink: 'https://developers.facebook.com/docs/instagram-basic-display-api/getting-started'
  },
  twitter: {
    name: 'Twitter',
    icon: Twitter,
    color: 'bg-black',
    fields: [
      { key: 'TWITTER_CONSUMER_KEY', label: 'API Key', type: 'text', required: true, placeholder: 'Your Twitter API Key' },
      { key: 'TWITTER_CONSUMER_SECRET', label: 'API Secret', type: 'password', required: true, placeholder: 'Your Twitter API Secret' },
      { key: 'TWITTER_ACCESS_TOKEN', label: 'Access Token', type: 'password', required: true, placeholder: 'Your Twitter Access Token' },
      { key: 'TWITTER_ACCESS_TOKEN_SECRET', label: 'Access Token Secret', type: 'password', required: true, placeholder: 'Your Twitter Access Token Secret' },
      { key: 'TWITTER_BEARER_TOKEN', label: 'Bearer Token', type: 'password', required: true, placeholder: 'Your Twitter Bearer Token' },
      { key: 'TWITTER_CLIENT_ID', label: 'Client ID', type: 'text', required: true, placeholder: 'Your Twitter OAuth 2.0 Client ID' },
      { key: 'TWITTER_CLIENT_SECRET', label: 'Client Secret', type: 'password', required: true, placeholder: 'Your Twitter OAuth 2.0 Client Secret' },
      { key: 'TWITTER_USERNAME', label: 'Username', type: 'text', required: true, placeholder: 'Your Twitter Username' }
    ],
    description: 'Connect your Twitter account to post tweets automatically.'
  },
  reddit: {
    name: 'Reddit',
    icon: MessageCircle,
    color: 'bg-orange-600',
    fields: [
      { key: 'REDDIT_CLIENT_ID', label: 'Client ID', type: 'text', required: true, placeholder: 'Your Reddit App Client ID' },
      { key: 'REDDIT_CLIENT_SECRET', label: 'Client Secret', type: 'password', required: true, placeholder: 'Your Reddit App Client Secret' },
      { key: 'REDDIT_USERNAME', label: 'Username', type: 'text', required: true, placeholder: 'Your Reddit Username' },
      { key: 'REDDIT_PASSWORD', label: 'Password', type: 'password', required: true, placeholder: 'Your Reddit Password' },
      { key: 'REDDIT_USER_AGENT', label: 'User Agent', type: 'text', required: true, placeholder: 'Your Reddit User Agent (e.g., MyApp/1.0)' },
      { key: 'REDDIT_ACCESS_TOKEN', label: 'Access Token', type: 'password', required: true, placeholder: 'Your Reddit OAuth Access Token' },
      { key: 'REDDIT_REFRESH_TOKEN', label: 'Refresh Token', type: 'password', required: true, placeholder: 'Your Reddit OAuth Refresh Token' }
    ],
    description: 'Connect your Reddit account to post to subreddits automatically.'
  }
};

export default function SocialMediaConnectionModal({ open, onOpenChange, platform, onSave }) {
  const [credentials, setCredentials] = useState({});
  const [loading, setSaving] = useState(false);
  const [errors, setErrors] = useState({});

  const config = PLATFORM_CONFIGS[platform];

  useEffect(() => {
    if (open && platform) {
      // Reset form when modal opens
      const initialCredentials = {};
      config.fields.forEach(field => {
        initialCredentials[field.key] = '';
      });
      setCredentials(initialCredentials);
      setErrors({});
    }
  }, [open, platform, config?.fields]);

  const handleInputChange = (fieldKey, value) => {
    setCredentials(prev => ({ ...prev, [fieldKey]: value }));
    // Clear error when user starts typing
    if (errors[fieldKey]) {
      setErrors(prev => ({ ...prev, [fieldKey]: null }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    config.fields.forEach(field => {
      if (field.required && (!credentials[field.key] || credentials[field.key].trim() === '')) {
        newErrors[field.key] = `${field.label} is required`;
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSaving(true);
    try {
      await onSave(platform, credentials);
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to save credentials:', error);
    } finally {
      setSaving(false);
    }
  };

  if (!config) return null;

  const Icon = config.icon;

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={`Connect ${config.name}`}>
      <div className="space-y-6">
        {/* Platform Header */}
        <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
          <div className={`w-12 h-12 ${config.color} rounded-lg flex items-center justify-center`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-lg">{config.name}</h3>
            <p className="text-sm text-gray-600">{config.description}</p>
          </div>
        </div>

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {config.fields.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              <input
                type={field.type}
                value={credentials[field.key] || ''}
                onChange={(e) => handleInputChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors[field.key] ? 'border-red-500' : 'border-gray-300'
                }`}
                required={field.required}
              />
              {errors[field.key] && (
                <p className="text-red-500 text-xs mt-1">{errors[field.key]}</p>
              )}
            </div>
          ))}

          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={loading}>
              {loading ? 'Connecting...' : 'Save & Connect'}
            </Button>
          </div>
        </form>

        {/* Help Text */}
        <div className="text-xs text-gray-500 bg-blue-50 p-3 rounded-md">
          <p className="font-medium mb-1">How to get your credentials:</p>
          {platform === 'facebook' && (
            <div className="space-y-1">
              <p>• Go to <a href="https://developers.facebook.com/" target="_blank" rel="noopener" className="text-blue-600 underline">Facebook Developers</a></p>
              <p>• Create an app and get your Page Access Token</p>
              <p>• Find your Page ID in your Facebook page settings</p>
            </div>
          )}
          {platform === 'twitter' && (
            <div className="space-y-1">
              <p>• Go to <a href="https://developer.twitter.com/" target="_blank" rel="noopener" className="text-blue-600 underline">Twitter Developer Portal</a></p>
              <p>• Create an app and generate API keys and tokens</p>
              <p>• Make sure your app has read and write permissions</p>
              <p>• Bearer Token is needed for reading tweets</p>
              <p>• OAuth 2.0 credentials provide additional features</p>
            </div>
          )}
          {platform === 'reddit' && (
            <div className="space-y-1">
              <p>• Go to <a href="https://www.reddit.com/prefs/apps" target="_blank" rel="noopener" className="text-blue-600 underline">Reddit App Preferences</a></p>
              <p>• Create a new app and get your Client ID and Secret</p>
              <p>• Use your Reddit account credentials</p>
              <p>• Access and Refresh tokens enable OAuth authentication</p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}