import { lazy, Suspense, useEffect, useState } from 'react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronRight,
  CircleDollarSign,
  CloudUpload,
  FileSpreadsheet,
  Fingerprint,
  Gauge,
  Layers3,
  Menu,
  ShieldCheck,
  Sparkles,
  Target,
  WandSparkles,
  X,
} from 'lucide-react'
import { getHealth } from './services/api'
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom'
import './App.css'

const DataChart = lazy(() => import('./components/DataChart.jsx'))
const Dashboard = lazy(() => import('./dashboard/Dashboard.jsx'))

const features = [
  { icon: CloudUpload, title: 'CSV and Excel upload', text: 'Bring in spreadsheets and transaction exports in a few clicks.' },
  { icon: WandSparkles, title: 'Automatic data cleaning', text: 'Standardize formats and prepare records for consistent analysis.' },
  { icon: Target, title: 'Missing value detection', text: 'Spot gaps early and choose how to handle incomplete fields.' },
  { icon: Layers3, title: 'Duplicate removal', text: 'Find repeated transactions and keep your dataset tidy.' },
  { icon: CircleDollarSign, title: 'Financial data analysis', text: 'Turn organized records into clear totals and useful summaries.' },
  { icon: BarChart3, title: 'Interactive charts', text: 'Explore trends and patterns with visual reports.' },
]

const steps = [
  { number: '01', icon: CloudUpload, title: 'Upload your files', text: 'Start with a CSV or Excel file. Your original data stays yours.' },
  { number: '02', icon: Fingerprint, title: 'Review and clean', text: 'See detected issues and prepare records with clear controls.' },
  { number: '03', icon: Gauge, title: 'Explore your insights', text: 'Review summaries, charts, and download your cleaned dataset.' },
]

const benefits = [
  'Spend less time fixing spreadsheets by hand',
  'Catch common data quality issues earlier',
  'Get a clearer view of your financial activity',
]

const chartData = [
  { month: 'Jan', value: 28000 }, { month: 'Feb', value: 37000 }, { month: 'Mar', value: 33000 },
  { month: 'Apr', value: 48000 }, { month: 'May', value: 43000 }, { month: 'Jun', value: 61000 },
  { month: 'Jul', value: 55000 }, { month: 'Aug', value: 72000 },
]

function Brand({ footer = false }) {
  return (
    <a className={`brand${footer ? ' brand--footer' : ''}`} href="#home" aria-label="FinPrep home">
      <span className="brand-mark"><BarChart3 size={19} strokeWidth={2.4} /></span>
      <span>fin<span>prep</span></span>
    </a>
  )
}

