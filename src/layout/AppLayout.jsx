import Sidebar from "./Sidebar.jsx";
import Footer from "../components/ui/Footer.jsx";
import CalendarPicker from "../components/ui/CalendarPicker.jsx";
import WalletConnectionBanner from "../components/wallet/WalletConnectionBanner.jsx";

function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main id="main" className="flex-1 ml-[280px] relative" role="main">
        {/* Wallet connection prompt banner */}
        <WalletConnectionBanner />
        
        <div className="max-w-screen-2xl mx-auto px-6 lg:px-8 py-6">

          {/* Glass morphism content wrapper */}
          <div className="glass rounded-3xl p-6 md:p-8 min-h-[calc(100vh-8rem)] animate-slide-in flex flex-col">
            <div className="flex-1">
              {children}
            </div>
            <Footer />
          </div>
        </div>
      </main>
    </div>
  );
}

export default AppLayout;


