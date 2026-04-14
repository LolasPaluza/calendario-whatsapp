'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const router = useRouter()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    document.cookie = `auth=${password}; path=/; max-age=2592000`
    router.push('/')
    router.refresh()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-violet-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden">
        <div className="bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-6 text-center">
          <h1 className="text-white text-xl font-bold">Calendário</h1>
          <p className="text-white/70 text-sm mt-1">Acesso restrito</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">
              Senha
            </label>
            <input
              type="password"
              className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(false) }}
              placeholder="Digite sua senha"
              autoFocus
            />
            {error && <p className="text-red-500 text-xs mt-1">Senha incorreta</p>}
          </div>
          <button
            type="submit"
            className="w-full bg-indigo-600 text-white rounded-xl py-2.5 text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-md shadow-indigo-200"
          >
            Entrar
          </button>
        </form>
      </div>
    </div>
  )
}
