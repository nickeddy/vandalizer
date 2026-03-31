import { useState, useEffect } from 'react'
import { Navigate, Link, useSearch } from '@tanstack/react-router'
import { useAuth } from '../hooks/useAuth'
import { AuthLayout } from '../components/layout/AuthLayout'
import { LoginForm } from '../components/auth/LoginForm'
import { getAuthConfig } from '../api/auth'

export function Login() {
  const { user, loading } = useAuth()
  const search = useSearch({ strict: false }) as Record<string, string | undefined>
  const adminOverride = search?.admin === '1'
  const [passwordAllowed, setPasswordAllowed] = useState<boolean | null>(null)

  useEffect(() => {
    getAuthConfig().then(c => setPasswordAllowed(c.auth_methods.includes('password') || adminOverride))
  }, [adminOverride])

  if (loading || passwordAllowed === null) return null
  if (user) {
    return (
      <Navigate
        to="/"
        search={{
          mode: undefined,
          tab: undefined,
          workflow: undefined,
          extraction: undefined,
          automation: undefined,
          kb: undefined,
        }}
      />
    )
  }

  if (!passwordAllowed) {
    return <Navigate to="/landing" search={{ error: undefined, invite_token: undefined }} />
  }

  return (
    <AuthLayout title="Sign in to Vandalizer">
      <LoginForm />
      <p className="mt-4 text-center text-sm text-gray-600">
        Don't have an account?{' '}
        <Link to="/register" className="font-medium text-highlight hover:brightness-75">
          Register
        </Link>
      </p>
    </AuthLayout>
  )
}
