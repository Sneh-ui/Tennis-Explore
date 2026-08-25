import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom"
import { motion, AnimatePresence, useMotionValue, useSpring } from "framer-motion";
import { useAuth } from "@/hooks/use-auth";
import { savePendingQuery } from "@/lib/pending-query";

/* ─────────────────────────── DATA ─────────────────────────── */
const APPS = [
  { icon: "groups", label: "Teamworks" },
  { icon: "analytics", label: "AMS" },
  { icon: "fitness_center", label: "Teambuildr" },
  { icon: "sports_tennis", label: "Bounce", filled: true, bold: true },
  { icon: "strategy", label: "Coaches Box" },
  { icon: "directions_run", label: "TennisMove" },
  { icon: "workspace_premium", label: "ACE" },
];

const HINTS = [
  "Match Prediction AI",
  "Biomechanics Analysis",
  "Sponsorship ROI",
  "ATP Live Rankings",
];

const PROFILE_IMG =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuBGIcKV9ELNPFkyEs0mERlw_quRuuVkySlODEgZCDK4tk-N5ahEITwftdEuXe-DSjb_YDIFVe1AYALix5ng02vJRraMscEIwlqfipXl9DO5UMjXDmCwpz79C7dIC5_1Ge3jFxnh3x7cblHx3t_k3CxrfECMBQQNcLhgyekfe2-G-Bvs0uZ6bDfO4_ybczWqXYhiXLElNcnW6-8TpKZ3e8ZxW9gjoHuDC_Lv14GQKqPyAnNuYqYzKOv9W_bmVuMdPu-oLLALoANOuw";

// Free Pexels tennis video (no auth needed for direct mp4)
const BG_VIDEO_URL =
  "/videos/herobg.mp4";
/* ─────────────────────────── ICON ─────────────────────────── */
const Icon = ({ name, className = "", filled = false }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={
      filled
        ? { fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24" }
        : undefined
    }
  >
    {name}
  </span>
);

/* ─────────────────────────── CURSOR GLOW ──────────────────── */
function CursorGlow() {
  const x = useMotionValue(-200);
  const y = useMotionValue(-200);
  const springX = useSpring(x, { damping: 25, stiffness: 200 });
  const springY = useSpring(y, { damping: 25, stiffness: 200 });

  useEffect(() => {
    const handler = (e) => {
      x.set(e.clientX);
      y.set(e.clientY);
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, [x, y]);

  return (
    <motion.div
      className="pointer-events-none fixed z-[5] w-[600px] h-[600px] rounded-full"
      style={{
        x: springX,
        y: springY,
        translateX: "-50%",
        translateY: "-50%",
        background:
          "radial-gradient(circle, rgba(176,248,32,0.06) 0%, rgba(99,102,241,0.03) 40%, transparent 70%)",
      }}
    />
  );
}

/* ─────────────────────────── GLASS CARD (APP) ─────────────── */
function AppCard({ icon, label, filled, bold, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.8 + index * 0.08, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ x: 8, backgroundColor: "rgba(18, 20, 28, 0.8)", borderColor: "rgba(176, 248, 32, 0.3)" }}
      className="flex items-center gap-4 px-5 py-3 rounded-xl cursor-pointer"
      style={{
        background: "rgba(18, 20, 28, 0.6)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255, 255, 255, 0.05)",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      <Icon name={icon} filled={filled} className="text-[#b0f820]" />
      <span
        className={`text-xs uppercase tracking-wider text-white ${bold ? "font-bold" : ""}`}
        style={{ fontFamily: "Inter", letterSpacing: "0.05em", fontWeight: bold ? 700 : 600, fontSize: 12 }}
      >
        {label}
      </span>
    </motion.div>
  );
}

/* ─────────────────────────── HINT PILL ────────────────────── */
function HintPill({ label, index }) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.6 + index * 0.1, duration: 0.5 }}
      whileHover={{ borderColor: "rgba(176, 248, 32, 0.3)", scale: 1.04 }}
      className="px-4 py-2 rounded-full whitespace-nowrap cursor-pointer text-[#c2caae]"
      style={{
        background: "rgba(18, 20, 28, 0.6)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255, 255, 255, 0.05)",
        fontFamily: "Inter",
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
      }}
    >
      {label}
    </motion.span>
  );
}

