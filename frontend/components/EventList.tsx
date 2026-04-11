'use client'
import { Event } from '@/types'
import { deleteEvent } from '@/lib/api'

const STATUS_COLORS: Record<Event['status'], string> = {
  pending: 'bg-blue-100 text-blue-700',
  sent: 'bg-green-100 text-green-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

const STATUS_LABELS: Record<Event['status'], string> = {
  pending: 'Pendente',
  sent: 'Enviado',
  cancelled: 'Cancelado',
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
    return <p className="text-gray-500 text-center py-8">Nenhum evento encontrado.</p>
  }

  return (
    <ul className="space-y-3">
      {events.map((event) => (
        <li key={event.id} className="border border-gray-200 rounded-xl p-4 flex items-start justify-between gap-4">
          <div>
            <p className="font-medium text-gray-900">{event.title}</p>
            {event.description && (
              <p className="text-sm text-gray-500 mt-0.5">{event.description}</p>
            )}
            <p className="text-sm text-gray-600 mt-1">
              {new Date(event.event_datetime).toLocaleString('pt-BR', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </p>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[event.status]}`}>
              {STATUS_LABELS[event.status]}
            </span>
          </div>
          {event.status === 'pending' && (
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => onEdit(event)}
                className="text-sm text-blue-600 hover:underline"
              >
                Editar
              </button>
              <button
                onClick={() => handleCancel(event.id)}
                className="text-sm text-red-500 hover:underline"
              >
                Cancelar
              </button>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
