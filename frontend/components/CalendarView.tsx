'use client'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { Event } from '@/types'
import ptBrLocale from '@fullcalendar/core/locales/pt-br'

interface Props {
  events: Event[]
  onEventClick: (event: Event) => void
}

export default function CalendarView({ events, onEventClick }: Props) {
  const calendarEvents = events.map((e) => ({
    id: e.id,
    title: e.title,
    start: e.event_datetime,
    color: e.status === 'sent' ? '#16a34a' : e.status === 'cancelled' ? '#9ca3af' : '#2563eb',
    extendedProps: { original: e },
  }))

  return (
    <FullCalendar
      plugins={[dayGridPlugin, interactionPlugin]}
      initialView="dayGridMonth"
      locale={ptBrLocale}
      events={calendarEvents}
      eventClick={(info) => onEventClick(info.event.extendedProps.original as Event)}
      height="auto"
    />
  )
}
