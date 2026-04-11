export interface Event {
  id: string
  title: string
  description: string | null
  event_datetime: string
  remind_at: string
  status: 'pending' | 'sent' | 'cancelled'
  user_phone: string
  created_at: string
}

export interface EventCreate {
  title: string
  description?: string
  event_datetime: string
  remind_at?: string
  user_phone?: string
}

export interface EventUpdate {
  title?: string
  description?: string
  event_datetime?: string
  remind_at?: string
}
