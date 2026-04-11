'use client'
import { useState } from 'react'
import { Event, EventCreate } from '@/types'
import { createEvent, updateEvent } from '@/lib/api'

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
  const [datetime, setDatetime] = useState(
    event ? event.event_datetime.slice(0, 16) : ''
  )
  const [remindMinutes, setRemindMinutes] = useState(30)
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold mb-4">
          {event ? 'Editar evento' : 'Novo evento'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              placeholder="Ex: Reunião com cliente"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição (opcional)</label>
            <textarea
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={description ?? ''}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data e hora</label>
            <input
              type="datetime-local"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={datetime}
              onChange={(e) => setDatetime(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Lembrete</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={remindMinutes}
              onChange={(e) => setRemindMinutes(Number(e.target.value))}
            >
              {REMIND_OPTIONS.map((o) => (
                <option key={o.minutes} value={o.minutes}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 rounded-lg py-2 text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
