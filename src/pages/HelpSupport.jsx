import { useState } from "react";
import { MessageCircle, Mail, Phone, Book, Video, FileCode, Search } from "lucide-react";

export default function HelpSupport() {
  const [activeIndex, setActiveIndex] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  const faqs = [
    {
      question: "How do I connect my social media accounts?",
      answer:
        "To connect your social media accounts, navigate to Settings > Integrations and follow the authentication process for each platform you want to connect.",
    },
    {
      question: "Can I schedule posts to multiple platforms at once?",
      answer:
        "Yes, you can schedule posts to multiple platforms simultaneously. When creating a campaign, simply select all the platforms you want to post to.",
    },
    {
      question: "How does the AI content generator work?",
      answer:
        "Our AI content generator analyzes your product description, target audience, and campaign objectives to create personalized social media posts optimized for engagement.",
    },
    {
      question: "What analytics are available?",
      answer:
        "You can track engagement metrics, reach, impressions, click-through rates, and audience demographics for all your campaigns in the Analytics dashboard.",
    },
    {
      question: "Is there a limit to how many posts I can schedule?",
      answer:
        "The number of posts you can schedule depends on your subscription plan. Check your plan details in Settings > Billing for more information.",
    },
    {
      question: "Can I collaborate with team members?",
      answer:
        "Yes, team collaboration features are available on Business and Enterprise plans. You can invite team members and assign different roles and permissions.",
    },
  ];

  const toggleFAQ = (index) => {
    setActiveIndex(activeIndex === index ? null : index);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    alert("Your message has been sent!");
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[var(--text)] mb-2">Help & Support</h1>
        <p className="text-[var(--text-muted)]">
          Find answers to common questions or get in touch with our team
        </p>
      </div>

      {/* Search Bar */}
      <div className="mb-8">
        <div className="relative max-w-3xl">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-[var(--text-muted)] w-5 h-5" />
          <input
            type="text"
            placeholder="Search for help..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-4 bg-[var(--surface)] border border-[var(--border)] rounded-xl text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Support Cards and Resources Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-12">
        {/* Support Cards - 3 columns */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Live Chat Card */}
          <div className="bg-blue-50 dark:bg-blue-950/20 rounded-2xl p-5 flex flex-col items-center justify-center text-center aspect-square">
            <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center mb-3">
              <MessageCircle className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-base font-semibold text-[var(--text)] mb-1">Live Chat</h3>
            <p className="text-xs text-[var(--text-muted)] mb-3">Get instant help</p>
            <button className="bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm">
              Start Chat
            </button>
          </div>

          {/* Email Support Card */}
          <div className="bg-purple-50 dark:bg-purple-950/20 rounded-2xl p-5 flex flex-col items-center justify-center text-center aspect-square">
            <div className="w-14 h-14 bg-purple-600 rounded-2xl flex items-center justify-center mb-3">
              <Mail className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-base font-semibold text-[var(--text)] mb-1">Email Support</h3>
            <p className="text-xs text-[var(--text-muted)] mb-3">Response in 24h</p>
            <button className="bg-purple-600 text-white px-5 py-2 rounded-lg hover:bg-purple-700 transition-colors font-medium text-sm">
              Send Email
            </button>
          </div>

          {/* Phone Support Card */}
          <div className="bg-pink-50 dark:bg-pink-950/20 rounded-2xl p-5 flex flex-col items-center justify-center text-center aspect-square">
            <div className="w-14 h-14 bg-pink-600 rounded-2xl flex items-center justify-center mb-3">
              <Phone className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-base font-semibold text-[var(--text)] mb-1">Phone Support</h3>
            <p className="text-xs text-[var(--text-muted)] mb-3">Mon-Fri 9am-6pm</p>
            <button className="bg-pink-600 text-white px-5 py-2 rounded-lg hover:bg-pink-700 transition-colors font-medium text-sm">
              Call Us
            </button>
          </div>
        </div>

        {/* Resources Section - 1 column */}
        <div className="lg:col-span-1">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-5 h-full">
            <h2 className="text-lg font-semibold text-[var(--text)] mb-5">Resources</h2>
            <div className="space-y-3">
              <a href="#" className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group">
                <div className="w-11 h-11 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Book className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sm text-[var(--text)] group-hover:text-blue-600 transition-colors">
                    Documentation
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] truncate">Comprehensive guides and tutorials</p>
                </div>
              </a>

              <a href="#" className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group">
                <div className="w-11 h-11 bg-purple-600 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Video className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sm text-[var(--text)] group-hover:text-purple-600 transition-colors">
                    Video Tutorials
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] truncate">Step-by-step video guides</p>
                </div>
              </a>

              <a href="#" className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group">
                <div className="w-11 h-11 bg-pink-600 rounded-xl flex items-center justify-center flex-shrink-0">
                  <FileCode className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sm text-[var(--text)] group-hover:text-pink-600 transition-colors">
                    API Documentation
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] truncate">For developers and integrations</p>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Side - FAQs and Contact Form */}
        <div className="lg:col-span-2 space-y-8">
          {/* FAQ Section */}
          <div>
            <h2 className="text-2xl font-semibold text-[var(--text)] mb-6">Frequently Asked Questions</h2>
            <div className="space-y-3">
              {faqs.map((faq, index) => (
                <div
                  key={index}
                  className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden"
                >
                  <button
                    className="w-full flex justify-between items-center p-5 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    onClick={() => toggleFAQ(index)}
                  >
                    <span className="font-medium text-[var(--text)] pr-4">{faq.question}</span>
                    <span className="text-[var(--text)] text-xl flex-shrink-0">
                      {activeIndex === index ? "−" : "+"}
                    </span>
                  </button>
                  {activeIndex === index && (
                    <div className="px-5 pb-5 text-[var(--text-muted)] border-t border-[var(--border)] pt-4">
                      {faq.answer}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Contact Form */}
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-[var(--text)] mb-6">Send us a message</h2>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium mb-2 text-[var(--text)]">
                    Name
                  </label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    required
                    placeholder="Your name"
                    className="w-full border border-[var(--border)] rounded-lg px-4 py-3 bg-[var(--surface)] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all"
                  />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium mb-2 text-[var(--text)]">
                    Email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    placeholder="your@email.com"
                    className="w-full border border-[var(--border)] rounded-lg px-4 py-3 bg-[var(--surface)] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="subject" className="block text-sm font-medium mb-2 text-[var(--text)]">
                  Subject
                </label>
                <input
                  id="subject"
                  name="subject"
                  type="text"
                  required
                  placeholder="How can we help?"
                  className="w-full border border-[var(--border)] rounded-lg px-4 py-3 bg-[var(--surface)] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all"
                />
              </div>
              <div>
                <label htmlFor="message" className="block text-sm font-medium mb-2 text-[var(--text)]">
                  Message
                </label>
                <textarea
                  id="message"
                  name="message"
                  rows="5"
                  required
                  placeholder="Describe your issue or question..."
                  className="w-full border border-[var(--border)] rounded-lg px-4 py-3 bg-[var(--surface)] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all resize-none"
                ></textarea>
              </div>
              <button
                type="submit"
                className="bg-purple-600 text-white px-8 py-3 rounded-lg hover:bg-purple-700 transition-colors font-medium"
              >
                Send Message
              </button>
            </form>
          </div>
        </div>

        {/* Right Side - Contact Info */}
        <div className="space-y-8">
          {/* Contact Information */}
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-[var(--text)] mb-6">Contact Information</h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-purple-600" />
                <span className="text-[var(--text)]">support@agentanywhere.ai</span>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="w-5 h-5 text-purple-600" />
                <span className="text-[var(--text)]">+1 (555) 123-4567</span>
              </div>
              <div className="flex items-center gap-3">
                <MessageCircle className="w-5 h-5 text-purple-600" />
                <span className="text-[var(--text)]">Live chat available 24/7</span>
              </div>
            </div>

            {/* System Status */}
            <div className="mt-6 pt-6 border-t border-[var(--border)]">
              <h3 className="font-semibold text-[var(--text)] mb-3">System Status</h3>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-[var(--text)]">All systems operational</span>
              </div>
              <a href="#" className="text-purple-600 hover:text-purple-700 text-sm mt-2 inline-block">
                View status page →
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
