import { useState, useEffect } from "react";

const ProgressBar = ({ 
  progress = 0, 
  isVisible = false, 
  steps = [], 
  currentStep = 0,
  variant = "primary" // primary, success, warning, danger
}) => {
  const [displayProgress, setDisplayProgress] = useState(0);

  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        setDisplayProgress(progress);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setDisplayProgress(0);
    }
  }, [progress, isVisible]);

  const getProgressColor = () => {
    switch (variant) {
      case "success":
        return "bg-green-600";
      case "warning":
        return "bg-yellow-500";
      case "danger":
        return "bg-red-600";
      default:
        return "bg-blue-600";
    }
  };

  const getProgressBgColor = () => {
    switch (variant) {
      case "success":
        return "bg-green-100";
      case "warning":
        return "bg-yellow-100";
      case "danger":
        return "bg-red-100";
      default:
        return "bg-blue-100";
    }
  };

  if (!isVisible) return null;

  return (
    <div className="w-full space-y-3">
      {/* Progress Bar */}
      <div className="w-full">
        <div className={`w-full h-2 ${getProgressBgColor()} rounded-full overflow-hidden`}>
          <div
            className={`h-full ${getProgressColor()} transition-all duration-500 ease-out rounded-full`}
            style={{ width: `${displayProgress}%` }}
          />
        </div>
        <div className="flex justify-between items-center mt-1">
          <span className="text-xs text-gray-500">
            {steps.length > 0 && currentStep < steps.length 
              ? steps[currentStep] 
              : "Processing..."
            }
          </span>
          <span className="text-xs text-gray-500 font-medium">
            {Math.round(displayProgress)}%
          </span>
        </div>
      </div>

      {/* Steps Indicator */}
      {steps.length > 0 && (
        <div className="flex items-center space-x-2">
          {steps.map((step, index) => (
            <div key={index} className="flex items-center">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300 ${
                  index < currentStep
                    ? `${getProgressColor()} text-white`
                    : index === currentStep
                    ? `${getProgressColor()} text-white animate-pulse`
                    : "bg-gray-200 text-gray-500"
                }`}
              >
                {index < currentStep ? (
                  // Checkmark for completed steps
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`w-8 h-0.5 transition-all duration-300 ${
                    index < currentStep ? getProgressColor() : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
