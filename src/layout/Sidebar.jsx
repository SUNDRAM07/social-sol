// import { NavLink, useLocation } from "react-router-dom";
// import clsx from "clsx";
// import ThemeToggle from "../components/ThemeToggle.jsx";
// import UserMenu from "../components/UserMenu.jsx";

// const navItems = [
//   { to: "/dashboard", label: "Dashboard", icon: "home" },
//   { to: "/create", label: "Create Campaign", icon: "plus" },
//   { to: "/campaigns", label: "My Campaigns", icon: "folder" },
//   { to: "/analytics", label: "Analytics", icon: "chart" },
//   { to: "/idea-generator", label: "Idea Generator", icon: "lightbulb" },
//   { to: "/settings", label: "Settings", icon: "gear" },
//   { to: "/help-support", label: "Help & Support", icon: "help" },
// ];

// function Icon({ name, className }) {
//   const base = "w-5 h-5";
//   switch (name) {
//     case "home":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1v-10.5z" />
//         </svg>
//       );
//     case "plus":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <path d="M12 5v14M5 12h14" />
//         </svg>
//       );
//     case "folder":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
//         </svg>
//       );
//     case "chart":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <path d="M3 3v18h18" />
//           <path d="M7 15v-4M12 19V8M17 19v-8" />
//         </svg>
//       );
//     case "gear":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
//           <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82L4.21 6.4a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V2a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c0 .66.39 1.26 1 1.51.18.07.37.1.56.1H21a2 2 0 1 1 0 4h-.09c-.19 0-.38.03-.56.1-.61.25-1 .85-1 1.51z" />
//         </svg>
//       );
//     case "lightbulb":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <path d="M9 21H15" />
//           <path d="M12 17C15.866 17 19 13.866 19 10C19 6.134 15.866 3 12 3C8.134 3 5 6.134 5 10C5 13.866 8.134 17 12 17Z" />
//           <path d="M12 17V21" />
//         </svg>
//       );
//     case "dollar":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <line x1="12" y1="1" x2="12" y2="23" />
//           <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
//         </svg>
//       );
//     case "help":
//       return (
//         <svg
//           className={clsx(base, className)}
//           viewBox="0 0 24 24"
//           fill="none"
//           stroke="currentColor"
//           strokeWidth="2"
//         >
//           <circle cx="12" cy="12" r="10" />
//           <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
//           <path d="M12 17h.01" />
//         </svg>
//       );
//     default:
//       return null;
//   }
// }

// function Sidebar() {
//   const { pathname } = useLocation();
//   return (
//     <aside className="fixed left-0 top-0 h-full w-[280px] glass-hover flex flex-col z-20 shadow-lg">
//       {/* Header with Logo and Theme Toggle */}
//       <div className="h-20 flex items-center justify-between px-6 py-4 relative">
//         <div className="absolute inset-0 bg-gradient-primary opacity-20 rounded-t-3xl blur-sm text-black"></div>
//         <img
//           src="/agent-anywhere-logo.png"
//           alt="Agent Anywhere"
//           className="h-10 w-auto relative z-10 drop-shadow-lg text-black"
//         />
//         <ThemeToggle />
//       </div>

//       {/* Social Media Agent Section */}
//       <div className="h-20 flex items-center px-6 relative">
//         <div className="flex items-center gap-3">
//           <div className="relative">
//             <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 via-pink-500 to-blue-500 flex items-center justify-center shadow-lg ring-2 ring-white/20 backdrop-blur-sm">
//               <span className="text-white font-bold text-sm">AA</span>
//             </div>
//             <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white animate-pulse"></div>
//           </div>
//           <div className="flex flex-col">
//             <span className="font-extrabold text-lg gradient-primary-text">Social Media</span>
//             <span className="font-medium text-sm gradient-primary-text opacity-85">Agent</span>
//           </div>
//         </div>
//       </div>
//       <nav className="flex-1 overflow-y-auto py-6">
//         <ul className="px-4 space-y-2">
//           {navItems.map((item) => (
//             <li key={item.to}>
//               <NavLink
//                 to={item.to}
//                 className={({ isActive }) =>
//                   clsx(
//                     "flex items-center gap-4 px-4 py-3 rounded-2xl text-sm font-medium transition-all duration-300 group",
//                     isActive || pathname.startsWith(item.to)
//                       ? "bg-gradient-primary text-black shadow-lg scale-105"
//                       : "text-black/90 hover:bg-white/10 hover:text-black hover:scale-102 backdrop-blur-sm"
//                   )
//                 }
//               >
//                 <Icon
//                   name={item.icon}
//                   className={clsx(
//                     "w-5 h-5 transition-colors duration-200",
//                     pathname.startsWith(item.to)
//                       ? "text-black"
//                       : "text-black/70 group-hover:text-black"
//                   )}
//                 />
//                 <span className="font-semibold">{item.label}</span>
//                 {pathname.startsWith(item.to) && (
//                   <div className="ml-auto w-2 h-2 bg-black rounded-full animate-pulse"></div>
//                 )}
//               </NavLink>
//             </li>
//           ))}
//         </ul>
//       </nav>

