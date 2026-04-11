import { Event, EventCreate, EventUpdate } from '@/types'

const BASE = process.env.NEXT_PUBLIC_API_URL!
const KEY = process.env.NEXT_PUBLIC_API_KEY!

const headers = () => ({
  'Content-Type': 'application/json',
  'X-API-Key': KEY,
})

export async function fetchEvents(): Promise<Event[]> {
  const res = await fetch(`${BASE}/events`, { headers: headers() })
  if (!res.ok) throw new Error('Failed to fetch events')
  return res.json()
}

export async function createEvent(data: EventCreate): Promise<Event> {
  const res = await fetch(`${BASE}/events`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create event')
  return res.json()
}

export async function updateEvent(id: string, data: EventUpdate): Promise<Event> {
  const res = await fetch(`${BASE}/events/${id}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update event')
  return res.json()
}

export async function deleteEvent(id: string): Promise<Event> {
  const res = await fetch(`${BASE}/events/${id}`, {
    method: 'DELETE',
    headers: headers(),
  })
  if (!res.ok) throw new Error('Failed to cancel event')
  return res.json()
}
