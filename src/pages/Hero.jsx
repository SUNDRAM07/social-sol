import Button from "../components/ui/Button.jsx";
import { Link } from "react-router-dom";

// Import social media icons
import FacebookIcon from "../assets/social1/Facebook_icon.png";
import InstagramIcon from "../assets/social1/Instagram_icon.png";
import YouTubeIcon from "../assets/social1/YouTube_icon.png";
import TwitterIcon from "../assets/social1/Twitter_icon.png";

function Hero() {

  return (
    <section className="glass p-8 rounded-3xl flex items-center justify-between">
      <div className="max-w-xl">
        <h2 className="text-3xl font-bold gradient-primary-text mb-3">Your manager that never sleeps</h2>
        <p className="text-sm text-[var(--text-muted)] mb-4">Build, grow, and scale your business with a team of AI helpers — schedule posts, reply to comments, and automate work while you sleep.</p>
        <div className="flex items-center gap-3">
          <Link to="/create"><Button variant="primary" size="md">Get Started</Button></Link>
          <Link to="/help-support"><Button variant="ghost" size="sm">Learn more</Button></Link>
        </div>
      </div>
      {/* Social Media Icons Network - From Friend's Project */}
      <div className="w-1/3 flex justify-end">
        <div
          className="rounded-2xl shadow-xl p-6 flex items-center justify-center"
          style={{ background: "#dff6e9", minWidth: 280, minHeight: 260 }}
        >
          <svg viewBox="0 0 300 260" className="w-full h-full" aria-hidden>
            {/* Big Circle */}
            <circle
              cx="150"
              cy="130"
              r="80"
              stroke="#0b1724"
              strokeWidth="2"
              fill="none"
              opacity="0.6"
            />

            {/* Background small circles for nodes */}
            <g fill="#fff" stroke="#ddd" strokeWidth="1">
              <circle cx="150" cy="50" r="20" />
              <circle cx="230" cy="130" r="20" />
              <circle cx="150" cy="210" r="20" />
              <circle cx="70" cy="130" r="20" />
            </g>

            {/* Clip paths for circular crop */}
            <clipPath id="clipTop">
              <circle cx="150" cy="50" r="16" />
            </clipPath>
            <clipPath id="clipRight">
              <circle cx="230" cy="130" r="16" />
            </clipPath>
            <clipPath id="clipBottom">
              <circle cx="150" cy="210" r="16" />
            </clipPath>
            <clipPath id="clipLeft">
              <circle cx="70" cy="130" r="16" />
            </clipPath>

            {/* Social icons (small inside circles) */}
            <image
              href={FacebookIcon}
              x="134"
              y="34"
              width="32"
              height="32"
              clipPath="url(#clipTop)"
              preserveAspectRatio="xMidYMid slice"
            />
            <image
              href={InstagramIcon}
              x="214"
              y="114"
              width="32"
              height="32"
              clipPath="url(#clipRight)"
              preserveAspectRatio="xMidYMid slice"
            />
            <image
              href={YouTubeIcon}
              x="134"
              y="194"
              width="32"
              height="32"
              clipPath="url(#clipBottom)"
              preserveAspectRatio="xMidYMid slice"
            />
            <image
              href={TwitterIcon}
              x="54"
              y="114"
              width="32"
              height="32"
              clipPath="url(#clipLeft)"
              preserveAspectRatio="xMidYMid slice"
            />
          </svg>
        </div>
      </div>
    </section>
  );
}

export default Hero;


