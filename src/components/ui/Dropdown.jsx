import { useState, useRef, useEffect } from "react";
import clsx from "clsx";

function Dropdown({ options, value, onChange, placeholder = "Select...", className, ...props }) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }

        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    const selectedOption = options.find(option => option.value === value);

    return (
        <div className={clsx("relative", className)} ref={dropdownRef}>
            <button
                type="button"
                className={clsx(
                    "flex items-center gap-2 px-3.5 py-2 text-sm font-medium",
                    "bg-white border border-gray-300 rounded-md",
                    "hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-400",
                    "transition-colors"
                )}
                onClick={() => setIsOpen(!isOpen)}
                {...props}
            >
                {selectedOption?.icon && (
                    <span className="w-4 h-4 flex items-center justify-center">
                        {selectedOption.icon}
                    </span>
                )}
                <span>{selectedOption?.label || placeholder}</span>
                <svg
                    className={clsx(
                        "w-4 h-4 transition-transform",
                        isOpen ? "rotate-180" : ""
                    )}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {isOpen && (
                <div className="absolute right-0 z-10 mt-1 w-full min-w-[200px] bg-white border border-gray-300 rounded-md shadow-lg">
                    <div className="py-1">
                        {options.map((option) => (
                            <button
                                key={option.value}
                                className={clsx(
                                    "w-full flex items-center gap-2 px-3.5 py-2 text-sm text-left",
                                    "hover:bg-gray-50 transition-colors",
                                    value === option.value ? "bg-blue-50 text-blue-700" : "text-gray-700"
                                )}
                                onClick={() => {
                                    onChange(option.value);
                                    setIsOpen(false);
                                }}
                            >
                                {option.icon && (
                                    <span className="w-4 h-4 flex items-center justify-center">
                                        {option.icon}
                                    </span>
                                )}
                                <span>{option.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default Dropdown;