//       {/* User Profile Section - Bottom of Sidebar */}
//       <div className="p-4 border-t border-white/20">
//         <UserMenu />
//       </div>
//     </aside>
//   );
// }

// export default Sidebar;

import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import ThemeToggle from "../components/ThemeToggle.jsx";
import UserMenu from "../components/UserMenu.jsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: "home" },
  { to: "/create", label: "Create Campaign", icon: "plus" },
  { to: "/campaigns", label: "My Campaigns", icon: "folder" },
  { to: "/analytics", label: "Analytics", icon: "chart" },
  { to: "/idea-generator", label: "Idea Generator", icon: "lightbulb" },
  { to: "/settings", label: "Settings", icon: "gear" },
  { to: "/help-support", label: "Help & Support", icon: "help" },
];

function Icon({ name, className }) {
  const base = "w-5 h-5";
  switch (name) {
    case "home":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1v-10.5z" />
        </svg>
      );
    case "plus":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
      );
    case "folder":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
        </svg>
      );
    case "chart":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 3v18h18" />
          <path d="M7 15v-4M12 19V8M17 19v-8" />
        </svg>
      );
    case "gear":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82L4.21 6.4a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V2a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c0 .66.39 1.26 1 1.51.18.07.37.1.56.1H21a2 2 0 1 1 0 4h-.09c-.19 0-.38.03-.56.1-.61.25-1 .85-1 1.51z" />
        </svg>
      );
    case "lightbulb":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9 21H15" />
          <path d="M12 17C15.866 17 19 13.866 19 10C19 6.134 15.866 3 12 3C8.134 3 5 6.134 5 10C5 13.866 8.134 17 12 17Z" />
          <path d="M12 17V21" />
        </svg>
      );
    case "dollar":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="1" x2="12" y2="23" />
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      );
    case "help":
      return (
        <svg className={clsx(base, className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
          <path d="M12 17h.01" />
        </svg>
      );
    default:
      return null;
  }
}

function Sidebar() {
  const { pathname } = useLocation();
  return (
    <aside className="fixed left-0 top-0 h-full w-[280px] glass-hover flex flex-col z-20 shadow-lg">
      {/* Header with Logo and Theme Toggle */}
      <div className="h-20 flex items-center justify-center px-6 py-4 relative">
        <div className="absolute inset-0 bg-gradient-primary opacity-20 rounded-t-3xl blur-sm text-black"></div>
        <img
          src="/socialanywhere/agent-anywhere-logo-light.png"
          alt="Agent Anywhere"
          className="h-25 max-h-25 w-auto mx-auto object-contain relative z-10 drop-shadow-lg text-black"
          // className="h-2 w-auto relative z-10 drop-shadow-lg text-black" // ← updated h-8 for smaller logo
        />
      </div>

      {/* Social Media Agent Section (NO AA ICON, TEXT LEFT, TOGGLE RIGHT) */}
      <div className="h-20 flex items-center justify-between px-6 relative">
        <div className="flex flex-col">
          <span className="font-extrabold text-lg gradient-primary-text">Social Media</span>
          <span className="font-medium text-sm gradient-primary-text opacity-85">Agent</span>
        </div>
        <ThemeToggle />
      </div>

      <nav className="flex-1 overflow-y-auto py-6">
        <ul className="px-4 space-y-2">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-4 px-4 py-3 rounded-2xl text-sm font-medium transition-all duration-300 group",
                    isActive || pathname.startsWith(item.to)
                      ? "bg-gradient-primary text-black shadow-lg scale-105"
                      : "text-black/90 hover:bg-white/10 hover:text-black hover:scale-102 backdrop-blur-sm"
                  )
                }
              >
                <Icon
                  name={item.icon}
                  className={clsx(
                    "w-5 h-5 transition-colors duration-200",
                    pathname.startsWith(item.to)
                      ? "text-black"
                      : "text-black/70 group-hover:text-black"
                  )}
                />
                <span className="font-semibold">{item.label}</span>
                {pathname.startsWith(item.to) && (
                  <div className="ml-auto w-2 h-2 bg-black rounded-full animate-pulse"></div>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* User Profile Section - Bottom of Sidebar */}
      <div className="p-4 border-t border-white/20">
        <UserMenu />
      </div>
    </aside>
  );
}

export default Sidebar;
