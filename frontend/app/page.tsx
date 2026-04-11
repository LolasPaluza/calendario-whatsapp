'use client'
import { useCallback, useEffect, useState } from 'react'
import { Event } from '@/types'
import { fetchEvents } from '@/lib/api'
import CalendarView from '@/components/CalendarView'
import EventList from '@/components/EventList'
import EventModal from '@/components/EventModal'

export default function HomePage() {
  const [events, setEvents] = useState<Event[]>([])
  const [view, setView] = useState<'calendar' | 'list'>('calendar')
  const [modal, setModal] = useState<{ open: boolean; event?: Event }>({ open: false })

  const load = useCallback(async () => {
    const data = await fetchEvents()
    setEvents(data)
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Meu Calendário</h1>
        <div className="flex gap-2">
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setView('calendar')}
              className={`px-3 py-1.5 text-sm ${view === 'calendar' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Calendário
            </button>
            <button
              onClick={() => setView('list')}
              className={`px-3 py-1.5 text-sm ${view === 'list' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Lista
            </button>
          </div>
          <button
            onClick={() => setModal({ open: true })}
            className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-blue-700"
          >
            + Novo evento
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        {view === 'calendar' ? (
          <CalendarView events={events} onEventClick={(e) => setModal({ open: true, event: e })} />
        ) : (
          <EventList events={events} onEdit={(e) => setModal({ open: true, event: e })} onRefresh={load} />
        )}
      </div>

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
