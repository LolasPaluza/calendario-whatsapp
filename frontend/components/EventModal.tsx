'use client'
import { useState } from 'react'
import { Event, EventCreate } from '@/types'
import { createEvent, updateEvent } from '@/lib/api'
import { X, CalendarDays, Clock, AlignLeft, Bell } from 'lucide-react'

interface Props {
  event?: Event
  onClose: () => void
  onSaved: () => void
}

const REMIND_OPTIONS = [
  { label: '15 min antes', minutes: 15 },
  { label: '30 min antes', minutes: 30 },
  { label: '1 hora antes', minutes: 60 },
  { label: '1 dia antes', minutes: 1440 },
]

export default function EventModal({ event, onClose, onSaved }: Props) {
  const [title, setTitle] = useState(event?.title ?? '')
  const [description, setDescription] = useState(event?.description ?? '')
  const [datetime, setDatetime] = useState(() => {
    if (!event) return ''
    const dt = new Date(event.event_datetime)
    // Convert UTC to local time so datetime-local input shows the correct local time
    return new Date(dt.getTime() - dt.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16)
  })
  const [remindMinutes, setRemindMinutes] = useState(() => {
    if (!event) return 30
    const eventDt = new Date(event.event_datetime)
    const remindDt = new Date(event.remind_at)
    const diff = Math.round((eventDt.getTime() - remindDt.getTime()) / 60000)
    const closest = REMIND_OPTIONS.reduce((prev, curr) =>
      Math.abs(curr.minutes - diff) < Math.abs(prev.minutes - diff) ? curr : prev
    )
    return closest.minutes
  })
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title || !datetime) return
    setLoading(true)
    try {
      const dt = new Date(datetime)
      const remindAt = new Date(dt.getTime() - remindMinutes * 60 * 1000)
      if (event) {
        await updateEvent(event.id, {
          title,
          description: description || undefined,
          event_datetime: dt.toISOString(),
          remind_at: remindAt.toISOString(),
        })
      } else {
        const data: EventCreate = {
          title,
          description: description || undefined,
          event_datetime: dt.toISOString(),
          remind_at: remindAt.toISOString(),
          user_phone: '',
        }
        await createEvent(data)
      }
      onSaved()
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        {/* Modal header */}
        <div className="bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-4 flex items-center justify-between">
          <h2 className="text-white font-semibold text-base">
            {event ? 'Editar evento' : 'Novo evento'}
          </h2>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Title */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">
              <CalendarDays size={12} /> Título
            </label>
            <input
              className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              placeholder="Ex: Reunião com cliente"
            />
          </div>

          {/* Description */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">
              <AlignLeft size={12} /> Descrição <span className="normal-case font-normal text-slate-400">(opcional)</span>
            </label>
            <textarea
              className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none"
              value={description ?? ''}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Detalhes do evento..."
            />
          </div>

          {/* Date/time + Reminder side by side */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">
                <Clock size={12} /> Data e hora
              </label>
              <input
                type="datetime-local"
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                value={datetime}
                onChange={(e) => setDatetime(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">
                <Bell size={12} /> Lembrete
              </label>
              <select
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition bg-white"
                value={remindMinutes}
                onChange={(e) => setRemindMinutes(Number(e.target.value))}
              >
                {REMIND_OPTIONS.map((o) => (
                  <option key={o.minutes} value={o.minutes}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-200 rounded-xl py-2.5 text-sm text-slate-600 font-medium hover:bg-slate-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-indigo-600 text-white rounded-xl py-2.5 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-md shadow-indigo-200"
            >
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
