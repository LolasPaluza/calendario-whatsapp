'use client'
import { useCallback, useEffect, useState } from 'react'
import { Event } from '@/types'
import { fetchEvents } from '@/lib/api'
import CalendarView from '@/components/CalendarView'
import EventList from '@/components/EventList'
import EventModal from '@/components/EventModal'
import { CalendarDays, List, Plus, Bell, CheckCircle2, Clock } from 'lucide-react'

export default function HomePage() {
  const [events, setEvents] = useState<Event[]>([])
  const [view, setView] = useState<'calendar' | 'list'>('calendar')
  const [modal, setModal] = useState<{ open: boolean; event?: Event }>({ open: false })

  const load = useCallback(async () => {
    const data = await fetchEvents()
    setEvents(data)
  }, [])

  useEffect(() => { load() }, [load])

  const pending = events.filter(e => e.status === 'pending').length
  const sent = events.filter(e => e.status === 'sent').length
  const today = new Date().toDateString()
  const todayCount = events.filter(e =>
    e.status === 'pending' && new Date(e.event_datetime).toDateString() === today
  ).length

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-600 to-violet-600 shadow-lg">
        <div className="max-w-5xl mx-auto px-4 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-white/20 rounded-xl p-2">
              <CalendarDays className="text-white" size={22} />
            </div>
            <div>
              <h1 className="text-white font-bold text-xl leading-tight">Meu Calendário</h1>
              <p className="text-indigo-200 text-xs">Gerenciado pelo WhatsApp</p>
            </div>
          </div>
          <button
            onClick={() => setModal({ open: true })}
            className="flex items-center gap-2 bg-white text-indigo-600 px-4 py-2 rounded-xl text-sm font-semibold hover:bg-indigo-50 transition-colors shadow-md"
          >
            <Plus size={16} />
            Novo evento
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-5">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 flex items-center gap-3">
            <div className="bg-indigo-100 rounded-xl p-2.5">
              <Bell size={18} className="text-indigo-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">{pending}</p>
              <p className="text-xs text-slate-500">Pendentes</p>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 flex items-center gap-3">
            <div className="bg-amber-100 rounded-xl p-2.5">
              <Clock size={18} className="text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">{todayCount}</p>
              <p className="text-xs text-slate-500">Hoje</p>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 flex items-center gap-3">
            <div className="bg-emerald-100 rounded-xl p-2.5">
              <CheckCircle2 size={18} className="text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">{sent}</p>
              <p className="text-xs text-slate-500">Concluídos</p>
            </div>
          </div>
        </div>

        {/* View toggle + content */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
            <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
              <button
                onClick={() => setView('calendar')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  view === 'calendar'
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <CalendarDays size={14} />
                Calendário
              </button>
              <button
                onClick={() => setView('list')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  view === 'list'
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <List size={14} />
                Lista
              </button>
            </div>
            <span className="text-xs text-slate-400">{events.length} evento{events.length !== 1 ? 's' : ''}</span>
          </div>

          <div className="p-5">
            {view === 'calendar' ? (
              <CalendarView events={events} onEventClick={(e) => setModal({ open: true, event: e })} />
            ) : (
              <EventList events={events} onEdit={(e) => setModal({ open: true, event: e })} onRefresh={load} />
            )}
          </div>
        </div>
      </main>

      {modal.open && (
        <EventModal
          event={modal.event}
          onClose={() => setModal({ open: false })}
          onSaved={load}
        />
      )}
    </div>
  )
}
