'use client'
import { Event } from '@/types'
import { deleteEvent } from '@/lib/api'
import { CalendarDays, Clock, Pencil, X } from 'lucide-react'

const STATUS_STYLES: Record<Event['status'], { dot: string; badge: string; label: string }> = {
  pending:   { dot: 'bg-indigo-500',  badge: 'bg-indigo-50 text-indigo-700 border-indigo-200',  label: 'Pendente'  },
  sent:      { dot: 'bg-emerald-500', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Enviado'   },
  cancelled: { dot: 'bg-slate-400',   badge: 'bg-slate-50 text-slate-500 border-slate-200',      label: 'Cancelado' },
}

interface Props {
  events: Event[]
  onEdit: (event: Event) => void
  onRefresh: () => void
}

export default function EventList({ events, onEdit, onRefresh }: Props) {
  async function handleCancel(id: string) {
    if (!confirm('Cancelar este evento?')) return
    await deleteEvent(id)
    onRefresh()
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-14">
        <CalendarDays size={40} className="text-slate-300 mx-auto mb-3" />
        <p className="text-slate-400 text-sm">Nenhum evento ainda.</p>
        <p className="text-slate-400 text-xs mt-1">Crie um ou mande mensagem no WhatsApp.</p>
      </div>
    )
  }

  const sorted = [...events].sort(
    (a, b) => new Date(a.event_datetime).getTime() - new Date(b.event_datetime).getTime()
  )

  return (
    <ul className="space-y-2">
      {sorted.map((event) => {
        const s = STATUS_STYLES[event.status]
        const dt = new Date(event.event_datetime)
        const remind = new Date(event.remind_at)
        return (
          <li
            key={event.id}
            className="group flex items-start gap-4 p-4 rounded-xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all"
          >
            {/* Color dot */}
            <div className={`mt-1.5 w-2.5 h-2.5 rounded-full shrink-0 ${s.dot}`} />

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className={`font-semibold text-slate-800 truncate ${event.status === 'cancelled' ? 'line-through text-slate-400' : ''}`}>
                {event.title}
              </p>
              {event.description && (
                <p className="text-xs text-slate-500 mt-0.5 truncate">{event.description}</p>
              )}
              <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <CalendarDays size={11} />
                  {dt.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className="flex items-center gap-1 text-xs text-slate-400">
                  <Clock size={11} />
                  Lembrete: {remind.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${s.badge}`}>
                  {s.label}
                </span>
              </div>
            </div>

            {/* Actions */}
            {event.status === 'pending' && (
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <button
                  onClick={() => onEdit(event)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-100 transition-colors"
                  title="Editar"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={() => handleCancel(event.id)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-100 transition-colors"
                  title="Cancelar"
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