/* ─────────────────────────── SEARCH BAR ───────────────────── */
function SearchBar() {
  const [focused, setFocused] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleSend = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    if (user) {
      navigate("/ai-chatbot", { state: { query: trimmed } });
    } else {
      await savePendingQuery(trimmed);
      navigate("/login");
    }
    setQuery("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.2, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className="mt-8 relative group"
    >
      {/* Glow aura */}
      <AnimatePresence>
        {focused && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="absolute -inset-1 rounded-[32px] blur-xl"
            style={{
              background: "linear-gradient(to right, rgba(176,248,32,0.2), rgba(49,49,192,0.2))",
            }}
          />
        )}
      </AnimatePresence>

      <div
        className="relative flex items-center gap-4 p-2 rounded-[32px] shadow-2xl"
        style={{
          background: "rgba(18, 20, 28, 0.6)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
        }}
      >
        <input
          className="flex-1 bg-transparent border-none outline-none text-white placeholder:text-[#c2caae]/50 py-4 pl-6 pr-3"
          style={{ fontFamily: "Inter", fontSize: 18, lineHeight: "28px" }}
          placeholder="Ask anything about tennis..."
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />

        <div className="flex items-center gap-1 pr-1">
          <motion.button
            whileHover={{ color: "#ffffff" }}
            className="p-3 text-[#c2caae] transition-colors"
          >
            <Icon name="mic" />
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            onClick={handleSend}
            className="w-14 h-14 rounded-full flex items-center justify-center"
            style={{
              backgroundColor: "#b0f820",
              boxShadow: "0 0 20px rgba(176,248,32,0.4)",
            }}
          >
            <Icon name="arrow_upward" className="text-black font-bold" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

/* ─────────────────────────── HEADER ───────────────────────── */
function Header() {
  const { user } = useAuth();

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center py-6 border-b"
      style={{
        paddingLeft: 64,
        paddingRight: 64,
        backgroundColor: "rgba(17, 19, 29, 0.1)",
        backdropFilter: "blur(12px)",
        borderColor: "rgba(255,255,255,0.05)",
      }}
    >
      {/* Menu button */}
      <div className="flex items-center gap-4">
        <motion.button
          whileHover={{ borderColor: "rgba(176,248,32,0.3)" }}
          className="flex items-center gap-2 px-4 py-2 rounded-full uppercase tracking-[0.15em] text-[#e1e1f0] hover:text-[#b0f820] transition-colors"
          style={{
            background: "rgba(18, 20, 28, 0.6)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(255,255,255,0.05)",
            fontFamily: "Inter",
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: "0.05em",
          }}
        >
          <Icon name="menu" className="text-[18px]" />
          Menu
        </motion.button>
      </div>

      {/* Logo */}
      <div className="absolute left-1/2 -translate-x-1/2">
        <motion.h1
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="flex gap-1 tracking-tight"
          style={{ fontFamily: "'Playfair Display', serif", fontSize: 32, fontWeight: 500, lineHeight: "40px" }}
        >
          <span className="text-white font-extrabold italic">Tennis</span>
          <span className="text-[#b0f820] font-light">Explore</span>
        </motion.h1>
      </div>

      {/* Right nav */}
      <div className="flex items-center gap-6">
        <nav
          className="hidden md:flex items-center gap-8 uppercase tracking-[0.15em] text-[#c2caae]"
          style={{ fontFamily: "Inter", fontSize: 12, fontWeight: 600, letterSpacing: "0.05em" }}
        >
          {user ? (
            <motion.div whileHover={{ color: "#b0f820" }}>
              <Link
                to="/dashboard"
                className="cursor-pointer transition-colors"
              >
                Dashboard
              </Link>
            </motion.div>
          ) : (
            <motion.div whileHover={{ color: "#b0f820" }}>
              <Link
                to="/login"
                className="cursor-pointer transition-colors"
              >
                Login
              </Link>
            </motion.div>
          )}
        </nav>
        <motion.div
          whileHover={{ scale: 1.1 }}
          className="w-10 h-10 rounded-full overflow-hidden cursor-pointer group"
          style={{
            background: "rgba(18, 20, 28, 0.6)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          <img
            className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
            src={PROFILE_IMG}
            alt="Profile"
          />
        </motion.div>
      </div>
    </motion.header>
  );
}


/* ─────────────────────────── VIDEO BG ─────────────────────── */
function VideoBG() {
  const [loaded, setLoaded] = useState(false);

  return (
    <div className="fixed inset-0 z-0 overflow-hidden">
      {/* Video layer */}
      <motion.video
        initial={{ opacity: 0, scale: 1.1 }}
        animate={{ opacity: loaded ? 0.8 : 0, scale: 1 }}
        transition={{ duration: 2, ease: "easeOut" }}
        className="absolute inset-0 w-full h-full object-cover"
        src={BG_VIDEO_URL}
        autoPlay
        loop
        muted
        playsInline
        onCanPlay={() => setLoaded(true)}
        style={{ filter: "blur(2px) saturate(0.3)" }}
      />

      {/* Gradient overlays */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to right, #02030A 0%, rgba(2,3,10,0.85) 40%, rgba(2,3,10,0.4) 70%, rgba(2,3,10,0.6) 100%)",
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to bottom, rgba(2,3,10,0.5) 0%, transparent 30%, transparent 70%, #02030A 100%)",
        }}
      />

      {/* Ambient glow orbs */}
      <motion.div
        animate={{
          y: [0, -30, 0],
          opacity: [0.15, 0.25, 0.15],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-[20%] right-[15%] w-[500px] h-[500px] rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)",
        }}
      />
      <motion.div
        animate={{
          y: [0, 20, 0],
          opacity: [0.1, 0.2, 0.1],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 2 }}
        className="absolute bottom-[10%] right-[25%] w-[400px] h-[400px] rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(176,248,32,0.08) 0%, transparent 70%)",
        }}
      />
    </div>
  );
}

