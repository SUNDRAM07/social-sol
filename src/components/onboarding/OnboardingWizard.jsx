import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { 
  Sparkles, 
  Wallet, 
  Share2, 
  Rocket, 
  ArrowRight, 
  ArrowLeft,
  Check,
  Twitter,
  Youtube,
  MessageCircle,
  Linkedin,
  X
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { checkPlatformConnections, apiUrl } from '../../lib/apiClient';

const STEPS = [
  {
    id: 'welcome',
    title: 'Welcome to SocialAnywhere',
    subtitle: 'Your AI-powered social media manager for Web3',
    icon: Sparkles,
  },
  {
    id: 'wallet',
    title: 'Connect Your Wallet',
    subtitle: 'Hold $SOCIAL tokens for premium features',
    icon: Wallet,
  },
  {
    id: 'platforms',
    title: 'Connect Social Platforms',
    subtitle: 'Link at least one account to start posting',
    icon: Share2,
  },
  {
    id: 'ready',
    title: "You're All Set!",
    subtitle: 'Start creating amazing content with AI',
    icon: Rocket,
  },
];

const PLATFORMS = [
  { id: 'twitter', name: 'Twitter/X', icon: Twitter, color: 'text-blue-400' },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'text-blue-500' },
  { id: 'youtube', name: 'YouTube', icon: Youtube, color: 'text-red-500' },
  { id: 'reddit', name: 'Reddit', icon: MessageCircle, color: 'text-orange-500' },
];

