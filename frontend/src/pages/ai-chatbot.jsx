import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Icon, ProgressBar } from '@/components/shared'
import { INITIAL_MESSAGES, CHAT_SUGGESTIONS } from '@/data/constants'
import { cn } from '@/lib/utils'

function ChatMessage({ msg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex gap-4 items-start justify-end">
        <div className="bg-primary p-5 rounded-xl text-primary-foreground shadow-md max-w-[85%]" style={{ borderBottomRightRadius: 4 }}>
          <p className="text-body-md">{msg.content}</p>
        </div>
        <div className="w-8 h-8 bg-primary-container rounded-lg flex items-center justify-center shrink-0">
          <Icon name="person" className="text-sm text-primary-container-foreground" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-4 items-start max-w-[90%]">
      <div className="w-8 h-8 bg-te-surface-container-highest rounded-lg flex items-center justify-center shrink-0">
        <Icon name="smart_toy" className="text-sm text-foreground" />
      </div>
      <Card className={cn('p-5 space-y-5', msg.chart && 'border-l-4 border-l-primary')} style={{ borderBottomLeftRadius: 4 }}>
        <p className="text-body-md text-foreground">{msg.content}</p>

        {/* Inline bar chart */}
        {msg.chart && (
          <div className="space-y-3 bg-te-surface-container-low p-4 rounded-lg">
            <p className="text-label-md font-bold text-muted-foreground uppercase tracking-wider">First Serve Win %</p>
            <div className="space-y-4">
              {msg.chart.map((p) => (
                <div key={p.name} className="flex items-center gap-3">
                  <span className="text-xs font-bold w-20 text-foreground">{p.name}</span>
                  <div className="flex-1 h-3 bg-te-surface-container-highest rounded-full overflow-hidden">
                    <div className={cn('h-full rounded-full transition-all duration-700', p.color)} style={{ width: `${p.pct}%` }} />
                  </div>
                  <span className="text-xs font-bold text-foreground">{p.pct}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Inline data table */}
        {msg.table && (
          <div className="overflow-hidden border border-te-outline-variant rounded-lg">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-te-surface-container-low border-b border-te-outline-variant font-bold text-muted-foreground">
                  <th className="px-4 py-2">Matchup</th>
                  <th className="px-4 py-2 text-center">Score</th>
                  <th className="px-4 py-2 text-right">Aces</th>
                </tr>
              </thead>
              <tbody className="text-foreground">
                {msg.table.map((row, i) => (
                  <tr key={i} className="border-b border-muted last:border-0 hover:bg-te-surface-container-low transition-colors">
                    <td className="px-4 py-2 font-medium">{row.matchup}</td>
                    <td className="px-4 py-2 text-center">{row.score}</td>
                    <td className="px-4 py-2 text-right">{row.aces}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {msg.followUp && <p className="text-body-md text-muted-foreground">{msg.followUp}</p>}
      </Card>
    </div>
  )
}

function SuggestionsPanel() {
  return (
    <aside className="hidden xl:flex flex-col w-80 bg-card p-6 shrink-0 overflow-y-auto border-l border-te-outline-variant">
      <div className="mb-8">
        <h3 className="font-bold text-xs uppercase tracking-wider text-te-outline mb-4">Suggested Actions</h3>
        <div className="space-y-3">
          {CHAT_SUGGESTIONS.map((s, i) => (
            <button key={i} className="w-full text-left p-4 rounded-xl border border-te-outline-variant hover:border-primary hover:bg-te-surface-container-low transition-all group">
              <p className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">{s.title}</p>
              <p className="text-xs text-muted-foreground mt-1">{s.desc}</p>
            </button>
          ))}
        </div>
      </div>
      <div className="mt-auto">
        <Card className="p-5 bg-muted">
          <div className="flex items-center gap-3 mb-3">
            <Icon name="info" className="text-primary" />
            <span className="font-bold text-sm text-foreground">Did you know?</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            You can now compare two players side-by-side by asking "Compare Player A and Player B in tie-break situations."
          </p>
        </Card>
      </div>
    </aside>
  )
}

export default function AIChatbotPage() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: input },
      {
        role: 'ai',
        content: "I'm analyzing the data you requested. This is a demo response — in production, this would connect to the analytics engine for real-time insights.",
      },
    ])
    setInput('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden -m-6">
      {/* Chat Container */}
      <div className="flex-1 flex flex-col relative bg-card">
        {/* Chat Header */}
        <div className="px-8 py-4 border-b border-te-outline-variant flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-primary-foreground">
              <Icon name="psychology" />
            </div>
            <div>
              <h2 className="text-title-lg text-foreground">AI Assistant</h2>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <span className="w-2 h-2 bg-primary rounded-full animate-pulse" /> Online &amp; Ready
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-primary">
            <Icon name="history" className="text-lg" /> View Session History
          </Button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-te-surface-container-low scrollbar-thin">
          {messages.map((msg, i) => (
            <ChatMessage key={i} msg={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-6 border-t border-te-outline-variant bg-card shrink-0">
          <div className="max-w-4xl mx-auto relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="pr-16 min-h-[64px] max-h-[200px]"
              placeholder="Ask about players, matches, or videos..."
            />
            <div className="absolute right-3 bottom-3">
              <Button size="icon" className="w-10 h-10 rounded-xl" onClick={handleSend}>
                <Icon name="send" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <SuggestionsPanel />
    </div>
  )
}