/* ─────────────────────────── MAIN EXPORT ──────────────────── */
const TennisExploreHero = ()=> {
  return (
    <div
      className="h-screen w-full overflow-hidden relative select-none"
      style={{
        backgroundColor: "#02030A",
        color: "#e1e1f0",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      {/* Google Fonts */}
      <link
        href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Inter:wght@300;400;500;600;700&display=swap"
        rel="stylesheet"
      />
      <link
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
        rel="stylesheet"
      />
      <style>{`
        .material-symbols-outlined {
          font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
          vertical-align: middle;
        }
        input::placeholder { opacity: 0.5; }
        ::-webkit-scrollbar { display: none; }
        * { scrollbar-width: none; }
      `}</style>

      {/* Layers */}
      <VideoBG />
      <CursorGlow />
      <Header />

      {/* ── Main Grid ── */}
      <main
        className="relative z-10 grid grid-cols-12 h-screen pt-32 pb-16"
        style={{ paddingLeft: 64, paddingRight: 64 }}
      >
        {/* Left: App list */}
        <div className="col-span-3 flex flex-col justify-center gap-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5 }}
            className="flex flex-col gap-2"
          >
            <p
              className="text-[#b0f820] font-bold uppercase"
              style={{
                fontFamily: "Inter",
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: "0.3em",
                lineHeight: "16px",
              }}
            >
              Our Own Apps
            </p>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: 48 }}
              transition={{ delay: 0.8, duration: 0.4 }}
              className="h-[1px] bg-[#b0f820]"
            />
          </motion.div>

          <div className="flex flex-col gap-3 max-w-[240px]">
            {APPS.map((app, i) => (
              <AppCard key={app.label} index={i} {...app} />
            ))}
          </div>
        </div>

        {/* Right: Hero content */}
        <div className="col-span-9 flex flex-col justify-center pl-12 relative">
          {/* Headline + description row */}
          <div className="flex items-start justify-between mb-8">
            <div className="max-w-2xl">
              <h2 className="flex flex-col" style={{ fontFamily: "'Playfair Display', serif" }}>
                <motion.span
                  initial={{ opacity: 0, y: 60, rotateX: 40 }}
                  animate={{ opacity: 1, y: 0, rotateX: 0 }}
                  transition={{ delay: 0.3, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                  className="text-white font-normal tracking-tighter"
                  style={{ fontSize: 84, lineHeight: "92px", letterSpacing: "-0.02em" }}
                >
                  Let's Explore
                </motion.span>
                <motion.span
                  initial={{ opacity: 0, y: 60, rotateX: 40 }}
                  animate={{ opacity: 1, y: 0, rotateX: 0 }}
                  transition={{ delay: 0.5, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                  className="text-[#b0f820] italic font-bold tracking-tight"
                  style={{ fontSize: 84, lineHeight: "92px", letterSpacing: "-0.02em" }}
                >
                  Tennis
                </motion.span>
              </h2>
            </div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 1, duration: 0.7 }}
              className="max-w-[280px] mt-12"
            >
              <p
                className="text-right leading-relaxed"
                style={{
                  fontFamily: "Inter",
                  fontSize: 18,
                  lineHeight: "28px",
                  color: "rgba(194, 202, 174, 0.8)",
                }}
              >
                Explore tennis intelligence through data, media, and AI-powered insights.
              </p>
            </motion.div>
          </div>

          {/* Search bar */}
          <SearchBar />

          {/* Hint pills */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5, duration: 0.5 }}
            className="mt-10 flex gap-4 overflow-x-auto"
          >
            {HINTS.map((h, i) => (
              <HintPill key={h} label={h} index={i} />
            ))}
          </motion.div>
        </div>
      </main>
    </div>
  );
}

TennisExploreHero.showSidebar = false;
export default TennisExploreHero;
