import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Icon, StatCard, ProgressBar, PageHeader } from '@/components/shared'
import { DASHBOARD_STATS, WIN_RATES, RECENT_VIDEOS, RECENT_QUERIES } from '@/data/constants'

function PerformanceChart() {
  return (
    <Card className="lg:col-span-2 p-6">
      <div className="flex justify-between items-center mb-6">
        <CardTitle>Player Performance Trend</CardTitle>
        <Select defaultValue="30d">
          <SelectTrigger className="w-[150px] h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="30d">Last 30 Days</SelectItem>
            <SelectItem value="6m">Last 6 Months</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="h-64 flex items-end justify-between gap-1 relative pt-4">
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-5">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="border-t border-foreground w-full" />
          ))}
        </div>
        <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 100">
          <defs>
            <linearGradient id="chartGrad" x1="0%" x2="0%" y1="0%" y2="100%">
              <stop offset="0%" style={{ stopColor: '#0d631b', stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: '#0d631b', stopOpacity: 0 }} />
            </linearGradient>
          </defs>
          <path d="M0,80 Q10,75 20,60 T40,65 T60,40 T80,30 T100,20" fill="none" stroke="#0d631b" strokeWidth="2" vectorEffect="non-scaling-stroke" />
          <path d="M0,80 Q10,75 20,60 T40,65 T60,40 T80,30 T100,20 L100,100 L0,100 Z" fill="url(#chartGrad)" opacity="0.1" />
        </svg>
        <div className="w-full flex justify-between absolute bottom-[-28px] text-[10px] text-muted-foreground font-bold uppercase tracking-wider">
          {['WK 1', 'WK 2', 'WK 3', 'WK 4', 'WK 5'].map((w) => (
            <span key={w}>{w}</span>
          ))}
        </div>
      </div>
    </Card>
  )
}

function RecentVideos() {
  return (
    <Card className="overflow-hidden flex flex-col">
      <div className="p-4 border-b border-te-outline-variant flex justify-between items-center bg-te-surface-container-low">
        <h4 className="text-sm font-semibold text-foreground">Recent Videos Viewed</h4>
        <Button variant="link" size="sm" className="text-xs p-0 h-auto">View Library</Button>
      </div>
      <div className="divide-y divide-te-outline-variant">
        {RECENT_VIDEOS.map((v, i) => (
          <div key={i} className="p-4 flex items-center gap-4 hover:bg-te-surface-container-low transition-colors group cursor-pointer">
            <div className="relative w-28 h-16 rounded-lg bg-muted overflow-hidden flex-shrink-0">
              <img className="w-full h-full object-cover" src={v.img} alt={v.title} />
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <Icon name="play_circle" className="text-white text-3xl" />
              </div>
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-foreground">{v.title}</div>
              <div className="text-[11px] text-muted-foreground mt-1 flex items-center gap-2">
                <Icon name="schedule" className="text-xs" /> {v.time}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function RecentAIQueries() {
  return (
    <Card className="overflow-hidden flex flex-col">
      <div className="p-4 border-b border-te-outline-variant flex justify-between items-center bg-te-surface-container-low">
        <h4 className="text-sm font-semibold text-foreground">Recent Chatbot Queries</h4>
        <Button variant="link" size="sm" className="text-xs p-0 h-auto">New Query</Button>
      </div>
      <div className="divide-y divide-te-outline-variant">
        {RECENT_QUERIES.map((q, i) => (
          <div key={i} className="p-5 flex items-start gap-4">
            <div className="bg-primary/10 p-2.5 rounded-xl">
              <Icon name="psychology" className="text-primary text-xl" />
            </div>
            <div className="flex-1">
              <div className="text-[13px] italic text-muted-foreground leading-relaxed">{q.query}</div>
              <div className="mt-3 text-[11px] font-bold flex items-center gap-1.5 text-primary uppercase tracking-wide">
                <Icon name="check_circle" className="text-[16px]" filled /> {q.status}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Welcome back, Coach. Here's your player's performance summary."
        actions={
          <>
            <Button><Icon name="search" className="text-sm" /> Search Data</Button>
            <Button variant="outline"><Icon name="video_library" className="text-sm" /> Open Library</Button>
            <Button variant="outline"><Icon name="auto_awesome" className="text-sm" /> Ask AI</Button>
          </>
        }
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {DASHBOARD_STATS.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <PerformanceChart />
        <Card className="p-6">
          <CardTitle className="mb-6">Win Rate by Surface</CardTitle>
          <div className="space-y-6">
            {WIN_RATES.map((wr) => (
              <ProgressBar key={wr.surface} label={wr.surface} value={wr.pct} color={wr.color} />
            ))}
          </div>
        </Card>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentVideos />
        <RecentAIQueries />
      </div>
    </div>
  )
}
