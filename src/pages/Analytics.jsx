import { useState, useEffect, useRef } from "react";
import Card from "../components/ui/Card.jsx";
import Dropdown from "../components/ui/Dropdown.jsx";
import { apiFetch } from "../lib/api.js";

const createEmptyAnalytics = () => ({
  overview: {
    totals: {
      followers: 0,
      impressions: 0,
      reach: 0,
      engagement_rate: 0,
      best_post: null,
    },
    metrics_available: false,
    configured: false,
  },
  followers: { followers: 0, configured: false },
  demographics: {},
  posts: { posts: [], configured: false },
  bestPost: { post: {}, configured: false },
  worstPost: { post: {}, configured: false },
  status: { configured: false, account_info: {}, summary: {} },
});

// WebSocket real-time updates
const WS_PATH =
  typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "ws://localhost:8000/ws/analytics"
    : `${
        typeof window !== "undefined"
          ? window.location.protocol.replace("http", "ws")
          : "ws:"
      }//${typeof window !== "undefined" ? window.location.host : ""}/ws/analytics`;

function Analytics() {
  const [analyticsData, setAnalyticsData] = useState(createEmptyAnalytics);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isConfigured, setIsConfigured] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState("all");
  const [selectedCampaign, setSelectedCampaign] = useState("all");
  const [connectedAccounts, setConnectedAccounts] = useState([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [selectedAccountId, setSelectedAccountId] = useState(null);

  const platformRequiresExplicitAccount = (platform) => platform === "instagram" || platform === "twitter";

  const withAccountParam = (path) => {
    if (!selectedAccountId || selectedPlatform === "all") return path;
    const separator = path.includes("?") ? "&" : "?";
    return `${path}${separator}account_id=${encodeURIComponent(selectedAccountId)}`;
  };

  // Platform options for dropdown
  const platformOptions = [
    {
      value: "all",
      label: "All Platforms",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
        </svg>
      ),
    },
    {
      value: "facebook",
      label: "Facebook",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
        </svg>
      ),
    },
    {
      value: "instagram",
      label: "Instagram",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
        </svg>
      ),
    },
    {
      value: "twitter",
      label: "Twitter",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
        </svg>
      ),
    },
    {
      value: "reddit",
      label: "Reddit",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701z" />
        </svg>
      ),
    },
  ];

  // Platform-specific campaign options
  const getCampaignOptions = (platform) => {
    const baseOptions = [
      {
        value: "all",
        label: "All Campaigns",
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
        ),
      },
    ];

    switch (platform) {
      case "facebook":
        return [
          ...baseOptions,
          {
            value: "fifa_world_cup",
            label: "FIFA World Cup 2026",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ),
          },
          {
            value: "office_behind_scenes",
            label: "Office Behind Scenes",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            ),
          },
        ];
      case "instagram":
        return [
          ...baseOptions,
          {
            value: "lifestyle_brand",
            label: "Lifestyle Brand",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            ),
          },
          {
            value: "visual_storytelling",
            label: "Visual Storytelling",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            ),
          },
        ];
      case "twitter":
        return [
          ...baseOptions,
          {
            value: "product_launch",
            label: "Product Launch",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
            ),
          },
          {
            value: "startup_lessons",
            label: "Startup Lessons Thread",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clipRule="evenodd" />
              </svg>
            ),
          },
        ];
      case "reddit":
        return [
          ...baseOptions,
          {
            value: "nike_sale",
            label: "Nike Sale Alert",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
              </svg>
            ),
          },
          {
            value: "screen_time_til",
            label: "Screen Time TIL",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            ),
          },
        ];
      case "all":
      default:
        return [
          ...baseOptions,
          {
            value: "cross_platform",
            label: "Cross-Platform Campaign",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
              </svg>
            ),
          },
        ];
    }
  };

  const campaignOptions = getCampaignOptions(selectedPlatform);

  // Reset campaign selection when platform changes
  useEffect(() => {
    setSelectedCampaign("all");
  }, [selectedPlatform]);

  // WebSocket connection for real-time analytics updates
  const wsRef = useRef(null);
  useEffect(() => {
    const ws = new WebSocket(WS_PATH);
    wsRef.current = ws;

    ws.addEventListener("open", () => {
      try {
        ws.send("ping");
      } catch {}
    });

    ws.addEventListener("message", (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        if (payload.type === "snapshot" && payload.overview) {
          setAnalyticsData((prev) => ({
            ...prev,
            overview: payload.overview.data || payload.overview,
          }));
        }
      } catch (e) {
        console.warn("WS analytics parse error", e);
      }
    });

    ws.addEventListener("close", () => {
      setTimeout(() => {
        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED)
          loadAnalyticsData();
      }, 2000);
    });

    return () => {
      try {
        ws.close();
      } catch {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlatform]);

  // ---------- TRANSFORMERS ----------

  // Twitter transformer retained from original
  const transformTwitterData = (accountInfo, accountAnalytics, myTweets) => {
    const accRaw = accountInfo?.account || accountInfo?.user || accountInfo?.data || {};
    const followers =
      accRaw.followers_count || accRaw.public_metrics?.followers_count || 0;

    const raw = (myTweets && (myTweets.tweets || myTweets.posts || myTweets.data)) || [];
    const tweets = raw.map((t) => {
      const pm = t.public_metrics || {};
      return {
        id: t.id,
        text: t.text || t.message || t.full_text || "",
        created_at: t.created_at || t.created_time || t.timestamp || null,
        like_count: t.like_count ?? pm.like_count ?? t.reactions?.like ?? 0,
        retweet_count:
          t.retweet_count ?? pm.retweet_count ?? t.reactions?.retweet ?? 0,
        reply_count: t.reply_count ?? pm.reply_count ?? t.reactions?.reply ?? 0,
        impression_count:
          t.impression_count ?? pm.impression_count ?? t.impressions ?? 0,
        url: t.url || null,
      };
    });

    const totalImpressions = tweets.reduce((s, t) => s + (t.impression_count || 0), 0);
    const totalLikes = tweets.reduce((s, t) => s + (t.like_count || 0), 0);
    const totalRetweets = tweets.reduce((s, t) => s + (t.retweet_count || 0), 0);
    const totalReplies = tweets.reduce((s, t) => s + (t.reply_count || 0), 0);
    const avgImpressions = tweets.length ? Math.round(totalImpressions / tweets.length) : 0;

    const topTweets = [...tweets]
      .sort(
        (a, b) =>
          (b.like_count + b.retweet_count + b.reply_count) -
          (a.like_count + a.retweet_count + a.reply_count)
      )
      .slice(0, 5);

    const formattedTweets = tweets.map((tweet) => ({
      id: tweet.id,
      message: tweet.text,
      created_time: tweet.created_at,
      reach: tweet.impression_count || 0,
      impressions: tweet.impression_count || 0,
      engaged_users:
        (tweet.like_count || 0) + (tweet.retweet_count || 0) + (tweet.reply_count || 0),
      engagement_rate: tweet.impression_count
        ? (tweet.like_count + tweet.retweet_count + tweet.reply_count) /
          tweet.impression_count
        : 0,
      reactions: {
        like: tweet.like_count || 0,
        retweet: tweet.retweet_count || 0,
        reply: tweet.reply_count || 0,
      },
      url: tweet.url,
    }));

    return {
      overview: {
        totals: {
          followers,
          impressions: totalImpressions,
          reach: totalImpressions,
          engagement_rate: avgImpressions
            ? (totalLikes + totalRetweets + totalReplies) / avgImpressions
            : 0,
          best_post: topTweets[0]?.id || null,
        },
        metrics_available: true,
        configured: !!accountInfo?.success,
      },
      followers: { followers, configured: !!accountInfo?.success },
      demographics: {},
      posts: { posts: formattedTweets, configured: !!myTweets?.success },
      bestPost: {
        post: topTweets[0]
          ? {
              id: topTweets[0].id,
              message: topTweets[0].text,
              reach: topTweets[0].impression_count || 0,
              impressions: topTweets[0].impression_count || 0,
              engaged_users:
                (topTweets[0].like_count || 0) +
                (topTweets[0].retweet_count || 0) +
                (topTweets[0].reply_count || 0),
              engagement_rate: topTweets[0].impression_count
                ? (topTweets[0].like_count +
                    topTweets[0].retweet_count +
                    topTweets[0].reply_count) /
                  topTweets[0].impression_count
                : 0,
            }
          : {},
        configured: !!myTweets?.success,
      },
      worstPost: {
        post: topTweets[topTweets.length - 1] || {},
        configured: !!myTweets?.success,
      },
      status: {
        configured: !!accountInfo?.success,
        account_info: accRaw,
        summary: accountAnalytics || {},
      },
    };
  };

  // Reddit transformer retained from original
  const transformRedditData = (accountInfo, accountAnalytics, myPosts, myComments) => {
    const account = accountInfo.success ? accountInfo.account : {};
    const posts = myPosts.success ? myPosts.posts || [] : [];
    const totalPostScore = posts.reduce((s, p) => s + (p.score || 0), 0);
    const totalPostComments = posts.reduce((s, p) => s + (p.num_comments || 0), 0);
    const mapReddit = (post) => ({
      id: post.id,
      message: post.title || post.selftext || "",
      created_time: post.created_utc ? new Date(post.created_utc * 1000).toISOString() : null,
      reach: post.num_comments || 0, // Comments as reach
      impressions: post.score || 0, // Score/upvotes as impressions
      engaged_users: (post.score || 0) + (post.num_comments || 0), // Score + comments
      engagement_rate: post.score ? ((post.num_comments || 0) / post.score) * 100 : 0,
      reactions: { upvote: post.score || 0, downvote: 0, comment: post.num_comments || 0 },
      subreddit: post.subreddit,
      permalink: post.permalink,
      url: post.url,
    });
    const formatted = posts.map(mapReddit);
    const best = [...posts].sort((a, b) => (b.score || 0) - (a.score || 0))[0];
    const worst = [...posts].sort((a, b) => (a.score || 0) - (b.score || 0))[0];
    return {
      overview: {
        totals: {
          followers: account.followers_count || 0,
          impressions: totalPostScore,
          reach: totalPostComments,
          engagement_rate:
            totalPostComments > 0
              ? (totalPostComments / Math.max(totalPostScore, 1)) * 100
              : 0,
          best_post: best?.id || null,
        },
        metrics_available: true,
        configured: accountInfo.success,
      },
      followers: { followers: account.followers_count || 0, configured: accountInfo.success },
      demographics: {
        by_subreddit: posts.reduce((m, p) => ((m[p.subreddit] = (m[p.subreddit] || 0) + 1), m), {}),
      },
      posts: { posts: formatted, configured: myPosts.success },
      bestPost: { post: best ? mapReddit(best) : {}, configured: myPosts.success },
      worstPost: { post: worst ? mapReddit(worst) : {}, configured: myPosts.success },
      status: { configured: accountInfo.success, account_info: account, summary: accountAnalytics || {} },
    };
  };

  // Instagram transformer retained from original
  const transformInstagramData = (accountInfo, accountAnalytics, mediaList) => {
    const account = accountInfo.success ? accountInfo.account : {};
    const analytics = accountAnalytics.success ? (accountAnalytics.analytics || accountAnalytics) : {};
    const media = mediaList.success ? mediaList.media || [] : [];

    const mapInstagram = (post) => ({
      id: post.id,
      message: post.caption || "",
      created_time: post.timestamp || null,
      reach: post.total_engagement || 0,
      impressions: post.total_engagement || 0,
      engaged_users: post.comments_count || 0,
      engagement_rate: post.like_count > 0 ? (post.comments_count / post.like_count) * 100 : 0,
      reactions: { like: post.like_count || 0, comment: post.comments_count || 0 },
      media_type: post.media_type,
      media_url: post.media_url,
      permalink: post.permalink,
    });

    const formatted = media.map(mapInstagram);
    const best = [...media].sort((a, b) => (b.total_engagement || 0) - (a.total_engagement || 0))[0];
    const worst = [...media].sort((a, b) => (a.total_engagement || 0) - (b.total_engagement || 0))[0];

    const summary = analytics.summary || accountAnalytics.summary || {};
    const mediaTypes = analytics.media_types || accountAnalytics.media_types || {};

    return {
      overview: {
        totals: {
          followers: account.followers_count || 0,
          impressions: summary.total_engagement || summary.total_impressions || 0,
          reach: summary.total_engagement || summary.total_reach || 0,
          engagement_rate: summary.avg_engagement || summary.overall_engagement_rate || 0,
          best_post: best?.id || null,
        },
        metrics_available: true,
        configured: accountInfo.success,
      },
      followers: { followers: account.followers_count || 0, configured: accountInfo.success },
      demographics: {
        by_media_type: mediaTypes,
        by_engagement: formatted.reduce((m, p) => {
          const range = p.total_engagement > 100 ? "high" : p.total_engagement > 50 ? "medium" : "low";
          m[range] = (m[range] || 0) + 1;
          return m;
        }, {}),
      },
      posts: { posts: formatted, configured: mediaList.success },
      bestPost: { post: best ? mapInstagram(best) : {}, configured: mediaList.success },
      worstPost: { post: worst ? mapInstagram(worst) : {}, configured: mediaList.success },
      status: { configured: accountInfo.success, account_info: account, summary: summary },
    };
  };

  const findInsightValue = (post, metricName) => {
    if (!post) return 0;
    const insightArray = Array.isArray(post.insights?.data)
      ? post.insights.data
      : Array.isArray(post.insights)
      ? post.insights
      : [];
    const metric = insightArray.find((item) => item.name === metricName);
    if (!metric) return 0;
    const values = metric.values || [];
    if (!values.length) return 0;
    const lastValue = values[values.length - 1];
    return typeof lastValue.value === "number" ? lastValue.value : Number(lastValue.value) || 0;
  };

  const mapFacebookAnalyticsPost = (post) => {
    const likes = post?.likes?.summary?.total_count ?? post?.reactions_count ?? 0;
    const comments = post?.comments?.summary?.total_count ?? post?.comments_count ?? 0;
    const shares = post?.shares?.count ?? post?.shares_count ?? 0;
    const impressions = findInsightValue(post, "post_impressions");
    const reach = findInsightValue(post, "post_reach") || impressions;
    const engagedUsers = findInsightValue(post, "post_engaged_users") || post?.engaged_users || likes + comments + shares;

    return {
      id: post?.id,
      message: post?.message || post?.caption || post?.story || "",
      created_time: post?.created_time || null,
      reach,
      impressions,
      engaged_users: engagedUsers,
      engagement_rate: impressions ? engagedUsers / impressions : 0,
      reactions: {
        like: likes,
        comment: comments,
        share: shares,
      },
      permalink: post?.permalink_url || post?.permalink || post?.link || null,
    };
  };

  const normalizeFacebookAnalytics = (payload) => {
    const posts = Array.isArray(payload?.posts) ? payload.posts.map(mapFacebookAnalyticsPost) : [];
    const sortedByEngagement = [...posts].sort(
      (a, b) => (b.engaged_users || 0) - (a.engaged_users || 0)
    );
    const bestPostFromPayload = payload?.best_post ? mapFacebookAnalyticsPost(payload.best_post) : null;
    const bestPost = bestPostFromPayload?.id ? bestPostFromPayload : sortedByEngagement[0] || {};
    const worstPost = sortedByEngagement[sortedByEngagement.length - 1] || {};
    const totalImpressions =
      payload?.totals?.impressions ??
      posts.reduce((sum, post) => sum + (post.impressions || 0), 0);
    const totalReach =
      payload?.totals?.reach ??
      posts.reduce((sum, post) => sum + (post.reach || post.impressions || 0), 0);
    const followers = payload?.totals?.followers ?? 0;

    return {
      overview: {
        totals: {
          followers,
          impressions: totalImpressions,
          reach: totalReach,
          engagement_rate: payload?.totals?.engagement_rate ?? (totalReach ? totalReach / (posts.length || 1) : 0),
          best_post: payload?.totals?.best_post || bestPost?.id || null,
        },
        metrics_available: payload?.metrics_available ?? posts.length > 0,
        configured: true,
      },
      followers: { followers, configured: true },
      demographics: {
        by_country: payload?.demographics?.by_country || {},
        by_age_gender: payload?.demographics?.by_age_gender || {},
      },
      posts: { posts, configured: posts.length > 0 },
      bestPost: { post: bestPost, configured: Object.keys(bestPost || {}).length > 0 },
      worstPost: { post: worstPost, configured: Object.keys(worstPost || {}).length > 0 },
      status: { configured: true, account_info: payload?.page || {}, summary: payload?.totals || {} },
    };
  };

  const fetchFacebookAnalytics = async () => {
    const response = await apiFetch(withAccountParam("/api/facebook/analytics"));
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || "Failed to load Facebook analytics");
    }
    return normalizeFacebookAnalytics(data);
  };

  // Helper to ensure we have best/worst posts
  const ensureBestWorst = (data) => {
    try {
      const postsArr = data?.posts?.posts || [];
      const hasBest = data?.bestPost?.post && Object.keys(data.bestPost.post).length > 0;
      const hasWorst = data?.worstPost?.post && Object.keys(data.worstPost.post).length > 0;
      if ((!hasBest || !hasWorst) && postsArr.length > 0) {
        const sorted = [...postsArr].sort((a, b) => {
          const ae = (a.engaged_users || 0) + (a.impressions || a.reach || 0) * 0.001;
          const be = (b.engaged_users || 0) + (b.impressions || b.reach || 0) * 0.001;
          return be - ae;
        });
        const best = sorted[0];
        const worst = sorted[sorted.length - 1];
        return {
          ...data,
          bestPost: { post: hasBest ? data.bestPost.post : (best || {}), configured: data.bestPost?.configured ?? true },
          worstPost: { post: hasWorst ? data.worstPost.post : (worst || {}), configured: data.worstPost?.configured ?? true },
        };
      }
    } catch (e) {
      console.warn("ensureBestWorst error", e);
    }
    return data;
  };

  // ---------- LOAD ANALYTICS ----------

  const loadAnalyticsData = async () => {
    setLoading(true);
    setError(null);

    try {
      if (selectedPlatform === "all") {
        setAnalyticsData(createEmptyAnalytics());
        setIsConfigured(false);
        setLoading(false);
        return;
      }

      if (selectedPlatform !== "all" && !accountsLoaded) {
        setLoading(false);
        return;
      }

      const requiresExplicitAccount = platformRequiresExplicitAccount(selectedPlatform);

      // For Instagram, skip early account check - try to load analytics first
      // The account might exist in database even if not in connectedAccounts list
      if (selectedPlatform !== "instagram") {
        if (
          selectedPlatform !== "all" &&
          requiresExplicitAccount &&
          accountsLoaded &&
          connectedAccounts.length === 0
        ) {
          const platformLabel = selectedPlatform.charAt(0).toUpperCase() + selectedPlatform.slice(1);
          setError(`No ${platformLabel} account connected. Please connect an account in Settings.`);
          setAnalyticsData(createEmptyAnalytics());
          setIsConfigured(false);
          setLoading(false);
          return;
        }

        if (
          requiresExplicitAccount &&
          connectedAccounts.length > 0 &&
          !selectedAccountId
        ) {
          setLoading(false);
          return;
        }
      }

      if (selectedPlatform === "instagram") {
        // Wait for accounts to load before checking
        if (!accountsLoaded) {
          setLoading(true);
          return;
        }
        
        // Try to load analytics even if connectedAccounts is empty - the API might still work
        // Only show error if API calls also fail
        try {
          const [accountInfoRes, accountAnalyticsRes, mediaListRes] = await Promise.all([
            apiFetch(withAccountParam("/api/instagram/account/info")).then((r) => r.json()).catch((e) => ({ success: false, error: e.message })),
            apiFetch(withAccountParam("/api/instagram/account/analytics")).then((r) => r.json()).catch((e) => ({ success: false, error: e.message })),
            apiFetch(withAccountParam("/api/instagram/media?limit=25")).then((r) => r.json()).catch((e) => ({ success: false, error: e.message })),
          ]);
          
          // Check if all API calls failed - only then show "no account" error
          const allFailed = !accountInfoRes.success && !accountAnalyticsRes.success && !mediaListRes.success;
          
          // Check for token expiration errors (these should show reconnect message, not "no account")
          const isTokenError = accountInfoRes.error?.error?.code === 190 || 
                               accountInfoRes.error?.error?.type === 'OAuthException' ||
                               accountAnalyticsRes.error?.error?.code === 190 ||
                               accountAnalyticsRes.error?.error?.type === 'OAuthException' ||
                               (typeof accountInfoRes.error === 'string' && accountInfoRes.error.includes('expired')) ||
                               (typeof accountAnalyticsRes.error === 'string' && accountAnalyticsRes.error.includes('expired'));
          
          // Check if API explicitly says "no account" (not just a generic failure)
          const explicitNoAccountError = 
            (typeof accountInfoRes.error === 'string' && accountInfoRes.error.toLowerCase().includes('no account')) ||
            (typeof accountAnalyticsRes.error === 'string' && accountAnalyticsRes.error.toLowerCase().includes('no account')) ||
            (accountInfoRes.error?.error?.message && accountInfoRes.error.error.message.toLowerCase().includes('no account')) ||
            (accountAnalyticsRes.error?.error?.message && accountAnalyticsRes.error.error.message.toLowerCase().includes('no account'));
          
          // Only show "no account" error if:
          // 1. API explicitly says "no account" OR
          // 2. (No accounts in connectedAccounts list AND all API calls failed AND it's not a token error)
          // This allows analytics to load even if connectedAccounts list is empty (account might exist in DB)
          if (explicitNoAccountError || (connectedAccounts.length === 0 && allFailed && !isTokenError)) {
            setError("No Instagram account connected. Please connect an Instagram account in Settings.");
            setAnalyticsData(createEmptyAnalytics());
            setIsConfigured(false);
            setLoading(false);
            return;
          }

          if (accountInfoRes.success && accountAnalyticsRes.success) {
            const instagramData = transformInstagramData(accountInfoRes, accountAnalyticsRes, mediaListRes);
            setAnalyticsData(ensureBestWorst(instagramData));
            setIsConfigured(true);
          } else {
            // Properly extract error message from response objects
            let errorMsg = "Failed to fetch Instagram analytics";
            let needsReconnect = false;
            
            // Check for token expiration errors
            const checkForTokenError = (errorObj) => {
              if (typeof errorObj === 'object' && errorObj !== null) {
                // Handle nested error structure: {error: {message: "...", code: 190, type: "OAuthException"}}
                if (errorObj.error) {
                  const err = errorObj.error;
                  if (err.code === 190 || err.type === 'OAuthException' || 
                      (typeof err.message === 'string' && (err.message.includes('expired') || err.message.includes('Session has expired')))) {
                    needsReconnect = true;
                    return "Your Instagram access token has expired. Please reconnect your Instagram account in Settings.";
                  }
                  if (err.message) {
                    return err.message;
                  }
                }
                // Handle direct error object
                if (errorObj.code === 190 || errorObj.type === 'OAuthException' || 
                    (typeof errorObj.message === 'string' && (errorObj.message.includes('expired') || errorObj.message.includes('Session has expired')))) {
                  needsReconnect = true;
                  return "Your Instagram access token has expired. Please reconnect your Instagram account in Settings.";
                }
                if (errorObj.message) {
                  return errorObj.message;
                }
              }
              // Handle string errors
              if (typeof errorObj === 'string' && (errorObj.includes('expired') || errorObj.includes('Session has expired'))) {
                needsReconnect = true;
                return "Your Instagram access token has expired. Please reconnect your Instagram account in Settings.";
              }
              return null;
            };
            
            const tokenError = checkForTokenError(accountInfoRes.error) || checkForTokenError(accountAnalyticsRes.error);
            if (tokenError) {
              errorMsg = tokenError;
            } else if (accountInfoRes.error) {
              const err = accountInfoRes.error;
              if (typeof err === 'object' && err.error?.message) {
                errorMsg = err.error.message;
              } else if (typeof err === 'object' && err.message) {
                errorMsg = err.message;
              } else {
                errorMsg = typeof err === 'string' ? err : JSON.stringify(err);
              }
            } else if (accountAnalyticsRes.error) {
              const err = accountAnalyticsRes.error;
              if (typeof err === 'object' && err.error?.message) {
                errorMsg = err.error.message;
              } else if (typeof err === 'object' && err.message) {
                errorMsg = err.message;
              } else {
                errorMsg = typeof err === 'string' ? err : JSON.stringify(err);
              }
            } else if (accountInfoRes.message) {
              errorMsg = typeof accountInfoRes.message === 'string' ? accountInfoRes.message : JSON.stringify(accountInfoRes.message);
            } else if (accountAnalyticsRes.message) {
              errorMsg = typeof accountAnalyticsRes.message === 'string' ? accountAnalyticsRes.message : JSON.stringify(accountAnalyticsRes.message);
            }
            
            setError(needsReconnect ? errorMsg : `Error loading Instagram analytics: ${errorMsg}.`);
            if (accountInfoRes.success || accountAnalyticsRes.success || mediaListRes.success) {
              const partialData = transformInstagramData(
                accountInfoRes.success ? accountInfoRes : { success: false, account: {} },
                accountAnalyticsRes.success ? accountAnalyticsRes : { success: false },
                mediaListRes.success ? mediaListRes : { success: false, media: [] }
              );
              setAnalyticsData(ensureBestWorst(partialData));
              setIsConfigured(accountInfoRes.success && accountAnalyticsRes.success);
            } else {
              setAnalyticsData(createEmptyAnalytics());
              setIsConfigured(false);
            }
          }
        } catch (e) {
          console.error("Instagram analytics error:", e);
          const errorMsg = e?.message || (typeof e === 'object' ? JSON.stringify(e) : String(e));
          setError(`Error loading Instagram analytics: ${errorMsg}`);
          setAnalyticsData(createEmptyAnalytics());
          setIsConfigured(false);
        } finally {
          setLoading(false);
        }
        return;
      }

      if (selectedPlatform === "reddit") {
        try {
          const [accountInfo, accountAnalytics, myPosts, myComments] = await Promise.all([
            apiFetch("/api/reddit/account/info").then((r) => r.json()).catch(() => ({ success: false })),
            apiFetch("/api/reddit/account/analytics").then((r) => r.json()).catch(() => ({ success: false })),
            apiFetch("/api/reddit/posts/my?limit=10").then((r) => r.json()).catch(() => ({ success: false })),
            apiFetch("/api/reddit/comments/my?limit=10").then((r) => r.json()).catch(() => ({ success: false })),
          ]);

          const redditHasData =
            accountInfo.success || accountAnalytics.success || myPosts.success || myComments.success;

          if (redditHasData) {
            const rd = transformRedditData(
              accountInfo.success ? accountInfo : { success: false, account: {} },
              accountAnalytics.success ? accountAnalytics : { success: false },
              myPosts.success ? myPosts : { success: false, posts: [] },
              myComments.success ? myComments : { success: false, comments: [] }
            );
            setAnalyticsData(ensureBestWorst(rd));
            setIsConfigured(accountInfo.success && accountAnalytics.success);
            if (!(accountInfo.success && accountAnalytics.success)) {
              setError("Some Reddit metrics are unavailable right now.");
            }
          } else {
            // Check if account is actually connected
            const hasAccount = connectedAccounts && connectedAccounts.length > 0;
            if (hasAccount) {
              setError("Unable to load Reddit analytics. Please try refreshing or check your Reddit account connection.");
            } else {
              setError("Unable to load Reddit analytics. Please connect your Reddit account.");
            }
            setAnalyticsData(createEmptyAnalytics());
            setIsConfigured(false);
          }
        } catch (e) {
          console.error("Reddit analytics error:", e);
          setError(e.message || "Failed to load Reddit analytics");
          setAnalyticsData(createEmptyAnalytics());
          setIsConfigured(false);
        } finally {
          setLoading(false);
        }
        return;
      }

      if (selectedPlatform === "twitter") {
        try {
          const requiresExplicitAccount = platformRequiresExplicitAccount(selectedPlatform);
          const [accountInfo, accountAnalytics, myTweets] = await Promise.all([
            apiFetch(withAccountParam("/api/twitter/account/info")).then((r) => r.json()).catch((e) => ({ success: false, error: e.message })),
            apiFetch(withAccountParam("/api/twitter/account/analytics")).then((r) => r.json()).catch((e) => ({ success: false, error: e.message })),
            apiFetch("/api/twitter/posts/my?limit=10").then((r) => r.json()).catch(() => ({ success: false })),
          ]);

          const twitterHasData = accountInfo.success || accountAnalytics.success || myTweets.success;

          if (twitterHasData) {
            const td = transformTwitterData(
              accountInfo.success ? accountInfo : { success: false, account: {} },
              accountAnalytics.success ? accountAnalytics : { success: false },
              myTweets.success ? myTweets : { success: false, tweets: [] }
            );
            setAnalyticsData(ensureBestWorst(td));
            setIsConfigured(accountInfo.success && accountAnalytics.success);
            if (!(accountInfo.success && accountAnalytics.success)) {
              setError("Some Twitter metrics are unavailable right now.");
            }
          } else {
            setError("Unable to load Twitter analytics. Please connect your Twitter account.");
            setAnalyticsData(createEmptyAnalytics());
            setIsConfigured(false);
          }
        } catch (e) {
          console.error("Twitter analytics error:", e);
          setError(e.message || "Failed to load Twitter analytics");
          setAnalyticsData(createEmptyAnalytics());
          setIsConfigured(false);
        } finally {
          setLoading(false);
        }
        return;
      }

      if (selectedPlatform === "facebook") {
        try {
          const fb = await fetchFacebookAnalytics();
          setAnalyticsData(ensureBestWorst(fb));
          setIsConfigured(true);
        } catch (e) {
          console.error("Facebook analytics error:", e);
          setError(e.message || "Failed to load Facebook analytics");
          setAnalyticsData(createEmptyAnalytics());
          setIsConfigured(false);
        } finally {
          setLoading(false);
        }
        return;
      }

      setAnalyticsData(createEmptyAnalytics());
      setIsConfigured(false);
      setLoading(false);
    } catch (err) {
      console.error("Error loading analytics data:", err);
      setError(err.message || String(err));
      setAnalyticsData(createEmptyAnalytics());
      setIsConfigured(false);
      setLoading(false);
    }
  };

  // refresh helper
  const refreshData = () => {
    loadAnalyticsData();
  };

  // helpers
  const formatNumber = (num) => {
    if (num === null || num === undefined) return "0";
    return Number(num).toLocaleString();
  };
  const safeGet = (obj, path, fallback = "N/A") => {
    try {
      const v = path.split(".").reduce((o, p) => (o ? o[p] : undefined), obj);
      return v !== null && v !== undefined ? v : fallback;
    } catch {
      return fallback;
    }
  };

  // Fetch connected accounts on mount and when platform changes
  useEffect(() => {
    const fetchAccounts = async () => {
      setAccountsLoaded(false);
      try {
        const response = await apiFetch(`/api/social-media/accounts?platform=${selectedPlatform}`);
        const data = await response.json();
        if (data.success && Array.isArray(data.accounts)) {
          // Filter to only show active accounts (defensive filtering)
          const activeAccounts = data.accounts.filter(acc => acc.is_active !== false);
          setConnectedAccounts(activeAccounts);
          setSelectedAccountId((prev) => {
            if (!activeAccounts.length) return null;
            const stillExists = prev && activeAccounts.some((acc) => acc.account_id === prev);
            return stillExists ? prev : activeAccounts[0].account_id;
          });
        } else {
          setConnectedAccounts([]);
          setSelectedAccountId(null);
        }
      } catch (e) {
        console.error("Error fetching connected accounts:", e);
        setConnectedAccounts([]);
        setSelectedAccountId(null);
      } finally {
        setAccountsLoaded(true);
      }
    };
    if (selectedPlatform !== "all") {
      fetchAccounts();
    } else {
      setConnectedAccounts([]);
      setSelectedAccountId(null);
      setAccountsLoaded(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlatform]);

  // initial load
  useEffect(() => {
    // call loadAnalyticsData when platform/account changes
    loadAnalyticsData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlatform, selectedAccountId, accountsLoaded, selectedCampaign]);

  // Render loading / UI (kept original structure)
  if (loading)
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <span className="ml-4 text-gray-600">Loading analytics data...</span>
        </div>
      </div>
    );

  if (selectedPlatform === "all") {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-semibold">Analytics</h1>

          {/* Platform dropdown */}
          <Dropdown options={platformOptions} value={selectedPlatform} onChange={setSelectedPlatform} placeholder="Select Platform" />
        </div>

        {/* Platform Selection Interface */}
        <div className="flex flex-col items-center justify-center py-20">
          <div className="text-center max-w-lg">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Choose a Platform</h2>
            <p className="text-lg text-gray-600 mb-8 leading-relaxed">
              Select a social media platform from the dropdown above to view analytics and performance data.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <button onClick={() => setSelectedPlatform("facebook")} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700 transition-colors duration-200">Facebook</span>
              </button>

              <button onClick={() => setSelectedPlatform("instagram")} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-pink-300 hover:bg-pink-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-pink-700 transition-colors duration-200">Instagram</span>
              </button>

              <button onClick={() => setSelectedPlatform("twitter")} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700 transition-colors duration-200">Twitter</span>
              </button>

              <button onClick={() => setSelectedPlatform("reddit")} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-orange-300 hover:bg-orange-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-orange-600 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.568 8.16c-.169 1.858-.896 3.305-2.189 4.34-.98.78-2.267 1.244-3.768 1.244-2.954 0-5.355-2.401-5.355-5.355 0-.42.048-.83.138-1.224.8.09 1.536.22 2.189.39-.8-.48-1.328-1.24-1.328-2.14 0-.48.12-.93.33-1.32.9.11 1.69.35 2.4.7-.75-.8-1.86-1.3-3.07-1.3-2.33 0-4.22 1.89-4.22 4.22 0 .33.04.65.11.96-3.51-.18-6.62-1.86-8.7-4.42-.36.63-.57 1.36-.57 2.14 0 1.47.75 2.77 1.89 3.53-.7-.02-1.36-.21-1.94-.53v.05c0 2.05 1.46 3.76 3.4 4.15-.36.1-.73.15-1.12.15-.27 0-.54-.03-.8-.08.54 1.69 2.11 2.92 3.97 2.95-1.45 1.14-3.28 1.82-5.27 1.82-.34 0-.68-.02-1.02-.06 1.88 1.21 4.12 1.91 6.52 1.91 7.82 0 12.09-6.48 12.09-12.09 0-.18 0-.37-.01-.56.83-.6 1.55-1.35 2.12-2.2z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-orange-700 transition-colors duration-200">Reddit</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // MAIN dashboard view for a selected platform
  return (
    <div className="space-y-6">
      {/* Enhanced Header */}
      <div className="bg-gradient-to-r from-purple-600 via-blue-600 to-indigo-600 rounded-2xl shadow-xl p-6 mb-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32"></div>
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full -ml-24 -mb-24"></div>
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full backdrop-blur-sm ${isConfigured ? "bg-green-500/20 border border-green-400/30" : "bg-yellow-500/20 border border-yellow-400/30"}`}>
                <div className={`w-2.5 h-2.5 rounded-full ${isConfigured ? "bg-green-400 animate-pulse" : "bg-yellow-400"}`}></div>
                <span className="text-sm font-medium text-white">{isConfigured ? "Live Data" : "No Account Connected"}</span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {connectedAccounts.length > 0 && selectedPlatform !== "all" && (
              <Dropdown
                options={connectedAccounts.map((acc) => ({
                  value: acc.account_id,
                  label: acc.display_name || acc.username || acc.account_id,
                }))}
                value={selectedAccountId}
                onChange={setSelectedAccountId}
                placeholder="Select Account"
              />
            )}

            <Dropdown options={getCampaignOptions(selectedPlatform)} value={selectedCampaign} onChange={setSelectedCampaign} placeholder="Select Campaign" />
            <Dropdown options={platformOptions} value={selectedPlatform} onChange={setSelectedPlatform} placeholder="Select Platform" />
            <button 
              onClick={refreshData} 
              className="px-5 py-2.5 bg-white/20 backdrop-blur-sm text-white rounded-xl hover:bg-white/30 transition-all duration-200 font-medium border border-white/30 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh Data
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-gradient-to-r from-red-50 to-orange-50 border-l-4 border-red-500 rounded-xl p-5 shadow-lg mb-6">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="flex-1">
              <div className="text-red-800 font-semibold mb-1">Error loading analytics</div>
              <div className="text-red-700 text-sm">{error}</div>
              {error.includes("expired") || error.includes("reconnect") ? (
                <div className="mt-3">
                  <a 
                    href="/socialanywhere/settings" 
                    className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
                  >
                    Go to Settings to reconnect your account
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </a>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Metric Cards with Modern Design */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Followers Card */}
        <div className="relative overflow-hidden bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full -ml-12 -mb-12"></div>
          <div className="relative p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div className="text-xs font-medium bg-white/20 px-2 py-1 rounded-full">Followers</div>
            </div>
            <div className="text-4xl font-bold mb-1">{formatNumber(safeGet(analyticsData.followers, "followers", 0))}</div>
            <div className="text-sm text-blue-100">Total page followers</div>
          </div>
        </div>

        {/* Impressions Card */}
        <div className="relative overflow-hidden bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full -ml-12 -mb-12"></div>
          <div className="relative p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <div className="text-xs font-medium bg-white/20 px-2 py-1 rounded-full">Impressions</div>
            </div>
            <div className="text-4xl font-bold mb-1">{formatNumber(safeGet(analyticsData.overview, "totals.impressions", 0))}</div>
            <div className="text-sm text-purple-100">Post impressions</div>
          </div>
        </div>

        {/* Reach Card */}
        <div className="relative overflow-hidden bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full -ml-12 -mb-12"></div>
          <div className="relative p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="text-xs font-medium bg-white/20 px-2 py-1 rounded-full">Reach</div>
            </div>
            <div className="text-4xl font-bold mb-1">{formatNumber(safeGet(analyticsData.overview, "totals.reach", 0))}</div>
            <div className="text-sm text-indigo-100">Total reach</div>
          </div>
        </div>

        {/* Engagement Rate Card */}
        <div className="relative overflow-hidden bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full -ml-12 -mb-12"></div>
          <div className="relative p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <div className="text-xs font-medium bg-white/20 px-2 py-1 rounded-full">Engagement</div>
            </div>
            <div className="text-4xl font-bold mb-1">{formatNumber(safeGet(analyticsData.overview, "totals.engagement_rate", 0))}%</div>
            <div className="text-sm text-emerald-100">Average engagement</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Enhanced Demographics Card */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-shadow duration-300">
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">
                {selectedPlatform === "reddit" ? "Posts by Subreddit" : 
                 selectedPlatform === "twitter" ? "Account Statistics" : 
                 selectedPlatform === "instagram" ? "Content by Type" : 
                 "Audience by Country"}
              </h3>
            </div>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {selectedPlatform === "reddit" ? (
                analyticsData.demographics?.by_subreddit && Object.keys(analyticsData.demographics.by_subreddit).length > 0 ? (
                  Object.entries(analyticsData.demographics.by_subreddit)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 5)
                    .map(([subreddit, count], idx) => (
                      <div key={subreddit} className="flex items-center justify-between p-3 bg-gradient-to-r from-orange-50 to-red-50 rounded-lg border border-orange-100 hover:border-orange-300 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">{idx + 1}</div>
                          <span className="text-gray-800 font-medium">r/{subreddit}</span>
                        </div>
                        <span className="font-bold text-orange-600">{formatNumber(count)} posts</span>
                      </div>
                    ))
                ) : (
                  <div className="text-gray-500 text-center py-8">No subreddit data available</div>
                )
              ) : selectedPlatform === "twitter" ? (
                analyticsData.status?.account_info ? (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg border border-blue-100">
                      <span className="text-gray-700 font-medium">Total Tweets</span>
                      <span className="font-bold text-blue-600">{formatNumber(analyticsData.status.account_info.tweet_count || 0)}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg border border-purple-100">
                      <span className="text-gray-700 font-medium">Following</span>
                      <span className="font-bold text-purple-600">{formatNumber(analyticsData.status.account_info.following_count || 0)}</span>
                    </div>
                    <div className={`flex justify-between items-center p-3 rounded-lg border ${analyticsData.status.account_info.verified ? 'bg-green-50 border-green-100' : 'bg-gray-50 border-gray-100'}`}>
                      <span className="text-gray-700 font-medium">Verified</span>
                      <span className={`font-bold ${analyticsData.status.account_info.verified ? 'text-green-600' : 'text-gray-600'}`}>{analyticsData.status.account_info.verified ? "Yes" : "No"}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-indigo-50 rounded-lg border border-indigo-100">
                      <span className="text-gray-700 font-medium">Username</span>
                      <span className="font-bold text-indigo-600">@{analyticsData.status.account_info.username}</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-gray-500 text-center py-8">No account data available</div>
                )
              ) : selectedPlatform === "instagram" ? (
                // Instagram doesn't have country/age demographics, show media types or engagement levels instead
                analyticsData.demographics?.by_media_type && Object.keys(analyticsData.demographics.by_media_type).length > 0 ? (
                  Object.entries(analyticsData.demographics.by_media_type)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 5)
                    .map(([type, count], idx) => (
                      <div key={type} className="flex items-center justify-between p-3 bg-gradient-to-r from-pink-50 to-purple-50 rounded-lg border border-pink-100 hover:border-pink-300 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-gradient-to-br from-pink-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">{idx + 1}</div>
                          <span className="text-gray-800 font-medium capitalize">{type.replace('_', ' ')}</span>
                        </div>
                        <span className="font-bold text-pink-600">{formatNumber(count)}</span>
                      </div>
                    ))
                ) : analyticsData.demographics?.by_engagement && Object.keys(analyticsData.demographics.by_engagement).length > 0 ? (
                  Object.entries(analyticsData.demographics.by_engagement)
                    .sort(([, a], [, b]) => b - a)
                    .map(([level, count], idx) => (
                      <div key={level} className="flex items-center justify-between p-3 bg-gradient-to-r from-pink-50 to-purple-50 rounded-lg border border-pink-100 hover:border-pink-300 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm ${
                            level === 'high' ? 'bg-green-500' : level === 'medium' ? 'bg-yellow-500' : 'bg-gray-500'
                          }`}>{idx + 1}</div>
                          <span className="text-gray-800 font-medium capitalize">{level} Engagement</span>
                        </div>
                        <span className="font-bold text-pink-600">{formatNumber(count)} posts</span>
                      </div>
                    ))
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-400 mb-2">📊</div>
                    <div className="text-gray-500 text-sm">Instagram doesn't provide country demographics</div>
                    <div className="text-gray-400 text-xs mt-1">Try Facebook for audience insights</div>
                  </div>
                )
              ) : (
                analyticsData.demographics?.by_country && Object.keys(analyticsData.demographics.by_country).length > 0 ? (
                  Object.entries(analyticsData.demographics.by_country)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 5)
                    .map(([country, count], idx) => (
                      <div key={country} className="flex items-center justify-between p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100 hover:border-blue-300 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">{idx + 1}</div>
                          <span className="text-gray-800 font-medium">{country}</span>
                        </div>
                        <span className="font-bold text-blue-600">{formatNumber(count)}</span>
                      </div>
                    ))
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-400 mb-2">🌍</div>
                    <div className="text-gray-500 text-sm">No country data available</div>
                    <div className="text-gray-400 text-xs mt-1">Connect your account to see audience insights</div>
                  </div>
                )
              )}
            </div>
          </div>
        </div>

        {/* Enhanced Statistics Card */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-shadow duration-300">
          <div className="bg-gradient-to-r from-purple-500 to-pink-600 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">
                {selectedPlatform === "reddit" ? "Account Statistics" : 
                 selectedPlatform === "twitter" ? "API Access Info" : 
                 selectedPlatform === "instagram" ? "Engagement Distribution" : 
                 "Audience by Age & Gender"}
              </h3>
            </div>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {selectedPlatform === "reddit" ? (
                analyticsData.status?.account_info ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-4 bg-orange-50 rounded-xl border border-orange-200 hover:shadow-md transition-all">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">⭐</span>
                        <span className="text-gray-700 font-medium">Total Karma</span>
                      </div>
                      <span className="font-bold text-orange-600 text-lg">{formatNumber(analyticsData.status.account_info.total_karma || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-blue-50 rounded-xl border border-blue-200 hover:shadow-md transition-all">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">🔗</span>
                        <span className="text-gray-700 font-medium">Link Karma</span>
                      </div>
                      <span className="font-bold text-blue-600 text-lg">{formatNumber(analyticsData.status.account_info.link_karma || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-purple-50 rounded-xl border border-purple-200 hover:shadow-md transition-all">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">💬</span>
                        <span className="text-gray-700 font-medium">Comment Karma</span>
                      </div>
                      <span className="font-bold text-purple-600 text-lg">{formatNumber(analyticsData.status.account_info.comment_karma || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-green-50 rounded-xl border border-green-200 hover:shadow-md transition-all">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">📅</span>
                        <span className="text-gray-700 font-medium">Account Age</span>
                      </div>
                      <span className="font-bold text-green-600 text-lg">{analyticsData.status.account_info.created_utc ? Math.floor((Date.now() - analyticsData.status.account_info.created_utc * 1000) / (1000 * 60 * 60 * 24)) + " days" : "Unknown"}</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-gray-500 text-center py-8">No account data available</div>
                )
              ) :               selectedPlatform === "twitter" ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-4 bg-yellow-50 rounded-xl border border-yellow-200">
                    <span className="text-gray-700 font-medium">API Access Level</span>
                    <span className="px-3 py-1 rounded-full font-semibold text-yellow-700 bg-yellow-200">Free Tier</span>
                  </div>
                  <div className="flex justify-between items-center p-4 bg-red-50 rounded-xl border border-red-200">
                    <span className="text-gray-700 font-medium">Tweets Access</span>
                    <span className="px-3 py-1 rounded-full font-semibold text-red-700 bg-red-200">Limited</span>
                  </div>
                  <div className="flex justify-between items-center p-4 bg-green-50 rounded-xl border border-green-200">
                    <span className="text-gray-700 font-medium">Analytics Available</span>
                    <span className="px-3 py-1 rounded-full font-semibold text-green-700 bg-green-200">Basic</span>
                  </div>
                  <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
                    <div className="text-sm text-gray-600 space-y-2">
                      <div className="flex items-center gap-2"><span className="text-green-600">✅</span> Account info: Available</div>
                      <div className="flex items-center gap-2"><span className="text-red-600">❌</span> Tweet content: Restricted</div>
                      <div className="flex items-center gap-2"><span className="text-red-600">❌</span> Engagement metrics: Restricted</div>
                    </div>
                  </div>
                </div>
              ) : selectedPlatform === "instagram" ? (
                // Instagram alternative: Show engagement distribution
                analyticsData.demographics?.by_engagement && Object.keys(analyticsData.demographics.by_engagement).length > 0 ? (
                  Object.entries(analyticsData.demographics.by_engagement)
                    .sort(([, a], [, b]) => b - a)
                    .map(([level, count]) => {
                      const total = Object.values(analyticsData.demographics.by_engagement).reduce((a, b) => a + b, 0);
                      const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                      return (
                        <div key={level} className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-700 font-medium capitalize">{level} Engagement</span>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-purple-600">{formatNumber(count)}</span>
                              <span className="text-xs text-gray-500">({percentage}%)</span>
                            </div>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full ${
                                level === 'high' ? 'bg-green-500' : level === 'medium' ? 'bg-yellow-500' : 'bg-gray-400'
                              }`}
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-400 mb-2">👥</div>
                    <div className="text-gray-500 text-sm">Instagram doesn't provide age/gender demographics</div>
                    <div className="text-gray-400 text-xs mt-1">Try Facebook for detailed audience insights</div>
                  </div>
                )
              ) : (
                analyticsData.demographics?.by_age_gender && Object.keys(analyticsData.demographics.by_age_gender).length > 0 ? (
                  Object.entries(analyticsData.demographics.by_age_gender)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 6)
                    .map(([segment, count]) => {
                      const total = Object.values(analyticsData.demographics.by_age_gender).reduce((a, b) => a + b, 0);
                      const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                      return (
                        <div key={segment} className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-700 font-medium">{segment}</span>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-pink-600">{formatNumber(count)}</span>
                              <span className="text-xs text-gray-500">({percentage}%)</span>
                            </div>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="h-2 rounded-full bg-gradient-to-r from-pink-500 to-purple-600"
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })
                ) : (
                  <div className="text-center py-8">
                    <div className="text-gray-400 mb-2">👥</div>
                    <div className="text-gray-500 text-sm">No demographic data available</div>
                    <div className="text-gray-400 text-xs mt-1">Connect your account to see audience insights</div>
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Best Performing Post - Enhanced */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-shadow duration-300">
          <div className="bg-gradient-to-r from-emerald-500 to-teal-600 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">Best Performing Post</h3>
            </div>
          </div>
          <div className="p-6">
            {analyticsData.bestPost?.post && Object.keys(analyticsData.bestPost.post).length > 0 ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-700 line-clamp-3 bg-gray-50 p-4 rounded-lg border-l-4 border-emerald-500">{safeGet(analyticsData.bestPost.post, "message", "No message available")}</div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <div className="text-xs text-blue-600 font-medium mb-1">Reach</div>
                    <div className="text-lg font-bold text-blue-700">{formatNumber(safeGet(analyticsData.bestPost.post, "reach", 0))}</div>
                  </div>
                  <div className="bg-purple-50 p-3 rounded-lg">
                    <div className="text-xs text-purple-600 font-medium mb-1">Impressions</div>
                    <div className="text-lg font-bold text-purple-700">{formatNumber(safeGet(analyticsData.bestPost.post, "impressions", 0))}</div>
                  </div>
                  <div className="bg-emerald-50 p-3 rounded-lg">
                    <div className="text-xs text-emerald-600 font-medium mb-1">Engaged</div>
                    <div className="text-lg font-bold text-emerald-700">{formatNumber(safeGet(analyticsData.bestPost.post, "engaged_users", 0))}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-center py-8">No post data available</div>
            )}
          </div>
        </div>

        {/* Worst Performing Post - Enhanced */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-shadow duration-300">
          <div className="bg-gradient-to-r from-orange-500 to-red-600 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">Worst Performing Post</h3>
            </div>
          </div>
          <div className="p-6">
            {analyticsData.worstPost?.post && Object.keys(analyticsData.worstPost.post).length > 0 ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-700 line-clamp-3 bg-gray-50 p-4 rounded-lg border-l-4 border-orange-500">{safeGet(analyticsData.worstPost.post, "message", "No message available")}</div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <div className="text-xs text-blue-600 font-medium mb-1">Reach</div>
                    <div className="text-lg font-bold text-blue-700">{formatNumber(safeGet(analyticsData.worstPost.post, "reach", 0))}</div>
                  </div>
                  <div className="bg-purple-50 p-3 rounded-lg">
                    <div className="text-xs text-purple-600 font-medium mb-1">Impressions</div>
                    <div className="text-lg font-bold text-purple-700">{formatNumber(safeGet(analyticsData.worstPost.post, "impressions", 0))}</div>
                  </div>
                  <div className="bg-orange-50 p-3 rounded-lg">
                    <div className="text-xs text-orange-600 font-medium mb-1">Engaged</div>
                    <div className="text-lg font-bold text-orange-700">{formatNumber(safeGet(analyticsData.worstPost.post, "engaged_users", 0))}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-center py-8">No post data available</div>
            )}
          </div>
        </div>
      </div>

      {analyticsData.posts?.posts && analyticsData.posts.posts.length > 0 && (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          <div className="bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">Recent Posts Performance</h3>
            </div>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {analyticsData.posts.posts.slice(0, 5).map((post, index) => {
              let engagementMetrics = [];
              if (selectedPlatform === "twitter") {
                const likes = post.reactions?.like || 0;
                const retweets = post.reactions?.retweet || 0;
                const replies = post.reactions?.reply || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Likes", value: likes },
                  { label: "Retweets", value: retweets },
                  { label: "Replies", value: replies },
                ];
              } else if (selectedPlatform === "reddit") {
                const upvotes = post.reactions?.upvote || 0;
                const downvotes = post.reactions?.downvote || 0;
                const comments = post.reactions?.comment || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Upvotes", value: upvotes },
                  { label: "Downvotes", value: downvotes },
                  { label: "Comments", value: comments },
                ];
              } else if (selectedPlatform === "facebook") {
                const totalLikes = post.reactions?.like || post.reactions_count || 0;
                const actualComments = post.reactions?.comment || post.comments_count || 0;
                const actualShares = post.reactions?.share || post.shares_count || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Likes", value: totalLikes },
                  { label: "Comments", value: actualComments },
                  { label: "Shares", value: actualShares },
                ];
              } else {
                const likes = post.reactions?.like || 0;
                const comments = post.reactions?.comment || 0;
                const shares = post.reactions?.share || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Likes", value: likes },
                  { label: "Comments", value: comments },
                  { label: "Shares", value: shares },
                ];
              }
              return (
                <div key={post.id || index} className="bg-gradient-to-r from-gray-50 to-white p-4 rounded-xl border border-gray-200 hover:border-indigo-300 hover:shadow-md transition-all duration-200">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1 text-sm text-gray-700 line-clamp-2 font-medium">{post.message || "No message available"}</div>
                    <div className="ml-3 px-2 py-1 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold">#{index + 1}</div>
                  </div>
                  <div className="grid grid-cols-4 gap-3">
                    {engagementMetrics.map((metric, idx) => (
                      <div key={idx} className="bg-white p-2 rounded-lg border border-gray-100">
                        <div className="text-xs text-gray-500 mb-1">{metric.label}</div>
                        <div className="text-sm font-bold text-gray-800">{formatNumber(metric.value)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
            </div>
          </div>
        </div>
      )}

      {!isConfigured &&
        connectedAccounts.length === 0 &&
        selectedPlatform !== "all" &&
        platformRequiresExplicitAccount(selectedPlatform) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-800">
                <strong>No {selectedPlatform} account connected.</strong> Please connect your {selectedPlatform} account in Settings to view analytics.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Analytics;