import OnboardingWizard from '../components/onboarding/OnboardingWizard';
import { useNavigate } from 'react-router-dom';

export default function Onboarding() {
  const navigate = useNavigate();

  const handleComplete = () => {
    navigate('/chat');
  };

  return <OnboardingWizard onComplete={handleComplete} />;
}
