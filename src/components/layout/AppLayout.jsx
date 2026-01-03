import React from 'react';
import { ToastProvider } from '../ui/Toast.jsx';
import AppSidebar from './AppSidebar';
import AppTopbar from './AppTopbar';

export default function AppLayout({ children }) {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] relative">
        {/* Background decoration */}
        <div className="fixed inset-0 -z-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-purple-400/10 to-pink-400/10 rounded-full blur-3xl"></div>
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-indigo-400/10 to-blue-400/10 rounded-full blur-3xl"></div>
        </div>
        
        <div className="min-h-screen grid grid-cols-12 relative z-0">
          <aside className="hidden lg:block col-span-3 xl:col-span-2 border-r border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-sm">
            <div className="h-full sticky top-0 p-4">
              <AppSidebar />
            </div>
          </aside>
          <main className="col-span-12 lg:col-span-9 xl:col-span-10">
            <div className="sticky top-0 z-30 bg-[var(--surface)]/80 backdrop-blur-sm border-b border-[var(--border)]">
              <AppTopbar />
            </div>
            <div className="px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-screen-2xl mx-auto page-shell">
              {children}
            </div>
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
