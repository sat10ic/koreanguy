import { lazy, Suspense } from "react";
import { Route, HashRouter, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ModeProvider } from "./lib/ModeContext";
import { RouteBoundary } from "./components/ui/PanelBoundary";
import { Skeleton } from "./components/ui/Skeleton";

// F-5: route-level code splitting — each screen (and its chart library) is
// fetched on first visit instead of one 7+ MB chunk.
const Tonight = lazy(() => import("./screens/Tonight").then((m) => ({ default: m.Tonight })));
const Market = lazy(() => import("./screens/Market").then((m) => ({ default: m.Market })));
const Candidates = lazy(() => import("./screens/Candidates").then((m) => ({ default: m.Candidates })));
const Stock = lazy(() => import("./screens/Stock").then((m) => ({ default: m.Stock })));
const Desk = lazy(() => import("./screens/Desk").then((m) => ({ default: m.Desk })));
const History = lazy(() => import("./screens/History").then((m) => ({ default: m.History })));
const Research = lazy(() => import("./screens/Research").then((m) => ({ default: m.Research })));
const Settings = lazy(() => import("./screens/Settings").then((m) => ({ default: m.Settings })));
const Events = lazy(() => import("./screens/Events").then((m) => ({ default: m.Events })));

// E-4.4: short fade/slide route transitions (screens previously hard-cut).
// framer-motion runs under MotionConfig reducedMotion="user" (main.tsx), so
// the OS reduced-motion setting suppresses these too.
function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.16, ease: "easeOut" }}
        className="h-full"
      >
        <Routes location={location}>
          <Route path="/" element={<RouteBoundary><Tonight /></RouteBoundary>} />
          <Route path="/market" element={<RouteBoundary><Market /></RouteBoundary>} />
          <Route path="/candidates" element={<RouteBoundary><Candidates /></RouteBoundary>} />
          <Route path="/stock" element={<RouteBoundary><Stock /></RouteBoundary>} />
          <Route path="/stock/:symbol" element={<RouteBoundary><Stock /></RouteBoundary>} />
          <Route path="/desk" element={<RouteBoundary><Desk /></RouteBoundary>} />
          <Route path="/history" element={<RouteBoundary><History /></RouteBoundary>} />
          <Route path="/research" element={<RouteBoundary><Research /></RouteBoundary>} />
          <Route path="/settings" element={<RouteBoundary><Settings /></RouteBoundary>} />
          <Route path="/events" element={<RouteBoundary><Events /></RouteBoundary>} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <ModeProvider>
      <HashRouter>
        <Suspense fallback={<Skeleton label="loading screen…" />}>
          <AnimatedRoutes />
        </Suspense>
      </HashRouter>
    </ModeProvider>
  );
}
