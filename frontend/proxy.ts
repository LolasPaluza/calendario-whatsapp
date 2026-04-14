import { NextRequest, NextResponse } from 'next/server'

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const auth = request.cookies.get('auth')?.value
  const password = process.env.DASHBOARD_PASSWORD || 'calendario2024'

  if (pathname === '/login') return NextResponse.next()

  if (auth !== password) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