function LandingPage() {
  const navigate = useNavigate()
  const [connection, setConnection] = useState('checking')
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal)
      .then(() => setConnection('connected'))
      .catch((error) => {
        if (error.name !== 'CanceledError') setConnection('disconnected')
      })
    return () => controller.abort()
  }, [])

  const closeMenu = () => setMenuOpen(false)
  const openDashboard = (event) => {
    event.preventDefault()
    closeMenu()
    navigate('/dashboard')
    window.scrollTo(0, 0)
  }

  return (
    <>
      <header className="site-header">
        <nav className="nav-wrap" aria-label="Main navigation">
          <Brand />
          <button className="mobile-menu-toggle" type="button" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </button>
          <div className={`nav-content${menuOpen ? ' nav-content--open' : ''}`}>
            <div className="nav-links">
              <a href="#home" onClick={closeMenu}>Home</a>
              <a href="#features" onClick={closeMenu}>Features</a>
              <a href="#about" onClick={closeMenu}>About</a>
            </div>
            <div className="nav-actions">
              <a className="login-link" href="#login" onClick={closeMenu}>Log in</a>
              <a className="button button--small button--primary" href="/dashboard" onClick={openDashboard}>Get Started <ArrowRight size={16} /></a>
            </div>
          </div>
        </nav>
      </header>

      <main>
        <section className="hero section-shell" id="home">
          <div className="hero-copy">
            <div className="eyebrow"><Sparkles size={15} /> YOUR FINANCIAL DATA, IN FOCUS</div>
            <h1>Clean Your Financial Data. <span>Make Smarter Decisions.</span></h1>
            <p className="hero-description">Turn messy spreadsheets into reliable insights. Clean, validate, and understand your financial data in one simple workspace.</p>
            <div className="hero-actions">
              <a className="button button--primary" href="/dashboard" onClick={openDashboard}>Get Started <ArrowRight size={17} /></a>
              <a className="button button--quiet" href="#how-it-works"><span className="play-icon"><ArrowDown size={15} /></span> See how it works</a>
            </div>
            <div className="hero-trust">
              <div className="trust-avatars" aria-hidden="true"><span>F</span><span>D</span><span>A</span></div>
              <div><strong>Built for clearer books</strong><small>From first upload to final report</small></div>
            </div>
          </div>

          <div className="hero-visual" aria-label="Example financial data overview">
            <div className="visual-orbit visual-orbit--one" />
            <div className="visual-orbit visual-orbit--two" />
            <div className="overview-card">
              <div className="overview-topline"><span className="overview-label"><span className="live-dot" /> DATA OVERVIEW</span><span className="period-pill">Last 8 months <ChevronRight size={13} /></span></div>
              <div className="overview-title-row"><div><span className="metric-caption">Net cash flow</span><strong className="metric-value">₹48,290.00<span className="metric-change"><ArrowUpRight size={14} /> 12.8%</span></strong></div><span className="metric-icon"><CircleDollarSign size={19} /></span></div>
              <div className="chart-wrap"><Suspense fallback={<div className="chart-loading" /> }><DataChart data={chartData} /></Suspense></div>
              <div className="overview-bottom"><div className="mini-stat"><span className="mini-stat-icon mini-stat-icon--green"><Check size={13} /></span><span><b>Data quality</b><small>Looking good</small></span></div><div className="mini-stat"><span className="mini-stat-icon mini-stat-icon--blue"><FileSpreadsheet size={13} /></span><span><b>Transactions</b><small>1,248 records</small></span></div></div>
            </div>
            <div className="floating-note"><span className="floating-note-icon"><ShieldCheck size={17} /></span><span><b>Ready to analyze</b><small>Your data is organized</small></span><Check className="floating-check" size={16} /></div>
            <div className="decor-dot decor-dot--one" /><div className="decor-dot decor-dot--two" />
          </div>
        </section>

        <section className="proof-strip" aria-label="Product highlights">
          <div className="proof-inner"><span>ONE WORKSPACE FOR</span><b><FileSpreadsheet size={17} /> SPREADSHEETS</b><i /><b><ShieldCheck size={17} /> DATA QUALITY</b><i /><b><BarChart3 size={17} /> FINANCIAL INSIGHTS</b></div>
        </section>

        <section className="section section-shell" id="features">
          <div className="section-heading"><span className="section-kicker">MADE FOR YOUR WORKFLOW</span><h2>Everything your data needs.<br /><span>Nothing it doesn’t.</span></h2><p>A practical toolkit for cleaner records and more confident analysis.</p></div>
          <div className="feature-grid">
            {features.map(({ icon: Icon, title, text }, index) => <article className="feature-card" key={title} style={{ '--card-delay': `${index * 60}ms` }}><span className="feature-icon"><Icon size={21} strokeWidth={1.8} /></span><h3>{title}</h3><p>{text}</p><span className="feature-arrow"><ArrowUpRight size={17} /></span></article>)}
          </div>
        </section>

        <section className="how-section" id="how-it-works">
          <div className="section section-shell">
            <div className="section-heading"><span className="section-kicker">A CLEARER PROCESS</span><h2>From raw file to <span>ready.</span></h2><p>Three straightforward steps take you from spreadsheet to signal.</p></div>
            <div className="steps-grid">{steps.map(({ number, icon: Icon, title, text }, index) => <article className="step-card" key={number}><div className="step-top"><span className="step-icon"><Icon size={21} /></span><span className="step-number">{number}</span></div><div className="step-connector" aria-hidden="true" /><h3>{title}</h3><p>{text}</p>{index < steps.length - 1 && <ArrowRight className="step-arrow" size={18} />}</article>)}</div>
          </div>
        </section>

        <section className="benefits section-shell" id="about">
          <div className="benefits-visual"><div className="benefit-orb" /><div className="benefit-sheet"><div className="sheet-header"><span>MONTHLY SUMMARY</span><span className="sheet-menu">•••</span></div><div className="sheet-total">₹24,680.00<small>Net position</small></div><div className="sheet-bars"><i style={{ height: '38%' }} /><i style={{ height: '57%' }} /><i style={{ height: '46%' }} /><i style={{ height: '73%' }} /><i style={{ height: '63%' }} /><i style={{ height: '92%' }} /><i style={{ height: '78%' }} /><i style={{ height: '100%' }} /></div><div className="sheet-legend"><span><i /> Income</span><span><i /> Expenses</span></div></div><div className="benefit-stamp"><Check size={17} /><span>Organized<br />with clarity</span></div></div>
          <div className="benefits-copy"><span className="section-kicker">MORE CLARITY, LESS BUSYWORK</span><h2>Make room for the work <span>that matters.</span></h2><p className="benefits-intro">When your numbers are in good shape, it’s easier to see what’s happening and decide what comes next.</p><ul>{benefits.map((benefit) => <li key={benefit}><span><Check size={14} /></span>{benefit}</li>)}</ul><a className="text-link" href="#get-started">Explore the workflow <ArrowRight size={17} /></a></div>
        </section>

        <section className="cta-section section-shell" id="get-started">
          <div className="cta-spark cta-spark--one"><Sparkles size={20} /></div><div className="cta-spark cta-spark--two"><Sparkles size={13} /></div>
          <div className="cta-content"><span className="cta-kicker"><span /> YOUR NEXT STEP STARTS HERE</span><h2>Put your financial data<br />to work.</h2><p>A clearer picture starts with a cleaner dataset.</p><a href="/dashboard" onClick={openDashboard} className="button button--white">Get Started <ArrowRight size={17} /></a></div>
          <div className="cta-decoration" aria-hidden="true"><div /><div /><div /><div /><div /><div /><div /></div>
        </section>
      </main>

      <footer className="site-footer" id="login">
        <div className="footer-main section-shell"><div className="footer-brand-col"><Brand footer /><p>Clean, reliable financial data for clearer decisions.</p><div className={`api-status api-status--${connection}`}><span />{connection === 'connected' ? 'All systems operational' : connection === 'checking' ? 'Connecting to service' : 'Service unavailable'}</div></div><div className="footer-links"><div><b>EXPLORE</b><a href="#features">Features</a><a href="#how-it-works">How it works</a><a href="#about">About</a></div><div><b>GET STARTED</b><a href="#get-started">Start with your data</a><a href="#login">Log in <ArrowUpRight size={13} /></a></div></div></div>
        <div className="footer-bottom section-shell"><span>© 2026 FinPrep. Built for better financial clarity.</span><span><ShieldCheck size={14} /> Your data. Your decisions.</span></div>
      </footer>
    </>
  )
}

function DashboardPage() {
  const navigate = useNavigate()
  return <Dashboard onBack={() => { navigate('/'); window.scrollTo(0, 0) }} />
}

function NotFoundPage() {
  return (
    <main className="route-not-found">
      <p>That page isn’t here.</p>
      <a className="button button--primary" href="/">Return to home</a>
      <a className="text-link" href="/dashboard">Open the dashboard <ArrowRight size={16} /></a>
    </main>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="app-loading">Opening your workspace…</div>}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