export default function OnboardingWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [platformConnections, setPlatformConnections] = useState({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  
  const { connected, publicKey } = useWallet();
  const { user, linkWallet, token } = useAuthStore();

  // Check platform connections
  useEffect(() => {
    const fetchConnections = async () => {
      try {
        const data = await checkPlatformConnections();
        if (data && data.platforms) {
          const connections = {};
          data.platforms.forEach(p => {
            connections[p.platform] = p.connected;
          });
          setPlatformConnections(connections);
        }
      } catch (e) {
        console.error('Failed to fetch platform connections:', e);
      }
    };
    fetchConnections();
  }, []);

  // Auto-link wallet when connected
  useEffect(() => {
    const autoLink = async () => {
      if (connected && publicKey && user && !user.wallet_address) {
        try {
          await linkWallet(publicKey.toBase58());
        } catch (e) {
          console.error('Auto-link failed:', e);
        }
      }
    };
    autoLink();
  }, [connected, publicKey, user, linkWallet]);

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleComplete = () => {
    // Mark onboarding as complete in localStorage
    localStorage.setItem('onboarding_completed', 'true');
    
    if (onComplete) {
      onComplete();
    } else {
      navigate('/chat');
    }
  };

  const handleSkip = () => {
    localStorage.setItem('onboarding_completed', 'true');
    navigate('/chat');
  };

  const handleConnectPlatform = (platformId) => {
    // Open OAuth flow in new window
    const authUrl = `${apiUrl}/social-media/${platformId}/oauth/initiate`;
    window.open(authUrl, '_blank', 'width=600,height=700');
  };

  const hasAnyConnection = Object.values(platformConnections).some(v => v);

  const renderStepContent = () => {
    switch (STEPS[currentStep].id) {
      case 'welcome':
        return (
          <div className="text-center space-y-6">
            <div className="w-24 h-24 mx-auto bg-gradient-to-br from-purple-500 to-pink-500 rounded-3xl flex items-center justify-center shadow-lg shadow-purple-500/30">
              <Sparkles className="w-12 h-12 text-white" />
            </div>
            
            <div>
              <h2 className="text-3xl font-bold text-white mb-3">
                Welcome to SocialAnywhere! 🎉
              </h2>
              <p className="text-gray-400 text-lg max-w-md mx-auto">
                The AI-powered social media manager built for Web3 projects. 
                Let's get you set up in under 2 minutes.
              </p>
            </div>

            <div className="bg-white/5 rounded-xl p-6 text-left max-w-md mx-auto">
              <h4 className="text-sm font-semibold text-gray-300 mb-4">What you'll be able to do:</h4>
              <ul className="space-y-3 text-sm text-gray-400">
                <li className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <span>Generate AI-powered content in seconds</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <span>Schedule posts across multiple platforms</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <span>Track analytics and optimize timing</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <span>Chat with AI to manage everything</span>
                </li>
              </ul>
            </div>
          </div>
        );

      case 'wallet':
        return (
          <div className="text-center space-y-6">
            <div className={`w-24 h-24 mx-auto rounded-3xl flex items-center justify-center shadow-lg ${
              connected ? 'bg-green-500 shadow-green-500/30' : 'bg-gradient-to-br from-purple-500 to-pink-500 shadow-purple-500/30'
            }`}>
              {connected ? (
                <Check className="w-12 h-12 text-white" />
              ) : (
                <Wallet className="w-12 h-12 text-white" />
              )}
            </div>
            
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">
                {connected ? 'Wallet Connected! ✅' : 'Connect Your Solana Wallet'}
              </h2>
              <p className="text-gray-400 max-w-md mx-auto">
                {connected 
                  ? `Connected: ${publicKey.toBase58().slice(0, 8)}...${publicKey.toBase58().slice(-8)}`
                  : 'Hold $SOCIAL tokens to unlock unlimited posts, auto-scheduling, and premium AI features.'
                }
              </p>
            </div>

            {!connected && (
              <>
                <div className="flex justify-center">
                  <WalletMultiButton className="!bg-gradient-to-r from-purple-500 to-pink-500 !rounded-xl !py-3 !px-8 !text-base !font-medium" />
                </div>

                <div className="bg-yellow-500/10 rounded-xl p-4 max-w-md mx-auto border border-yellow-500/30">
                  <p className="text-sm text-yellow-300">
                    💡 <strong>Tip:</strong> You can skip this step and connect later. 
                    Basic features work without a wallet!
                  </p>
                </div>
              </>
            )}

            {connected && (
              <div className="bg-green-500/10 rounded-xl p-4 max-w-md mx-auto border border-green-500/30">
                <p className="text-sm text-green-300">
                  🎉 <strong>Awesome!</strong> Your wallet is connected. 
                  Get $SOCIAL tokens to unlock premium features.
                </p>
              </div>
            )}
          </div>
        );

      case 'platforms':
        return (
          <div className="text-center space-y-6">
            <div className={`w-24 h-24 mx-auto rounded-3xl flex items-center justify-center shadow-lg ${
              hasAnyConnection ? 'bg-green-500 shadow-green-500/30' : 'bg-gradient-to-br from-blue-500 to-cyan-500 shadow-blue-500/30'
            }`}>
              {hasAnyConnection ? (
                <Check className="w-12 h-12 text-white" />
              ) : (
                <Share2 className="w-12 h-12 text-white" />
              )}
            </div>
            
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">
                Connect Your Social Accounts
              </h2>
              <p className="text-gray-400 max-w-md mx-auto">
                Link at least one platform to start scheduling and posting content.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
              {PLATFORMS.map((platform) => {
                const isConnected = platformConnections[platform.id];
                const Icon = platform.icon;
                
                return (
                  <button
                    key={platform.id}
                    onClick={() => !isConnected && handleConnectPlatform(platform.id)}
                    disabled={isConnected}
                    className={`p-4 rounded-xl border transition-all ${
                      isConnected 
                        ? 'bg-green-500/10 border-green-500/30 cursor-default'
                        : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-purple-500/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`w-6 h-6 ${isConnected ? 'text-green-400' : platform.color}`} />
                      <div className="text-left">
                        <p className="text-sm font-medium text-white">{platform.name}</p>
                        <p className={`text-xs ${isConnected ? 'text-green-400' : 'text-gray-500'}`}>
                          {isConnected ? 'Connected ✓' : 'Click to connect'}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {!hasAnyConnection && (
              <p className="text-sm text-gray-500">
                You can also connect platforms later from Settings
              </p>
            )}
          </div>
        );

      case 'ready':
        return (
          <div className="text-center space-y-6">
            <div className="w-24 h-24 mx-auto bg-gradient-to-br from-green-500 to-emerald-500 rounded-3xl flex items-center justify-center shadow-lg shadow-green-500/30 animate-pulse">
              <Rocket className="w-12 h-12 text-white" />
            </div>
            
            <div>
              <h2 className="text-3xl font-bold text-white mb-3">
                You're Ready to Go! 🚀
              </h2>
              <p className="text-gray-400 text-lg max-w-md mx-auto">
                Start chatting with AI to create your first campaign, generate content ideas, or schedule posts.
              </p>
            </div>

            <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl p-6 max-w-md mx-auto border border-purple-500/30">
              <h4 className="text-sm font-semibold text-white mb-3">Try saying:</h4>
              <ul className="space-y-2 text-sm text-gray-300">
                <li>"Create a Twitter thread about my NFT project"</li>
                <li>"Schedule 5 posts for next week"</li>
                <li>"What are the best times to post?"</li>
              </ul>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex items-center justify-center p-6">
      <div className="max-w-2xl w-full">
        {/* Progress dots */}
        <div className="flex justify-center gap-2 mb-8">
          {STEPS.map((step, index) => (
            <div
              key={step.id}
              className={`w-3 h-3 rounded-full transition-all ${
                index === currentStep
                  ? 'bg-purple-500 w-8'
                  : index < currentStep
                  ? 'bg-green-500'
                  : 'bg-white/20'
              }`}
            />
          ))}
        </div>

        {/* Content card */}
        <div className="bg-white/5 backdrop-blur-xl rounded-3xl p-8 md:p-12 border border-white/10">
          {renderStepContent()}

          {/* Navigation buttons */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/10">
            <button
              onClick={handleBack}
              disabled={currentStep === 0}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                currentStep === 0
                  ? 'text-gray-600 cursor-not-allowed'
                  : 'text-gray-300 hover:text-white hover:bg-white/10'
              }`}
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>

            <div className="flex items-center gap-3">
              {currentStep < STEPS.length - 1 && (
                <button
                  onClick={handleSkip}
                  className="text-gray-400 hover:text-white text-sm transition-colors"
                >
                  Skip for now
                </button>
              )}

              <button
                onClick={handleNext}
                className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-medium rounded-lg transition-all shadow-lg shadow-purple-500/25"
              >
                {currentStep === STEPS.length - 1 ? (
                  <>
                    Start Creating
                    <Rocket className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Continue
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Close button */}
        <button
          onClick={handleSkip}
          className="absolute top-6 right-6 p-2 text-gray-400 hover:text-white transition-colors"
          title="Skip onboarding"
        >
          <X className="w-6 h-6" />
        </button>
      </div>
    </div>
  );
}
