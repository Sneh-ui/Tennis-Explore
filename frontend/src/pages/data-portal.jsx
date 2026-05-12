import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Card } from '@/components/ui/card'
import { Icon, PageHeader, DataTable, InsightCard } from '@/components/shared'
import { MATCH_DATA, DATA_PORTAL_FILTERS, DATA_PORTAL_INSIGHTS } from '@/data/constants'
import { cn } from '@/lib/utils'

function FilterBar() {
  return (
    <Card className="p-4 flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-2 text-muted-foreground pr-4 border-r border-te-outline-variant text-label-md">
        <Icon name="filter_list" /> <span>Filters</span>
      </div>

      <Select defaultValue="All Players">
        <SelectTrigger className="w-[160px] h-9 text-label-md">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DATA_PORTAL_FILTERS.players.map((p) => (
            <SelectItem key={p} value={p}>{p}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select defaultValue="Wimbledon">
        <SelectTrigger className="w-[160px] h-9 text-label-md bg-primary-container text-primary-container-foreground border-transparent hover:border-transparent">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DATA_PORTAL_FILTERS.tournaments.map((t) => (
            <SelectItem key={t} value={t}>{t}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select defaultValue="2024">
        <SelectTrigger className="w-[100px] h-9 text-label-md">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DATA_PORTAL_FILTERS.years.map((y) => (
            <SelectItem key={y} value={y}>{y}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select defaultValue="Match Type">
        <SelectTrigger className="w-[140px] h-9 text-label-md">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DATA_PORTAL_FILTERS.matchTypes.map((m) => (
            <SelectItem key={m} value={m}>{m}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button variant="ghost" size="sm" className="ml-auto text-label-md">
        Clear all
      </Button>
    </Card>
  )
}

const TABLE_COLUMNS = [
  {
    key: 'player',
    label: 'Player Name',
    sortable: true,
    render: (val) => (
      <div className="flex items-center gap-3">
        <div className="w-1 h-6 bg-primary rounded-full" />
        <span className="font-semibold">{val}</span>
      </div>
    ),
  },
  { key: 'opponent', label: 'Opponent', render: (val) => <span className="text-muted-foreground">{val}</span> },
  { key: 'date', label: 'Match Date', render: (val) => <span className="text-muted-foreground">{val}</span> },
  { key: 'score', label: 'Score', render: (val) => <span className="font-bold">{val}</span> },
  { key: 'aces', label: 'Aces', align: 'center', render: (val) => <span className="font-bold">{val}</span> },
  { key: 'df', label: 'Double Faults', align: 'center' },
]

export default function DataPortalPage() {
  const [currentPage, setCurrentPage] = useState(1)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Data Portal"
        subtitle="Access and filter comprehensive professional tennis datasets."
        actions={
          <Button variant="dark" className="rounded-full">
            <Icon name="download" className="text-sm" /> Export Data
          </Button>
        }
      />

      <FilterBar />

      <DataTable
        columns={TABLE_COLUMNS}
        data={MATCH_DATA}
        currentPage={currentPage}
        totalItems={124}
        onPageChange={setCurrentPage}
      />

      {/* Summary Insight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {DATA_PORTAL_INSIGHTS.map((insight) => (
          <InsightCard
            key={insight.label}
            label={insight.label}
            value={insight.value}
            subtext={insight.sub}
            subtextIcon={insight.icon}
            subtextColor={insight.color}
            borderColor={insight.borderColor}
          />
        ))}
      </div>
    </div>
  )
}
